"""Grounded semantic readiness consumed independently from reference coverage."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from validator.pre_impl_analysis import AnalyzeFinding, AnalyzeSeverity, _finding_id
from validator.review_source_identity import prepared_sources_current
from validator.semantic.review_context import PreparedReview


def _finding(category: str, summary: str, locations: tuple[str, ...] = ()) -> AnalyzeFinding:
    return AnalyzeFinding(
        finding_id=_finding_id(category, AnalyzeSeverity.HIGH, locations, summary),
        category=category,
        severity=AnalyzeSeverity.HIGH,
        locations=locations,
        summary=summary,
        recommendation="Refresh the complete independent plan review and resolve its findings",
    )


# @spec FR-004: Fresh semantic readiness
# — .specs/features/078-requirement-evidence-integrity/spec.md#fr-004


def analyze_semantic_readiness(
    feature_dir: Path,
    constitution_path: Path,
    receipt_path: Path | None,
    prepared: PreparedReview | None,
) -> tuple[str, list[AnalyzeFinding]]:
    """Reject absent, stale or incomplete receipts; never interpret prose heuristically."""
    from validator.semantic.review_receipts import load_review_receipt, verify_review_receipt

    path = receipt_path or feature_dir / ".reviews" / "plan.json"
    if not path.is_file():
        return "incomplete", [_finding("semantic", "Missing mandatory semantic review receipt")]
    try:
        if prepared is None:
            from validator.semantic.review_files import prepare_feature_review

            project_root = constitution_path.parent.parent
            prepared = prepare_feature_review(project_root, feature_dir.name, "plan")
        receipt = load_review_receipt(path)
        if (
            not prepared_sources_current(prepared, feature_dir, constitution_path)
            or not verify_review_receipt(receipt, prepared)
            or not receipt.complete
        ):
            return "incomplete", [
                _finding("semantic", "Stale, invalid or incomplete semantic review")
            ]
    except (OSError, ValueError, ValidationError) as error:
        return "incomplete", [_finding("semantic", f"Semantic review unavailable: {error}")]
    findings = [
        _finding(
            "semantic",
            f"{item.requirement_id}: {item.disposition}: {item.rationale}",
            tuple(
                citation.section_id for citation in (*item.source_citations, *item.plan_citations)
            ),
        )
        for item in receipt.conclusions
        if item.disposition != "covered"
    ]
    findings.extend(
        _finding("scope", item.description) for item in receipt.extra_scope if not item.approved
    )
    if not receipt.ready and not findings:
        findings.append(_finding("semantic", "Semantic review has unresolved blocking findings"))
    return ("blocked" if findings else "covered"), findings
