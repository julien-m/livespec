"""Schema validation for canonical journey YAML sources."""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from .models import JourneyFile, JourneyIssue, JourneySeverity, JsonValue, ValidationResult
from .paths import iter_journey_paths

ALLOWED_ACTIONS = {
    # @spec FR-005: v1 journey actions
    # — .specs/features/056-executable-user-journeys/spec.md#fr-005
    "open",
    "click",
    "fill",
    "select",
    "wait",
    "assert",
    "assert_not",
    "screenshot",
    "back",
    "press",
}
RUN_POLICIES = {"always", "smoke", "manual", "disabled"}
SUPPORTED_SURFACES = {"web", "ios", "watchos", "android", "maestro"}


def validate_journeys(project_root: Path, feature: str | None = None) -> ValidationResult:
    """Validate all journey files under the project.

    Args:
        project_root: Project root containing `.specs/`.
        feature: Optional feature slug.

    Returns:
        Validation result with valid journeys and issues.
    """
    # @spec FR-002: Journey validation package
    # — .specs/features/056-executable-user-journeys/spec.md#fr-002
    journeys: list[JourneyFile] = []
    issues: list[JourneyIssue] = []
    for path in iter_journey_paths(project_root, feature):
        journey, path_issues = validate_journey_file(path)
        issues.extend(path_issues)
        if journey is not None:
            journeys.append(journey)
    return ValidationResult(journeys=journeys, issues=issues)


def validate_journey_file(path: Path) -> tuple[JourneyFile | None, list[JourneyIssue]]:
    """Validate one journey YAML file.

    Args:
        path: `.journey.yaml` source path.

    Returns:
        A tuple of parsed journey or `None`, plus validation issues.
    """
    issues: list[JourneyIssue] = []
    try:
        raw_text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw_text)
    except (OSError, yaml.YAMLError) as exc:
        return None, [_issue("journey_yaml_invalid", JourneySeverity.ERROR, str(exc), path)]
    if not isinstance(data, dict):
        return None, [
            _issue(
                "journey_schema_invalid",
                JourneySeverity.ERROR,
                "root must be a map",
                path,
            )
        ]

    journey_id = _required_str(data, "id", path, issues)
    feature = _required_str(data, "feature", path, issues)
    title = _required_str(data, "title", path, issues)
    run_policy = _optional_str(data, "run_policy", "always")
    disabled = bool(data.get("disabled", False)) or run_policy == "disabled"
    target_surface = _target_surface(data, path, issues)
    covers_ac, covers_fr = _covers(data)
    steps = _steps(data, path, issues)
    manual_reason = _optional_nullable_str(data, "manual_reason")

    if run_policy not in RUN_POLICIES:
        issues.append(
            _issue(
                "journey_run_policy_unknown",
                JourneySeverity.ERROR,
                f"unknown run_policy {run_policy!r}",
                path,
            )
        )
    if target_surface not in SUPPORTED_SURFACES:
        issues.append(
            _issue(
                "journey_target_unsupported",
                JourneySeverity.ERROR,
                f"unsupported target surface {target_surface!r}",
                path,
            )
        )
    if run_policy == "manual" and not manual_reason:
        issues.append(
            _issue(
                "journey_manual_reason_missing",
                JourneySeverity.ERROR,
                "manual journeys require manual_reason",
                path,
            )
        )

    if any(issue.severity == JourneySeverity.ERROR for issue in issues):
        return None, issues
    return (
        JourneyFile(
            path=path,
            journey_id=journey_id,
            feature=feature,
            title=title,
            target_surface=target_surface,
            run_policy=run_policy,
            steps=steps,
            covers_ac=covers_ac,
            covers_fr=covers_fr,
            disabled=disabled,
            manual_reason=manual_reason,
            source_hash=hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
        ),
        issues,
    )


def _steps(
    data: dict[object, object],
    path: Path,
    issues: list[JourneyIssue],
) -> list[dict[str, JsonValue]]:
    """Validate and normalize the journey step list."""
    raw_steps = data.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        issues.append(
            _issue(
                "journey_steps_missing",
                JourneySeverity.ERROR,
                "steps must be a non-empty list",
                path,
            )
        )
        return []

    steps: list[dict[str, JsonValue]] = []
    for index, raw_step in enumerate(raw_steps, start=1):
        if not isinstance(raw_step, dict) or len(raw_step) != 1:
            issues.append(
                _issue(
                    "journey_step_invalid",
                    JourneySeverity.ERROR,
                    f"step {index} must contain exactly one action",
                    path,
                )
            )
            continue
        action = next(iter(raw_step.keys()))
        if not isinstance(action, str):
            issues.append(
                _issue(
                    "journey_step_invalid",
                    JourneySeverity.ERROR,
                    f"step {index} action must be a string",
                    path,
                )
            )
            continue
        if action not in ALLOWED_ACTIONS:
            issues.append(
                _issue(
                    "journey_action_unknown",
                    JourneySeverity.ERROR,
                    f"unknown action {action!r} at step {index}",
                    path,
                )
            )
        value = raw_step[action]
        if action == "wait" and isinstance(value, dict):
            has_until = "until" in value
            has_reason = bool(value.get("reason"))
            if "seconds" in value and not has_until and not has_reason:
                issues.append(
                    _issue(
                        "wait_reason_missing",
                        JourneySeverity.WARNING,
                        f"wait.seconds at step {index} needs until or reason",
                        path,
                    )
                )
        steps.append({action: _json_value(value)})
    return steps


def _covers(data: dict[object, object]) -> tuple[list[str], list[str]]:
    """Extract covered AC and FR identifiers from the `covers` block."""
    covers = data.get("covers")
    if not isinstance(covers, dict):
        return [], []
    return _str_list(covers.get("ac")), _str_list(covers.get("fr"))


def _target_surface(
    data: dict[object, object],
    path: Path,
    issues: list[JourneyIssue],
) -> str:
    """Extract target.surface from the journey payload."""
    target = data.get("target")
    if not isinstance(target, dict):
        issues.append(
            _issue(
                "journey_target_missing",
                JourneySeverity.ERROR,
                "target.surface is required",
                path,
            )
        )
        return ""
    surface = target.get("surface")
    if not isinstance(surface, str) or not surface.strip():
        issues.append(
            _issue(
                "journey_target_missing",
                JourneySeverity.ERROR,
                "target.surface is required",
                path,
            )
        )
        return ""
    return surface.strip().lower()


def _required_str(
    data: dict[object, object],
    key: str,
    path: Path,
    issues: list[JourneyIssue],
) -> str:
    """Read a required string field and append an issue when missing."""
    value = data.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    issues.append(
        _issue(
            "journey_field_missing",
            JourneySeverity.ERROR,
            f"{key} is required",
            path,
        )
    )
    return ""


def _optional_str(data: dict[object, object], key: str, default: str) -> str:
    """Read an optional string field."""
    value = data.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else default


def _optional_nullable_str(data: dict[object, object], key: str) -> str | None:
    """Read an optional string field as `None` when absent or empty."""
    value = data.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _str_list(value: object) -> list[str]:
    """Return a list of strings from a YAML scalar list."""
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _json_value(value: object) -> JsonValue:
    """Convert YAML values into the supported JSON-like type."""
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return str(value)


def _issue(code: str, severity: JourneySeverity, message: str, path: Path) -> JourneyIssue:
    """Create a journey issue."""
    return JourneyIssue(code=code, severity=severity, message=message, path=path)
