"""Delivery lane of an implement goal (feature 086 FR-007)."""

from __future__ import annotations

from pathlib import Path


# @spec FR-007: Delivery lane in the implement goal
#   — .specs/features/086-risk-proportional-delivery/spec.md#fr-007
def goal_delivery_lane(
    command: str, project_root: Path, feature: str | None, normalized_flags: list[str]
) -> dict[str, object] | None:
    """Return the lane decision for an implement goal of an existing feature, else None."""
    if command != "spec-implement" or not feature:
        return None
    from .lane import DeliveryInputError, evaluate_lane

    model = _flag_value(normalized_flags, "--model") or ""
    budget = _flag_value(normalized_flags, "--review-max-chars")
    # A malformed explicit budget becomes 0, which resolution refuses as out of bounds.
    explicit = None
    if budget is not None:
        explicit = int(budget) if budget.isascii() and budget.isdigit() else 0
    try:
        # Goal render binds the model or refuses a review-bearing goal (093); until
        # then an unresolved identity keeps the full lane.
        decision = evaluate_lane(project_root, feature, model, explicit, identity_required=False)
    except DeliveryInputError:
        return None
    return decision.to_json()


def _flag_value(normalized_flags: list[str], name: str) -> str | None:
    return next(
        (flag.split("=", 1)[1] for flag in normalized_flags if flag.startswith(f"{name}=")), None
    )
