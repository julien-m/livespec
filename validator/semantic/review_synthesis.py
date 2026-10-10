"""Preserve blocking batch issues until grounded synthesis explicitly resolves them."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from validator.semantic.review_context import PreparedReview
    from validator.semantic.review_contract import ReviewResponse


def _key(kind: str, identity: str) -> str:
    return kind + ":" + hashlib.sha256(identity.encode()).hexdigest()[:20]


def issue_ledger(response: ReviewResponse) -> dict[str, dict]:
    """Expose stable issue identities independently of formatting or display position."""
    ledger = {}
    for conclusion in response.conclusions:
        if conclusion.disposition == "contradictory":
            ledger[_key("contradiction", conclusion.requirement_id)] = conclusion.model_dump()
    for ambiguity in response.ambiguities:
        if ambiguity.critical and not ambiguity.resolution:
            identity = ambiguity.requirement_id + ":" + ambiguity.decision_key
            ledger[_key("ambiguity", identity)] = ambiguity.model_dump()
    for finding in response.findings:
        if finding.severity == "blocking":
            identity = finding.category + ":" + finding.description
            ledger[_key("finding", identity)] = finding.model_dump()
    for scope in response.extra_scope:
        if not scope.approved:
            ledger[_key("scope", scope.description)] = scope.model_dump()
    return ledger


def validate_issue_ledger(
    batches: list[ReviewResponse], final: ReviewResponse, prepared: PreparedReview
) -> list[str]:
    """Reject erased issues, duplicate/foreign resolutions or invented grounding."""
    from validator.semantic.review_contract import _citation_errors

    initial = {key for batch in batches for key in issue_ledger(batch)}
    remaining = set(issue_ledger(final))
    keys = [resolution.issue_key for resolution in final.resolutions]
    errors = []
    if len(keys) != len(set(keys)) or not set(keys) <= initial:
        errors.append("duplicate_or_foreign_issue_resolution")
    if initial - remaining - set(keys):
        errors.append("unresolved_batch_issues_erased")
    # A synthesis cannot certify a pairing from a summary or an unseen source excerpt.
    observed = [
        citation
        for batch in batches
        for conclusion in batch.conclusions
        for citation in [*conclusion.source_citations, *conclusion.plan_citations]
    ]
    for conclusion in final.conclusions:
        for citation in [*conclusion.source_citations, *conclusion.plan_citations]:
            if not any(
                citation.section_id == seen.section_id and citation.excerpt in seen.excerpt
                for seen in observed
            ):
                errors.append("synthesis_citation_not_observed_in_batch")
    allowed = {s.section_id for s in prepared.sections}
    for resolution in final.resolutions:
        errors.extend(_citation_errors(resolution.citations, prepared, allowed))
    return errors
