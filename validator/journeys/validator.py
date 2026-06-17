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

from .fixtures import (
    BootstrapAmbiguityError,
    FixtureContract,
    FixturesContractV1,
    MockContract,
    read_fixtures_contract,
    render_contract_skeleton,
    resolve_bootstrap,
)
from .history import validate_history
from .models import JourneyFile, JourneyIssue, JourneySeverity, JsonValue, ValidationResult
from .paths import fixtures_contract_path, iter_journey_source_paths
from .schema import (
    CoverageRefKind,
    JourneyAction,
    JourneyRunner,
    JourneySourceV2,
    RunPolicyValue,
)

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
    issues.extend(_validate_fixtures_contract(project_root, path, source))
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


def _validate_fixtures_contract(
    project_root: Path,
    path: Path,
    source: JourneySourceV2,
) -> list[JourneyIssue]:
    """Enforce the fixtures bootstrap contract for XCUITest fixture journeys."""
    # @spec FR-004: Five blocking fixture-contract validation rules
    # — .specs/features/060-journey-fixture-bootstrap-contract/spec.md#fr-004
    preconditions = source.preconditions
    # Exemption: journeys without fixtures and mocks never require a contract
    # (AC-014); Playwright/Maestro enforcement is deferred to a future feature.
    if not preconditions.fixtures and not preconditions.mocks:
        return []
    xcuitest_surfaces = sorted(
        {target.surface for target in source.targets if target.runner is JourneyRunner.XCUITEST}
    )
    if not xcuitest_surfaces:
        return []
    contract, contract_issue = read_fixtures_contract(project_root)
    if contract_issue is not None:
        return [contract_issue]
    if contract is None:
        skeleton = render_contract_skeleton(
            preconditions.fixtures,
            preconditions.mocks,
            xcuitest_surfaces,
        )
        return [
            _issue(
                "journey_fixture_contract_missing",
                JourneySeverity.ERROR,
                "journey declares fixtures/mocks but .specs/journeys/fixtures.yaml "
                f"is missing. Paste-ready skeleton:\n{skeleton}",
                fixtures_contract_path(project_root),
            )
        ]
    issues = _validate_contract_references(path, source, contract, xcuitest_surfaces)
    issues.extend(_validate_bootstrap_resolution(path, source, contract, xcuitest_surfaces))
    return issues


def _validate_contract_references(
    path: Path,
    source: JourneySourceV2,
    contract: FixturesContractV1,
    xcuitest_surfaces: list[str],
) -> list[JourneyIssue]:
    """Check declared fixture/mock ids and surfaces against the contract maps."""
    issues: list[JourneyIssue] = []
    issues.extend(
        _validate_reference_surfaces(
            path,
            ids=source.preconditions.fixtures,
            entries=contract.fixtures,
            reference_kind="fixture",
            xcuitest_surfaces=xcuitest_surfaces,
        )
    )
    issues.extend(
        _validate_reference_surfaces(
            path,
            ids=source.preconditions.mocks,
            entries=contract.mocks,
            reference_kind="mock",
            xcuitest_surfaces=xcuitest_surfaces,
        )
    )
    return issues


def _validate_reference_surfaces(
    path: Path,
    *,
    ids: list[str],
    entries: dict[str, FixtureContract] | dict[str, MockContract],
    reference_kind: str,
    xcuitest_surfaces: list[str],
) -> list[JourneyIssue]:
    issues: list[JourneyIssue] = []
    for reference_id in ids:
        entry = entries.get(reference_id)
        if entry is None:
            issues.append(
                _issue(
                    "journey_fixture_unknown",
                    JourneySeverity.ERROR,
                    f"{reference_kind} '{reference_id}' is not declared in fixtures.yaml",
                    path,
                )
            )
            continue
        for surface in xcuitest_surfaces:
            if surface not in entry.surfaces:
                issues.append(
                    _issue(
                        "journey_fixture_surface_unsupported",
                        JourneySeverity.ERROR,
                        f"{reference_kind} '{reference_id}' does not support surface "
                        f"'{surface}' (declared: {', '.join(entry.surfaces)})",
                        path,
                    )
                )
    return issues


def _validate_bootstrap_resolution(
    path: Path,
    source: JourneySourceV2,
    contract: FixturesContractV1,
    xcuitest_surfaces: list[str],
) -> list[JourneyIssue]:
    """Dry-run resolve_bootstrap per surface to surface ambiguity at validation."""
    issues: list[JourneyIssue] = []
    for surface in xcuitest_surfaces:
        try:
            resolve_bootstrap(source, contract, surface)
        except BootstrapAmbiguityError as error:
            issues.append(
                _issue(
                    "journey_bootstrap_ambiguous",
                    JourneySeverity.ERROR,
                    f"surface '{surface}': {error}",
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
