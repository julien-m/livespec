"""Shared source-backed direct and pipeline readiness (078 FR-015)."""

from __future__ import annotations

from pathlib import Path

from .clarify_inventory import collect_clarification_inventory
from .delivery.revision import RevisionUnverified, accepted_reviews, read_revision
from .pre_impl_analysis import analyze_feature_artifacts, has_blocking_findings
from .release_evidence import pending_release_evidence, release_evidence_errors
from .semantic.review_files import prepare_feature_review, review_receipt_path

# ``ship`` is ``complete`` plus the release evidence the plan deferred (090).
PROGRESSION_DESTINATIONS = ("plan", "implement", "test", "complete", "ship", "clarify", "analyze")


class ProgressionBlocked(ValueError):
    """Current source obligations do not permit the requested transition."""


def _accepted(project_root: Path, feature: str, destination: str) -> frozenset[str]:
    """Receipts an open spec revision lets ``implement`` and ``test`` accept (089, 094)."""
    try:
        record = read_revision(project_root, feature)
        verify = record is not None and destination in ("implement", "test")
        accepted = accepted_reviews(project_root, feature) if verify else frozenset()
    except RevisionUnverified as exc:
        raise ProgressionBlocked(str(exc)) from exc
    except ValueError as exc:
        raise ProgressionBlocked(f"spec_revision_malformed:{exc}") from exc
    if record is not None and destination == "complete":
        raise ProgressionBlocked("spec_revision_open")
    return accepted


def require_progression(
    project_root: Path,
    feature: str,
    destination: str,
    *,
    model: str = "",
    max_chars: int | None = None,
) -> None:
    """Recheck actual source and receipts without invoking another model or creating state."""
    if destination not in PROGRESSION_DESTINATIONS:
        raise ProgressionBlocked(f"unknown_progression_destination:{destination}")
    if destination == "ship":
        # An unreadable plan or implementation map blocks shipping with a code, not a raw error.
        try:
            require_progression(project_root, feature, "complete", model=model, max_chars=max_chars)
            _require_release_evidence(project_root, feature)
        except OSError as exc:
            reason = f"{type(exc).__name__}: {exc.strerror or exc}"
            raise ProgressionBlocked("release_evidence_unreadable:" + reason) from exc
        return
    spec = project_root / ".specs/features" / feature / "spec.md"
    # @spec FR-005: Progressions during a spec revision
    #   — .specs/features/089-stable-review-identity/spec.md#fr-005
    accepted = _accepted(project_root, feature, destination)
    prepared = prepare_feature_review(project_root, feature, "spec", model, max_chars)
    inventory = collect_clarification_inventory(
        spec,
        review_receipt=review_receipt_path(project_root, feature, "spec"),
        prepared_review=prepared,
        accepted_reviews=accepted,
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
            accepted_reviews=accepted,
        )
        if has_blocking_findings(report):
            raise ProgressionBlocked(f"analyze_not_ready:{report.semantic_status}")


# @spec FR-002: spec-ship requires release evidence
#   — .specs/features/090-minimal-plan-scope/spec.md#fr-002
def _require_release_evidence(project_root: Path, feature: str) -> None:
    """Shipping needs a valid plan and a recorded proof for every release-class plan step.

    A plan whose evidence classes do not validate fails closed: an unreadable declaration
    could hide a release step.
    """
    errors = release_evidence_errors(project_root, feature)
    if errors:
        raise ProgressionBlocked("release_evidence_invalid:" + ";".join(errors))
    pending = pending_release_evidence(project_root, feature)
    if pending:
        steps = ";".join(f"step {item['step']}: {item['evidence']}" for item in pending)
        raise ProgressionBlocked("release_evidence_pending:" + steps)
