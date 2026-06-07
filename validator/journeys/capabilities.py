"""Runner capability checks for User Journeys v2 compilation."""

# @spec FR-028: reject unsupported runner capabilities before writing artifacts
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#fr-028

from __future__ import annotations

from pathlib import Path

from .compiler_registry import supported_native_runners
from .models import JourneyIssue, JourneySeverity

UI_RUNNERS = supported_native_runners()


def validate_runner_capability(runner: str, journey_id: str) -> JourneyIssue | None:
    """Return a blocking issue when a runner cannot compile UI journey actions."""
    if runner in UI_RUNNERS:
        return None
    return JourneyIssue(
        code="journey_capability_unsupported",
        severity=JourneySeverity.ERROR,
        message=f"Runner {runner!r} cannot compile UI journey {journey_id}.",
        path=Path("."),
    )


__all__ = ["validate_runner_capability"]
