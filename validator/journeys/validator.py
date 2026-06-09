# LiveSpec traceability anchors
# @spec(FR-002)
# @spec(FR-004)
# @spec(FR-005)
# @spec(FR-006)
# @spec(FR-017)
# @spec(FR-018)

"""Project-aware validation for User Journeys v2 YAML sources."""

# @spec FR-006, FR-017, FR-018: qualified refs, project-aware validation, and doctor findings source
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#fr-017

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import yaml  # type: ignore[import-untyped]  # PyYAML has no typed metadata.
from pydantic import ValidationError

from .history import validate_history
from .models import JourneyFile, JourneyIssue, JourneySeverity, JsonValue, ValidationResult
from .paths import iter_journey_source_paths
from .schema import CoverageRefKind, JourneyAction, JourneySourceV2, RunPolicyValue

_AC_RE = re.compile(r"\*\*(AC-\d+):")
_FR_RE = re.compile(r"\*\*(FR-\d+):")


def validate_journeys(project_root: Path, feature: str | None = None) -> ValidationResult:
    """Validate all canonical v2 journey files under the project.

    Args:
        project_root: Project root containing `.specs/`.
        feature: Optional covered feature slug to filter valid journeys.

    Returns:
        Validation result with valid journeys and blocking issues.
    """
    journeys: list[JourneyFile] = []
    issues: list[JourneyIssue] = []
    for path in iter_journey_source_paths(project_root):
        journey, path_issues = validate_journey_file(project_root, path)
        issues.extend(path_issues)
        if journey is None:
            continue
        if feature is None or feature in journey.covered_features:
            journeys.append(journey)
    return ValidationResult(journeys=journeys, issues=issues)


def validate_journey_file(
    project_root: Path,
    path: Path,
) -> tuple[JourneyFile | None, list[JourneyIssue]]:
    """Validate one v2 `journey.yaml` source file."""
    try:
        raw_text = path.read_text(encoding="utf-8")
        raw_data = yaml.safe_load(raw_text)
    except (OSError, yaml.YAMLError) as exc:
        return None, [_issue("journey_yaml_invalid", JourneySeverity.ERROR, str(exc), path)]
    if not isinstance(raw_data, dict):
        return None, [
            _issue("journey_schema_invalid", JourneySeverity.ERROR, "root must be a map", path)
        ]
    try:
        source = JourneySourceV2.model_validate(raw_data)
    except ValidationError as exc:
        return None, [_issue("journey_schema_invalid", JourneySeverity.ERROR, str(exc), path)]

    source_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    issues = _validate_source_contract(project_root, path, source)
    issues.extend(validate_history(project_root, source.id, source_hash))
    if any(issue.severity == JourneySeverity.ERROR for issue in issues):
        return None, issues
    primary_feature = source.covers[0].feature
    return (
        JourneyFile(
            path=path,
            journey_id=source.id,
            feature=primary_feature,
            title=source.title,
            target_surface=source.targets[0].surface,
            run_policy=_primary_policy(source),
            runner=source.targets[0].runner.value,
            steps=_legacy_steps(source),
            schema_version=2,
            covered_features=sorted({cover.feature for cover in source.covers}),
            covers_ac=[cover.ref for cover in source.covers if cover.kind is CoverageRefKind.AC],
            covers_fr=[cover.ref for cover in source.covers if cover.kind is CoverageRefKind.FR],
            disabled=source.status.value == "disabled" or _primary_policy(source) == "disabled",
            manual_reason=None,
            source_hash=source_hash,
        ),
        issues,
    )


def _validate_source_contract(
    project_root: Path,
    path: Path,
    source: JourneySourceV2,
) -> list[JourneyIssue]:
    """Validate cross-file constraints after Pydantic schema parsing."""
    issues: list[JourneyIssue] = []
    if path.parent.name != source.id:
        issues.append(
            _issue(
                "journey_id_path_mismatch",
                JourneySeverity.ERROR,
                "journey id must match its directory name",
                path,
            )
        )
    changelog = path.parent / "changelog.md"
    if not changelog.exists():
        issues.append(
            _issue(
                "journey_changelog_missing",
                JourneySeverity.ERROR,
                "v2 journeys require changelog.md",
                changelog,
            )
        )
    for cover in source.covers:
        spec_path = project_root / ".specs" / "features" / cover.feature / "spec.md"
        if not spec_path.exists():
            issues.append(
                _issue(
                    "journey_feature_missing",
                    JourneySeverity.ERROR,
                    f"covered feature {cover.feature} is missing",
                    path,
                )
            )
            continue
        known_refs = _known_refs(spec_path, cover.kind)
        if cover.ref not in known_refs:
            issues.append(
                _issue(
                    "journey_requirement_missing",
                    JourneySeverity.ERROR,
                    f"{cover.feature} does not define {cover.ref}",
                    path,
                )
            )
    return issues


def _known_refs(spec_path: Path, kind: CoverageRefKind) -> set[str]:
    """Return requirement IDs declared in a feature spec file."""
    text = spec_path.read_text(encoding="utf-8", errors="ignore")
    return set(_AC_RE.findall(text) if kind is CoverageRefKind.AC else _FR_RE.findall(text))


def _primary_policy(source: JourneySourceV2) -> str:
    """Return the most representative policy for legacy category counts."""
    if RunPolicyValue.DISABLED in source.run_policy.values():
        return "disabled"
    if RunPolicyValue.MANUAL in source.run_policy.values():
        return "manual"
    if RunPolicyValue.ALWAYS in source.run_policy.values():
        return "always"
    if RunPolicyValue.SMOKE in source.run_policy.values():
        return "smoke"
    return "impacted"


def _legacy_steps(source: JourneySourceV2) -> list[dict[str, JsonValue]]:
    """Convert v2 action models into the existing compiler step shape."""
    steps: list[dict[str, JsonValue]] = []
    for step in source.steps:
        if step.action is JourneyAction.OPEN and step.target is not None:
            steps.append({"open": step.target.route or ""})
            continue
        payload: dict[str, JsonValue] = {}
        if step.target is not None:
            payload = step.target.model_dump(mode="json", exclude_none=True)
        if step.value is not None:
            payload["value"] = step.value
        if step.seconds is not None:
            payload["seconds"] = step.seconds
        if step.key is not None:
            payload["key"] = step.key
        steps.append({step.action.value: payload})
    return steps


def _issue(code: str, severity: JourneySeverity, message: str, path: Path) -> JourneyIssue:
    """Create a journey issue."""
    return JourneyIssue(code=code, severity=severity, message=message, path=path)
