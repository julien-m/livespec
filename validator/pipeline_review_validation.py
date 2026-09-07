"""Read-only review prerequisites and identity guards for pipeline publication."""

from collections.abc import Callable, Collection, Sequence
from pathlib import Path

import typer

from .penflow_approval_files import BASELINE, PenflowApprovalError, bounded, load_object, read_ref
from .penflow_approval_models import RequirementsBaseline, ReviewApproval, ReviewResult
from .penflow_review_approval import has_approved_feature_history, validate_review_output
from .progression_gate import require_progression
from .visual_gate import detect_visual_feature

# Explicit internal entry points consumed only by the pipeline facade.
__all__ = ["_require_phase_progression", "_require_update_gates"]


# @spec FR-007: Publish reviewed authority after gate checks
# .specs/features/077-penflow-cumulative-verdict-consumer/spec.md#fr-007
def _review_for_update(
    feature_dir: Path,
    feature: str,
    phase: str,
    display_status: str,
    review_result: Path | None,
) -> Path | None:
    """Resolve the review prerequisite without publishing any files.

    The feature directory and slug select scope; phase/status select the transition.
    review_result is the optional supplied wrapper. Return the required wrapper
    or None for unrelated transitions. Raise PenflowApprovalError when required
    review evidence is absent;
    reader failures propagate to the command boundary.
    """
    if phase != "plan-review" or display_status != "Done":
        return None
    root = feature_dir.parents[2]
    visual = detect_visual_feature(project_root=root, feature_slug=feature)
    if (
        visual.classification != "NON_VISUAL"
        or review_result is not None
        or has_approved_feature_history(root, feature)
    ):
        if review_result is None:
            raise PenflowApprovalError("bound_review_result_required")
        return review_result
    return None


# @spec FR-006: Keep terminal authority certified
# .specs/features/077-penflow-cumulative-verdict-consumer/spec.md#fr-006
def _require_terminal_review_replay(root: Path, feature: str, review_result: Path) -> None:
    """Require an exact replay of the authority terminal closure will certify.

    root bounds every file read; feature identifies the original approval trigger;
    review_result references the caller's review wrapper. Return None on a match.
    Raise PenflowApprovalError for changed identity or raw output, and propagate
    malformed/unreadable input errors. This comparison publishes nothing.
    """
    baseline_path = bounded(root, BASELINE)
    if not baseline_path.is_file():
        raise PenflowApprovalError("terminal_review_requires_reopen")
    baseline = RequirementsBaseline.model_validate(load_object(baseline_path.read_bytes()))
    if len(baseline.approval_receipts) != 1:
        raise PenflowApprovalError("unsupported_approval_selection")
    approval = ReviewApproval.model_validate(
        load_object(read_ref(root, baseline.approval_receipts[0].model_dump(mode="json")))
    )
    candidate = ReviewResult.model_validate(load_object(bounded(root, review_result).read_bytes()))
    validate_review_output(root, candidate.review.model_dump(mode="json"))
    # Publication archives the raw output at another path; only that path may differ.
    same_review = candidate.review.model_dump(exclude={"output"}) == approval.review.model_dump(
        exclude={"output"}
    )
    if (
        approval.feature != feature
        or candidate.snapshot != approval.snapshot
        or not same_review
        or candidate.review.output.sha256 != approval.review.output.sha256
    ):
        raise PenflowApprovalError("terminal_review_requires_reopen")


def _require_update_gates(
    feature_dir: Path,
    feature: str,
    phase: str,
    display_status: str,
    content: str,
    build_manifest: Path | None,
    model: str,
    review_max_chars: int | None,
    review_result: Path | None,
    *,
    phase_order: Sequence[str],
    done_statuses: Collection[str],
    parse_pipeline: Callable[[str], dict[str, str]],
    check_closure: Callable[[Path, str, Path | None], None],
) -> Path | None:
    """Check the proposed phase transition without publishing review authority.

    feature_dir/feature select scope; phase/display_status/content describe the edit.
    build_manifest supplies closure proof; model/review_max_chars select current
    semantic identity; review_result is the supplied approval wrapper. phase_order,
    done_statuses and parse_pipeline interpret the existing state table. Injected
    check_closure enforces the existing facade closure authority.
    Return the review eligible for nonterminal publication, otherwise None. Propagate
    failed checks as ValueError or typer.Exit; caller retains the project lock.
    """
    review = _review_for_update(feature_dir, feature, phase, display_status, review_result)
    candidate = parse_pipeline(content)
    candidate[phase] = display_status
    terminal = all(candidate.get(item) in done_statuses for item in phase_order)
    if terminal and review is not None:
        _require_terminal_review_replay(feature_dir.parents[2], feature, review)
    if (phase == "test" and display_status in done_statuses) or terminal:
        check_closure(feature_dir, feature, build_manifest)
    if phase in {"clarify", "analyze"} and display_status == "Skipped":
        raise ValueError("required_progression_gate_cannot_be_skipped")
    if phase in {"plan", "implement", "test", "clarify", "analyze"} and display_status in {
        "Done",
        "In Progress",
        "Skipped",
    }:
        require_progression(
            feature_dir.parents[2], feature, phase, model=model, max_chars=review_max_chars
        )
    # A terminal replay already has this authority; do not reopen mutable review files to publish.
    return None if terminal else review


def _require_phase_progression(
    feature_dir: Path,
    feature: str,
    phase: str,
    model: str,
    review_max_chars: int | None,
) -> None:
    """Check the next phase through the current shared progression reader.

    feature_dir/feature select scope, phase selects the destination, and
    model/review_max_chars preserve the review identity. Return None when ready;
    convert a ValueError to BLOCKED stderr plus typer.Exit(1). No files are written.
    """
    try:
        require_progression(
            feature_dir.parents[2], feature, phase, model=model, max_chars=review_max_chars
        )
    except ValueError as exc:
        typer.echo(f"BLOCKED: {exc}", err=True)
        raise typer.Exit(1) from exc
