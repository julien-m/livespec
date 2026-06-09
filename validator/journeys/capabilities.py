# LiveSpec traceability anchors
# @spec(FR-028)

"""Runner capability checks for User Journeys v2 compilation."""

# @spec FR-028: reject unsupported runner capabilities before writing artifacts
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#fr-028

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from .compiler_registry import supported_native_runners
from .models import JourneyIssue, JourneySeverity, JsonValue

UI_RUNNERS = supported_native_runners()
_COMMON_TARGET_ACTIONS = {"click", "assert", "assert_not", "fill"}
_PLAYWRIGHT_ACTIONS = _COMMON_TARGET_ACTIONS | {"open", "back", "press", "screenshot"}
_XCUITEST_ACTIONS = _COMMON_TARGET_ACTIONS | {"open", "back", "screenshot"}
_MAESTRO_ACTIONS = _COMMON_TARGET_ACTIONS | {"open", "back", "press"}
_RUNNER_ACTIONS = {
    "playwright": _PLAYWRIGHT_ACTIONS,
    "xcuitest": _XCUITEST_ACTIONS,
    "maestro": _MAESTRO_ACTIONS,
}


def validate_runner_capability(
    runner: str,
    journey_id: str,
    steps: list[dict[str, JsonValue]],
) -> JourneyIssue | None:
    """Return a blocking issue when a runner cannot compile every journey action."""
    if runner in UI_RUNNERS:
        return _unsupported_step_issue(runner, journey_id, steps)
    return JourneyIssue(
        code="journey_capability_unsupported",
        severity=JourneySeverity.ERROR,
        message=f"Runner {runner!r} cannot compile UI journey {journey_id}.",
        path=Path("."),
    )


def _unsupported_step_issue(
    runner: str,
    journey_id: str,
    steps: list[dict[str, JsonValue]],
) -> JourneyIssue | None:
    supported_actions = _RUNNER_ACTIONS.get(runner, set())
    for step in steps:
        if len(step) != 1:
            return _issue(
                runner,
                journey_id,
                "malformed step dictionary",
            )
        action, payload = next(iter(step.items()))
        if action not in supported_actions:
            return _issue(runner, journey_id, f"action {action!r}")
        if (
            action == "open"
            and runner == "xcuitest"
            and (not isinstance(payload, str) or not _is_url(payload))
        ):
            return _issue(
                runner,
                journey_id,
                "open action without a URL/deep link",
            )
        if action in _COMMON_TARGET_ACTIONS and not _has_target_payload(payload):
            return _issue(runner, journey_id, f"{action!r} action without a target")
        if action == "fill" and (
            not isinstance(payload, dict) or not isinstance(payload.get("value"), str)
        ):
            return _issue(runner, journey_id, "fill action without a text value")
        if action == "press" and (
            not isinstance(payload, dict) or not isinstance(payload.get("key"), str)
        ):
            return _issue(runner, journey_id, "press action without a key")
    return None


def _has_target_payload(payload: JsonValue) -> bool:
    if not isinstance(payload, dict):
        return False
    for key in ("test_id", "semantic_id", "accessibility_label", "name", "text", "label", "route"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return True
    return False


def _is_url(value: str) -> bool:
    parsed = urlparse(value)
    return bool(parsed.scheme and (parsed.netloc or parsed.path))


def _issue(runner: str, journey_id: str, unsupported: str) -> JourneyIssue:
    return JourneyIssue(
        code="journey_capability_unsupported",
        severity=JourneySeverity.ERROR,
        message=f"Runner {runner!r} cannot compile {unsupported} for UI journey {journey_id}.",
        path=Path("."),
    )


__all__ = ["validate_runner_capability"]
