"""High-level review API for automatic hook integration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from .review_contract import ReviewReceipt, validate_review_result
from .review_files import prepare_feature_review, review_receipt_path
from .review_receipts import load_review_receipt, save_review_receipt, verify_review_receipt

if TYPE_CHECKING:
    from validator.semantic.plan_review import PlanReviewResult
    from validator.semantic.spec_review import SpecReviewResult

logger = logging.getLogger(__name__)


# @spec FR-010: Python API, FR-011: Silent skip
# .specs/features/001-auto-llm-review/spec.md#fr-010
def review_spec_auto(
    feature_dir: Path,
) -> SpecReviewResult | None:
    """Review a spec.md automatically with graceful degradation.

    Intended for calling from spec-specify hooks. Never raises --
    returns None on any error.

    Args:
        feature_dir: Path to the feature directory containing spec.md.

    Returns:
        SpecReviewResult if review succeeded, None otherwise.
    """
    try:
        from validator.llm_provider import is_available
        from validator.semantic.spec_review import review_spec

        if not is_available():
            return None

        spec_path = feature_dir / "spec.md"
        if not spec_path.exists():
            logger.warning("spec.md not found at %s", spec_path)
            return None

        spec_content = spec_path.read_text()
        if not _has_project_context(feature_dir):
            return review_spec(spec_content)
        return review_spec(
            spec_content,
            prepared=prepare_feature_review(feature_dir.parents[2], feature_dir.name, "spec"),
            cache_path=review_receipt_path(feature_dir.parents[2], feature_dir.name, "spec"),
        )
    except Exception:
        logger.warning("Spec review failed for %s", feature_dir, exc_info=True)
        return None


# @spec FR-010: Python API, FR-011: Silent skip
# .specs/features/001-auto-llm-review/spec.md#fr-010
def review_plan_auto(
    feature_dir: Path,
) -> PlanReviewResult | None:
    """Review a plan.md automatically with graceful degradation.

    Intended for calling from spec-plan hooks. Never raises --
    returns None on any error.

    Args:
        feature_dir: Path to the feature directory containing plan.md
            and spec.md.

    Returns:
        PlanReviewResult if review succeeded, None otherwise.
    """
    try:
        from validator.llm_provider import is_available
        from validator.semantic.plan_review import review_plan

        if not is_available():
            return None

        spec_path = feature_dir / "spec.md"
        plan_path = feature_dir / "plan.md"

        if not spec_path.exists():
            logger.warning("spec.md not found at %s", spec_path)
            return None
        if not plan_path.exists():
            logger.warning("plan.md not found at %s", plan_path)
            return None

        spec_content = spec_path.read_text()
        plan_content = plan_path.read_text()

        # Read optional context files
        specs_root = feature_dir.parent.parent
        constitution_path = specs_root / "constitution.md"
        stack_path = specs_root / "stacks" / "_default.md"
        constitution = constitution_path.read_text() if constitution_path.exists() else ""
        stack = stack_path.read_text() if stack_path.exists() else ""

        if not _has_project_context(feature_dir):
            return review_plan(spec_content, plan_content, stack, constitution)
        return review_plan(
            spec_content=spec_content,
            plan_content=plan_content,
            stack_content=stack,
            constitution_content=constitution,
            prepared=prepare_feature_review(feature_dir.parents[2], feature_dir.name, "plan"),
            cache_path=review_receipt_path(feature_dir.parents[2], feature_dir.name, "plan"),
        )
    except Exception:
        logger.warning("Plan review failed for %s", feature_dir, exc_info=True)
        return None


def ingest_feature_review(
    project_root: Path,
    feature: str,
    kind: Literal["spec", "plan"],
    raw_results: list[str],
    synthesis: str | None = None,
    *,
    model: str = "",
    max_chars: int | None = None,
) -> tuple[ReviewReceipt, Path]:
    """Validate native reviewer output and persist its derived receipt.

    Args:
        project_root: Root containing the canonical .specs inputs.
        feature: Feature directory slug, confined to .specs/features.
        kind: Spec quality or plan compliance review to prepare.
        raw_results: Unmodified reviewer JSON for each prepared batch.
        synthesis: Unmodified final JSON when several batches require synthesis.
        model: Resolved reviewer identity; empty uses project configuration.
        max_chars: Submission budget override; None uses project configuration.

    Returns:
        Receipt and saved path, including an incomplete receipt on invalid output.

    Raises:
        ValueError: Invalid feature/configuration, budget, or linked destination.
        OSError: Configuration reading or atomic receipt publication fails.
        UnicodeError: Configuration bytes are not valid UTF-8.

    Side effects:
        Reads canonical inputs and atomically replaces the derived receipt;
        never invokes a provider.
    """
    prepared = prepare_feature_review(project_root, feature, kind, model, max_chars)
    receipt = validate_review_result(prepared, raw_results, synthesis)
    path = save_review_receipt(review_receipt_path(project_root, feature, kind), receipt)
    return receipt, path


# @spec FR-009: Bind review purpose to the immutable task obligation (078).
def verify_feature_review(
    project_root: Path,
    feature: str,
    path: Path,
    *,
    model: str = "",
    max_chars: int | None = None,
    expected_kind: Literal["spec", "plan"] | None = None,
) -> bool:
    """Check complete, current, ready raw evidence for the required review purpose.

    Args:
        project_root: Root containing the canonical .specs inputs.
        feature: Feature directory slug, confined to .specs/features.
        path: Existing receipt to read without following its final symlink.
        model: Current resolved identity; empty uses project configuration.
        max_chars: Submission budget override; None uses project configuration.
        expected_kind: Purpose from the obligation; None preserves legacy either-kind checks.

    Returns:
        True only for revalidated complete and ready evidence of the required kind.

    Raises:
        ValueError: Receipt JSON, configuration, feature scope, or kind is invalid.
        OSError: Receipt or configuration cannot be read, including linked receipts.
        UnicodeError: Receipt or configuration bytes are not valid UTF-8.

    Side effects:
        Reads receipt and current inputs; no writes or provider calls.
    """
    if expected_kind not in (None, "spec", "plan"):
        raise ValueError("invalid_expected_review_kind")
    receipt = load_review_receipt(path)
    kinds: tuple[Literal["spec", "plan"], ...] = (
        (expected_kind,) if expected_kind is not None else ("spec", "plan")
    )
    for kind in kinds:
        prepared = prepare_feature_review(project_root, feature, kind, model, max_chars)
        if verify_review_receipt(receipt, prepared):
            return receipt.ready
    return False


def _has_project_context(feature_dir: Path) -> bool:
    """Legacy standalone wrappers review supplied bytes without claiming project readiness."""
    specs = feature_dir.parent.parent
    return specs.name == ".specs" and all(
        (specs / name).is_file() for name in ("constitution.md", "project.md", "stacks/_default.md")
    )
