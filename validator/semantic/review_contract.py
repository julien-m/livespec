"""Strict grounded reviewer output and completeness validation (078 FR-003)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from validator.semantic.review_context import PreparedReview, ReviewBatch
from validator.semantic.review_synthesis_transport import (
    SYNTHESIS_TRANSPORT_VERSION,
    synthesis_prompt,
)


class StrictModel(BaseModel):
    """External review data rejects unknown fields and coercions."""

    model_config = ConfigDict(extra="forbid", strict=True)


class Citation(StrictModel):
    """An exact excerpt inside an inventoried source section."""

    section_id: str
    excerpt: str = Field(min_length=1)


class RequirementConclusion(StrictModel):
    """Independent semantic judgment with inspectable grounding."""

    requirement_id: str
    disposition: Literal["covered", "contradictory", "missing", "ambiguous"]
    rationale: str = Field(min_length=1)
    source_citations: list[Citation] = Field(min_length=1)
    plan_citations: list[Citation] = Field(default_factory=list)
    searched_plan_sections: list[str] = Field(default_factory=list)


class Ambiguity(StrictModel):
    """Consequential business decision, optionally resolved by approved context."""

    requirement_id: str
    decision_key: str = Field(min_length=1)
    question: str = Field(min_length=1)
    critical: bool
    citations: list[Citation] = Field(min_length=1)
    resolution: str = ""
    resolution_citations: list[Citation] = Field(default_factory=list)


class ScopeFinding(StrictModel):
    """Additional behavior distinguished from justified technical necessities."""

    description: str = Field(min_length=1)
    justification: str
    approved: bool
    citations: list[Citation] = Field(min_length=1)


class GroundedFinding(StrictModel):
    """General reviewer issue with original legacy display fields."""

    category: str
    severity: Literal["blocking", "warning", "info"]
    description: str
    suggestion: str
    citations: list[Citation] = Field(min_length=1)


class IssueResolution(StrictModel):
    """Explicit cross-batch decision bound to an original issue key."""

    issue_key: str
    rationale: str = Field(min_length=1)
    citations: list[Citation] = Field(min_length=1)


class ReviewResponse(StrictModel):
    """One batch or final synthesis, with explicit exhaustive identities."""

    batch_id: str
    reviewed_section_ids: list[str]
    conclusions: list[RequirementConclusion]
    ambiguities: list[Ambiguity]
    extra_scope: list[ScopeFinding]
    findings: list[GroundedFinding]
    confidence: int = Field(ge=1, le=5)
    synthesized_batch_ids: list[str] = Field(default_factory=list)
    resolutions: list[IssueResolution] = Field(default_factory=list)


class ReviewReceipt(StrictModel):
    """Validated result and raw evidence; completion is distinct from readiness."""

    schema_version: str = "1"
    policy_version: str = "078.1"
    context_hash: str
    source_hashes: dict[str, str] = Field(default_factory=dict)
    reviewer_model: str
    complete: bool
    ready: bool
    errors: list[str]
    conclusions: list[RequirementConclusion] = Field(default_factory=list)
    ambiguities: list[Ambiguity] = Field(default_factory=list)
    extra_scope: list[ScopeFinding] = Field(default_factory=list)
    findings: list[GroundedFinding] = Field(default_factory=list)
    confidence: int = 0
    raw_results: list[str] = Field(default_factory=list)
    synthesis: str | None = None
    synthesis_transport_version: str | None = None


REVIEW_SCHEMA = {
    "name": "grounded_review",
    "strict": True,
    "schema": ReviewResponse.model_json_schema(),
}


def _citation_errors(
    citations: list[Citation], prepared: PreparedReview, allowed: set[str]
) -> list[str]:
    sections = {s.section_id: s for s in prepared.sections}
    return [
        f"invalid_citation:{citation.section_id}"
        for citation in citations
        if citation.section_id not in allowed
        or citation.section_id not in sections
        or citation.excerpt not in sections[citation.section_id].text
    ]


def _conclusion_errors(
    response: ReviewResponse, prepared: PreparedReview, allowed: set[str]
) -> list[str]:
    obligations = {r.requirement_id: r for r in prepared.requirements}
    plan_ids = {s.section_id for s in prepared.sections if s.role == "plan"}
    errors = []
    for conclusion in response.conclusions:
        obligation = obligations.get(conclusion.requirement_id)
        if obligation is None:
            errors.append(f"foreign_requirement:{conclusion.requirement_id}")
            continue
        errors.extend(
            _citation_errors(
                conclusion.source_citations, prepared, set(obligation.section_ids) & allowed
            )
        )
        errors.extend(_citation_errors(conclusion.plan_citations, prepared, plan_ids & allowed))
        if prepared.kind == "plan":
            if (
                conclusion.disposition in ("covered", "contradictory")
                and not conclusion.plan_citations
            ):
                errors.append(f"missing_plan_citation:{conclusion.requirement_id}")
            if conclusion.disposition == "missing" and (
                conclusion.plan_citations
                or set(conclusion.searched_plan_sections) != plan_ids & allowed
            ):
                errors.append(f"invalid_missing_search:{conclusion.requirement_id}")
    return errors


def validate_response(
    response: ReviewResponse, prepared: PreparedReview, batch: ReviewBatch | None = None
) -> list[str]:
    """Check source grounding and exhaustive inventory; never infer semantic truth."""
    expected_sections = set(
        batch.section_ids if batch else (s.section_id for s in prepared.sections)
    )
    expected_requirements = set(
        batch.requirement_ids if batch else (r.requirement_id for r in prepared.requirements)
    )
    errors = []
    ids = response.reviewed_section_ids
    if set(ids) != expected_sections or len(ids) != len(set(ids)):
        errors.append("incomplete_or_duplicate_sections")
    conclusions = [c.requirement_id for c in response.conclusions]
    if set(conclusions) != expected_requirements or len(conclusions) != len(set(conclusions)):
        errors.append("incomplete_or_duplicate_requirements")
    if response.batch_id != (batch.batch_id if batch else "synthesis"):
        errors.append("wrong_batch_identity")
    errors.extend(_conclusion_errors(response, prepared, expected_sections))
    citation_groups = [issue.citations for issue in response.findings]
    citation_groups.extend(issue.citations for issue in response.ambiguities)
    citation_groups.extend(issue.citations for issue in response.extra_scope)
    for citations in citation_groups:
        errors.extend(_citation_errors(citations, prepared, expected_sections))
    for ambiguity in response.ambiguities:
        if ambiguity.requirement_id not in expected_requirements:
            errors.append("foreign_ambiguity_requirement")
        approved = {
            s.section_id for s in prepared.sections if s.role in ("constitution", "project", "spec")
        }
        if ambiguity.resolution and not ambiguity.resolution_citations:
            errors.append("ungrounded_resolution")
        errors.extend(
            _citation_errors(ambiguity.resolution_citations, prepared, approved & expected_sections)
        )
    if any(scope.approved and not scope.justification.strip() for scope in response.extra_scope):
        errors.append("unjustified_extra_scope")
    if batch is None and response.synthesized_batch_ids != [b.batch_id for b in prepared.batches]:
        errors.append("incomplete_batch_synthesis")
    return errors


def validate_review_result(
    prepared: PreparedReview, raw_results: list[str], synthesis: str | None = None
) -> ReviewReceipt:
    """Assemble only a complete, grounded batch set and required final synthesis."""
    errors = list(prepared.errors)
    responses = []
    if len(raw_results) != len(prepared.batches):
        errors.append("incomplete_batch_count")
    for batch, raw in zip(prepared.batches, raw_results, strict=False):
        try:
            response = ReviewResponse.model_validate_json(raw)
        except ValidationError as exc:
            errors.append(f"malformed_response:{batch.batch_id}:{exc.error_count()}")
            continue
        errors.extend(validate_response(response, prepared, batch))
        responses.append(response)
    final = responses[0] if len(prepared.batches) == 1 and responses else None
    if len(prepared.batches) > 1:
        final, final_errors = _validated_synthesis(prepared, raw_results, responses, synthesis)
        errors.extend(final_errors)
    complete = prepared.complete and not errors and final is not None
    ready = bool(
        complete
        and final
        and all(c.disposition == "covered" for c in final.conclusions)
        and not any(a.critical and not a.resolution for a in final.ambiguities)
        and not any(not scope.approved for scope in final.extra_scope)
        and not any(f.severity == "blocking" for f in final.findings)
    )
    return ReviewReceipt(
        context_hash=prepared.context_hash,
        source_hashes=prepared.source_hashes,
        reviewer_model=prepared.reviewer_model,
        complete=complete,
        ready=ready,
        errors=errors,
        raw_results=raw_results,
        synthesis=synthesis,
        synthesis_transport_version=SYNTHESIS_TRANSPORT_VERSION
        if len(prepared.batches) > 1
        else None,
        conclusions=final.conclusions if final else [],
        ambiguities=final.ambiguities if final else [],
        extra_scope=final.extra_scope if final else [],
        findings=final.findings if final else [],
        confidence=final.confidence if final else 0,
    )


def _validated_synthesis(
    prepared: PreparedReview,
    raws: list[str],
    responses: list[ReviewResponse],
    synthesis: str | None,
) -> tuple[ReviewResponse | None, list[str]]:
    """Native ingestion and provider execution enforce the same complete transport budget."""
    from validator.semantic.review_synthesis import validate_issue_ledger

    errors = []
    if len(synthesis_prompt(prepared, raws)) > prepared.max_chars:
        errors.append("synthesis_context_over_budget")
    try:
        final = ReviewResponse.model_validate_json(synthesis or "")
    except ValidationError:
        return None, [*errors, "missing_or_malformed_synthesis"]
    errors.extend(validate_response(final, prepared))
    errors.extend(validate_issue_ledger(responses, final, prepared))
    return final, errors
