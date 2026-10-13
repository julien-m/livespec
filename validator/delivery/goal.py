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
    try:
        decision = evaluate_lane(
            project_root, feature, model, int(budget) if budget and budget.isdigit() else None
        )
    except DeliveryInputError:
        return None
    return decision.to_json()


def _flag_value(normalized_flags: list[str], name: str) -> str | None:
    return next(
        (flag.split("=", 1)[1] for flag in normalized_flags if flag.startswith(f"{name}=")), None
    )
