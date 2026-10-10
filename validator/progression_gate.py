"""Shared source-backed direct and pipeline readiness (078 FR-015)."""

from __future__ import annotations

from pathlib import Path

from .clarify_inventory import collect_clarification_inventory
from .pre_impl_analysis import analyze_feature_artifacts, has_blocking_findings
from .semantic.review_files import prepare_feature_review, review_receipt_path


class ProgressionBlocked(ValueError):
    """Current source obligations do not permit the requested transition."""


def require_progression(
    project_root: Path,
    feature: str,
    destination: str,
    *,
    model: str = "",
    max_chars: int | None = None,
) -> None:
    """Recheck actual source and receipts without invoking another model or creating state."""
    if destination not in ("plan", "implement", "test", "complete", "clarify", "analyze"):
        raise ProgressionBlocked(f"unknown_progression_destination:{destination}")
    spec = project_root / ".specs/features" / feature / "spec.md"
    prepared = prepare_feature_review(project_root, feature, "spec", model, max_chars)
    inventory = collect_clarification_inventory(
        spec,
        review_receipt=review_receipt_path(project_root, feature, "spec"),
        prepared_review=prepared,
    )
    if inventory.blocking:
        unresolved = [
            item.question for item in inventory.inventory if item.critical and not item.resolution
        ]
        raise ProgressionBlocked("clarify_not_ready:" + ";".join([*inventory.errors, *unresolved]))
    if destination in ("implement", "test", "complete", "analyze"):
        prepared_plan = prepare_feature_review(project_root, feature, "plan", model, max_chars)
        report = analyze_feature_artifacts(
            spec.parent,
            project_root / ".specs/constitution.md",
            review_receipt=review_receipt_path(project_root, feature, "plan"),
            prepared_review=prepared_plan,
        )
        if has_blocking_findings(report):
            raise ProgressionBlocked(f"analyze_not_ready:{report.semantic_status}")
