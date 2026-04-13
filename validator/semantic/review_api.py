"""High-level review API for automatic hook integration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

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

    Intended for calling from spec.specify hooks. Never raises --
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
        return review_spec(spec_content)
    except Exception:
        logger.warning("Spec review failed for %s", feature_dir, exc_info=True)
        return None


# @spec FR-010: Python API, FR-011: Silent skip
# .specs/features/001-auto-llm-review/spec.md#fr-010
def review_plan_auto(
    feature_dir: Path,
) -> PlanReviewResult | None:
    """Review a plan.md automatically with graceful degradation.

    Intended for calling from spec.plan hooks. Never raises --
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

        return review_plan(
            spec_content=spec_content,
            plan_content=plan_content,
            stack_content=stack,
            constitution_content=constitution,
        )
    except Exception:
        logger.warning("Plan review failed for %s", feature_dir, exc_info=True)
        return None
