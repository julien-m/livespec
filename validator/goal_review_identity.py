"""Bind resolved native review identity before saving a command goal (078 FR-009)."""

from __future__ import annotations

from pathlib import Path

from .goal_compile import normalize_goal_flags
from .goal_contracts import GoalContract, compile_command_goal


def flag_budget(flags: list[str] | tuple[str, ...] | str | None) -> int | None:
    """Return the ``--review-max-chars=`` goal flag, None when absent.

    Raises:
        ReviewIdentityError: The flag is not a decimal integer (feature 093).
    """
    from .semantic.review_identity_config import ReviewIdentityError

    items = normalize_goal_flags(flags)
    if "--review-max-chars" in items:
        # A value starting with "-" (such as -1) or none at all leaves the flag bare.
        detail = "--review-max-chars has no decimal integer value"
        raise ReviewIdentityError("review_max_chars_out_of_bounds", detail)
    prefix = "--review-max-chars="
    budget = next((flag[len(prefix) :] for flag in items if flag.startswith(prefix)), None)
    if budget is None:
        return None
    if not (budget.isascii() and budget.isdigit()):
        detail = f"--review-max-chars={budget[:40]!r} is not a decimal integer"
        raise ReviewIdentityError("review_max_chars_out_of_bounds", detail)
    return int(budget)


def flag_model(flags: list[str]) -> str:
    """Return the ``--model=`` goal flag, '' when absent.

    Raises:
        ReviewIdentityError: The flag has no value, so it never falls back to the
            configured model (feature 093).
    """
    from .semantic.review_identity_config import ReviewIdentityError

    prefix = "--model="
    model = next((flag[len(prefix) :] for flag in flags if flag.startswith(prefix)), None)
    # A value starting with "-" or none at all leaves the flag bare.
    if "--model" in flags or (model is not None and not model.strip()):
        detail = "--model has no value; pass --model=<model> or omit it to read review_model"
        raise ReviewIdentityError("review_model_required", detail)
    return model or ""


def bind_review_model(
    goal: GoalContract, project_root: Path, livespec_root: Path, feature: str | None
) -> GoalContract:
    """Resolve review identity before locking a goal, never from a later receipt.

    Raises:
        ReviewIdentityError: No option or configuration names a model, or a budget is
            out of bounds (feature 093).
    """
    if not any(
        task.get("evidence_kind") == "review"
        or "acceptance_review_receipt_path" in task.get("required_evidence", [])
        or "spec_review_receipt_path" in task.get("required_evidence", [])
        for task in goal.payload["tasks"]
    ):
        return goal
    from .semantic.review_identity_config import resolve_review_identity

    flags = list(goal.payload.get("normalized_flags") or [])
    supplied = flag_model(flags)
    # @spec FR-001: Goal render reads the configured identity
    #   — .specs/features/093-configured-review-identity/spec.md#fr-001
    model = resolve_review_identity(project_root, supplied, flag_budget(flags)).model
    if supplied:
        return goal
    return compile_command_goal(
        goal.command,
        project_root=project_root,
        livespec_root=livespec_root,
        feature=feature,
        flags=[*flags, f"--model={model}"],
    )
