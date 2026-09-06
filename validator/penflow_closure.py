"""Enforce the final visual lifecycle boundary through Penflow authority."""

from __future__ import annotations

from pathlib import Path

from yaml import YAMLError

from .parser import parse_file
from .penflow_contract import get_penflow_contract_status
from .penflow_review_approval import has_approved_feature_history, require_approved_requirements
from .penflow_verification import VerificationProfile
from .visual_gate import detect_visual_feature


class PenflowClosureError(ValueError):
    """Current visual scope cannot be certified for final closure."""


# @spec FR-006: mandatory lifecycle certification
# .specs/features/077-penflow-cumulative-verdict-consumer/spec.md#fr-006
def require_penflow_closure(
    project_root: Path,
    feature_slug: str,
    *,
    build_manifest: Path | None = None,
) -> None:
    """Require fresh implementation certification for active visual features.

    Preparation callers do not invoke this final boundary. Nonvisual features
    retain their existing finalization; contradictory active signals require
    upstream repair. A readable current spec is required even for nonvisual
    work. Historical run and check archives are not visual signals.
    """
    spec_path = project_root / ".specs" / "features" / feature_slug / "spec.md"
    try:
        spec = parse_file(spec_path)
    except (OSError, UnicodeError, ValueError, TypeError, YAMLError) as exc:
        raise PenflowClosureError(f"visual_closure_spec_unreadable: {spec_path}: {exc}") from exc
    # Missing authority must not become NON_VISUAL through an empty signal set.
    if not spec.content.strip() and not spec.metadata:
        raise PenflowClosureError(f"visual_closure_spec_empty: {spec_path}")
    try:
        visual = detect_visual_feature(project_root=project_root, feature_slug=feature_slug)
        signals = visual.signals
        if signals.s1_spec_explicit_false and (signals.strong_count or signals.weak_count):
            raise PenflowClosureError(
                "visual_authority_conflict: active visual evidence with visual:false"
            )
        if visual.classification == "CONFLICT":
            raise PenflowClosureError(f"visual_authority_conflict: {visual.conflict_reason}")
        if visual.classification == "NON_VISUAL":
            if has_approved_feature_history(project_root, feature_slug):
                require_approved_requirements(project_root, feature_slug, disposition="retired")
            return
        status = get_penflow_contract_status(
            project_root,
            feature_slug=feature_slug,
            required_profile=VerificationProfile.IMPLEMENTATION,
            build_manifest=build_manifest,
        )
    except PenflowClosureError:
        raise
    except (OSError, RuntimeError, ValueError, YAMLError) as exc:
        raise PenflowClosureError(f"visual_closure_input_unreadable: {exc}") from exc
    if not status.certified:
        reason = status.verification.reason if status.verification else status.state
        raise PenflowClosureError(f"penflow_implementation_not_certified: {reason}")
