# LiveSpec traceability anchors
# @spec(AC-001)
# @spec(AC-002)
# @spec(AC-003)
# @spec(AC-004)
# @spec(AC-006)
# @spec(AC-007)
# @spec(AC-011)
# @spec(AC-012)
# @spec(AC-013)
# @spec(AC-014)

"""Tests for the journey fixture bootstrap contract (feature 060)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]  # PyYAML has no typed metadata.

from validator.journeys.fixtures import (
    DEFAULT_BOOTSTRAP_TIMEOUT_SECONDS,
    BootstrapAmbiguityError,
    FixturesContractV1,
    fixtures_contract_hash,
    read_fixtures_contract,
    resolve_bootstrap,
)
from validator.journeys.paths import fixtures_contract_path
from validator.journeys.schema import JourneySourceV2

FULL_CONTRACT_YAML = """
schema_version: 1
bootstrap:
  ready_marker:
    ios: ui-test-bootstrap-ready
  timeout_seconds: 20
fixtures:
  session-workout:
    surfaces: [ios]
    expected_screen:
      ios: iphone-session-page
    required_markers:
      ios: [session-exercise-list]
  seed-only:
    surfaces: [ios, watchos]
mocks:
  storekit-pro:
    surfaces: [ios]
""".lstrip()

MINIMAL_CONTRACT_YAML = """
schema_version: 1
fixtures:
  seed-only:
    surfaces: [ios]
""".lstrip()


def _write_contract(project_root: Path, text: str) -> Path:
    path = fixtures_contract_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_fixtures_contract_path_is_project_local(tmp_path: Path) -> None:
    """FR-001: the contract lives at .specs/journeys/fixtures.yaml."""
    assert fixtures_contract_path(tmp_path) == tmp_path / ".specs" / "journeys" / "fixtures.yaml"


def test_read_full_contract_parses_models(tmp_path: Path) -> None:
    """AC-001: a full contract parses into frozen models with all maps."""
    _write_contract(tmp_path, FULL_CONTRACT_YAML)

    contract, issue = read_fixtures_contract(tmp_path)

    assert issue is None
    assert contract is not None
    assert contract.schema_version == 1
    assert contract.bootstrap is not None
    assert contract.bootstrap.ready_marker == {"ios": "ui-test-bootstrap-ready"}
    assert contract.bootstrap.timeout_seconds == 20
    fixture = contract.fixtures["session-workout"]
    assert fixture.surfaces == ["ios"]
    assert fixture.expected_screen == {"ios": "iphone-session-page"}
    assert fixture.required_markers == {"ios": ["session-exercise-list"]}
    assert contract.fixtures["seed-only"].expected_screen == {}
    assert contract.mocks["storekit-pro"].surfaces == ["ios"]


def test_read_minimal_contract_defaults(tmp_path: Path) -> None:
    """AC-001: omitting bootstrap means no ready_marker and default timeout 15."""
    _write_contract(tmp_path, MINIMAL_CONTRACT_YAML)

    contract, issue = read_fixtures_contract(tmp_path)

    assert issue is None
    assert contract is not None
    assert contract.bootstrap is None
    assert DEFAULT_BOOTSTRAP_TIMEOUT_SECONDS == 15
    assert contract.mocks == {}


def test_read_contract_absent_returns_none_pair(tmp_path: Path) -> None:
    """FR-001: an absent contract file is (None, None), not an error."""
    assert read_fixtures_contract(tmp_path) == (None, None)


def test_read_contract_invalid_yaml_is_blocking_issue(tmp_path: Path) -> None:
    """AC-001: invalid YAML yields journey_fixtures_contract_invalid."""
    _write_contract(tmp_path, "schema_version: [unclosed\n")

    contract, issue = read_fixtures_contract(tmp_path)

    assert contract is None
    assert issue is not None
    assert issue.code == "journey_fixtures_contract_invalid"


def test_read_contract_non_mapping_root_is_blocking_issue(tmp_path: Path) -> None:
    """AC-001: a non-mapping YAML root yields journey_fixtures_contract_invalid."""
    _write_contract(tmp_path, "- not\n- a\n- mapping\n")

    contract, issue = read_fixtures_contract(tmp_path)

    assert contract is None
    assert issue is not None
    assert issue.code == "journey_fixtures_contract_invalid"


def test_read_contract_rejects_unknown_keys(tmp_path: Path) -> None:
    """AC-001: extra keys are rejected by the frozen schema (extra=forbid)."""
    _write_contract(tmp_path, "schema_version: 1\nunknown_key: true\n")

    contract, issue = read_fixtures_contract(tmp_path)

    assert contract is None
    assert issue is not None
    assert issue.code == "journey_fixtures_contract_invalid"


def test_read_contract_rejects_out_of_bounds_timeouts(tmp_path: Path) -> None:
    """AC-001: timeout_seconds 0 and 61 are rejected at parse time."""
    for timeout in (0, 61):
        _write_contract(
            tmp_path,
            f"schema_version: 1\nbootstrap:\n  timeout_seconds: {timeout}\n",
        )

        contract, issue = read_fixtures_contract(tmp_path)

        assert contract is None
        assert issue is not None
        assert issue.code == "journey_fixtures_contract_invalid"


def test_fixtures_contract_hash_absent_and_stable(tmp_path: Path) -> None:
    """FR-001: the contract hash is "" when absent and a stable sha256 otherwise."""
    assert fixtures_contract_hash(tmp_path) == ""

    path = _write_contract(tmp_path, MINIMAL_CONTRACT_YAML)

    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    assert fixtures_contract_hash(tmp_path) == expected
    assert fixtures_contract_hash(tmp_path) == expected


def _journey_source(
    *,
    fixtures: list[str] | None = None,
    mocks: list[str] | None = None,
    bootstrap: dict[str, object] | None = None,
    surface: str = "ios",
) -> JourneySourceV2:
    preconditions: dict[str, object] = {}
    if fixtures:
        preconditions["fixtures"] = fixtures
    if mocks:
        preconditions["mocks"] = mocks
    if bootstrap is not None:
        preconditions["bootstrap"] = bootstrap
    return JourneySourceV2.model_validate(
        {
            "schema_version": 2,
            "id": "session-flow",
            "title": "Session flow",
            "description": "Fixture-backed session journey.",
            "covers": [
                {
                    "feature": "001-onboarding",
                    "kind": "ac",
                    "ref": "AC-001",
                    "reason": "Bootstrap proof.",
                }
            ],
            "run_policy": {"local": "impacted"},
            "targets": [{"surface": surface, "runner": "xcuitest"}],
            "preconditions": preconditions,
            "steps": [{"action": "assert", "target": {"test_id": "session-title"}}],
        }
    )


def _contract(text: str) -> FixturesContractV1:
    return FixturesContractV1.model_validate(yaml.safe_load(text))


MULTI_FIXTURE_CONTRACT = _contract(
    """
schema_version: 1
bootstrap:
  ready_marker:
    ios: ui-test-bootstrap-ready
  timeout_seconds: 20
fixtures:
  session-workout:
    surfaces: [ios]
    expected_screen:
      ios: iphone-session-page
    required_markers:
      ios: [session-exercise-list, shared-marker]
  session-history:
    surfaces: [ios]
    expected_screen:
      ios: iphone-session-page
    required_markers:
      ios: [history-list, shared-marker]
  other-screen:
    surfaces: [ios]
    expected_screen:
      ios: iphone-other-page
  seed-only:
    surfaces: [ios, watchos]
    expected_screen:
      watchos: watch-home
    required_markers:
      watchos: [watch-ring]
mocks:
  storekit-pro:
    surfaces: [ios]
"""
)


def test_resolve_bootstrap_single_fixture_full_plan() -> None:
    """AC-002: a single fixture derives ready, screen, markers, and timeout."""
    source = _journey_source(fixtures=["session-workout"])

    plan = resolve_bootstrap(source, MULTI_FIXTURE_CONTRACT, "ios")

    assert plan is not None
    assert plan.ready_marker == "ui-test-bootstrap-ready"
    assert plan.expected_screen == "iphone-session-page"
    assert plan.required_markers == ["session-exercise-list", "shared-marker"]
    assert plan.timeout_seconds == 20


def test_resolve_bootstrap_union_is_sorted_and_deduplicated() -> None:
    """AC-002: required_markers is the sorted deduplicated union across fixtures."""
    source = _journey_source(fixtures=["session-workout", "session-history"])

    plan = resolve_bootstrap(source, MULTI_FIXTURE_CONTRACT, "ios")

    assert plan is not None
    assert plan.required_markers == ["history-list", "session-exercise-list", "shared-marker"]
    assert plan.expected_screen == "iphone-session-page"


def test_resolve_bootstrap_zero_screens_omits_expected_screen() -> None:
    """AC-002: no fixture screen for the surface omits expected_screen."""
    source = _journey_source(fixtures=["seed-only"])

    plan = resolve_bootstrap(source, MULTI_FIXTURE_CONTRACT, "ios")

    assert plan is not None
    assert plan.expected_screen is None
    assert plan.ready_marker == "ui-test-bootstrap-ready"
    assert plan.required_markers == []


def test_resolve_bootstrap_ambiguous_screens_raise() -> None:
    """AC-003: two distinct screens without an override raise the domain error."""
    source = _journey_source(fixtures=["session-workout", "other-screen"])

    with pytest.raises(BootstrapAmbiguityError) as excinfo:
        resolve_bootstrap(source, MULTI_FIXTURE_CONTRACT, "ios")

    assert "iphone-other-page" in str(excinfo.value)
    assert "iphone-session-page" in str(excinfo.value)


def test_resolve_bootstrap_override_replaces_screen_and_appends_markers() -> None:
    """AC-004: the journey override replaces the screen and appends markers."""
    source = _journey_source(
        fixtures=["session-workout", "other-screen"],
        bootstrap={"expected_screen": "custom-screen", "required_markers": ["extra-marker"]},
    )

    plan = resolve_bootstrap(source, MULTI_FIXTURE_CONTRACT, "ios")

    assert plan is not None
    assert plan.expected_screen == "custom-screen"
    assert plan.required_markers == ["extra-marker", "session-exercise-list", "shared-marker"]


def test_resolve_bootstrap_no_fixtures_no_mocks_is_none() -> None:
    """AC-014: a journey without fixtures and mocks yields no plan."""
    source = _journey_source()

    assert resolve_bootstrap(source, MULTI_FIXTURE_CONTRACT, "ios") is None
    assert resolve_bootstrap(source, None, "ios") is None


def test_resolve_bootstrap_collapses_empty_plan_to_none() -> None:
    """AC-014: a plan with zero waits collapses to None (review finding #2)."""
    contract = _contract(
        """
schema_version: 1
fixtures:
  seed-only:
    surfaces: [ios]
"""
    )
    source = _journey_source(fixtures=["seed-only"])

    assert resolve_bootstrap(source, contract, "ios") is None


def test_resolve_bootstrap_seed_only_fixture_is_ready_only() -> None:
    """AC-002: a fixture without navigation yields a ready-marker-only plan."""
    contract = _contract(
        """
schema_version: 1
bootstrap:
  ready_marker:
    ios: ui-test-bootstrap-ready
fixtures:
  seed-only:
    surfaces: [ios]
"""
    )
    source = _journey_source(fixtures=["seed-only"])

    plan = resolve_bootstrap(source, contract, "ios")

    assert plan is not None
    assert plan.ready_marker == "ui-test-bootstrap-ready"
    assert plan.expected_screen is None
    assert plan.required_markers == []
    assert plan.timeout_seconds == DEFAULT_BOOTSTRAP_TIMEOUT_SECONDS


def test_resolve_bootstrap_only_reads_journey_surface_maps() -> None:
    """Edge case: other surfaces' screens and markers never leak into the plan."""
    source = _journey_source(fixtures=["seed-only"], mocks=["storekit-pro"])

    plan = resolve_bootstrap(source, MULTI_FIXTURE_CONTRACT, "ios")

    assert plan is not None
    assert plan.expected_screen is None
    assert plan.required_markers == []
    assert plan.ready_marker == "ui-test-bootstrap-ready"


def test_journey_schema_accepts_bootstrap_override() -> None:
    """AC-004: preconditions.bootstrap parses while schema_version stays 2."""
    source = _journey_source(
        fixtures=["session-workout"],
        bootstrap={"expected_screen": "custom-screen"},
    )

    assert source.schema_version == 2
    assert source.preconditions.bootstrap is not None
    assert source.preconditions.bootstrap.expected_screen == "custom-screen"
    assert source.preconditions.bootstrap.required_markers == []


def test_journey_schema_without_bootstrap_stays_valid() -> None:
    """AC-004: existing journeys without the bootstrap key remain valid."""
    source = _journey_source(fixtures=["session-workout"])

    assert source.preconditions.bootstrap is None


def _write_fixture_journey(
    specs: Path,
    *,
    journey_id: str = "session-flow",
    runner: str = "xcuitest",
    surface: str = "ios",
    fixtures: list[str] | None = None,
    mocks: list[str] | None = None,
    bootstrap_yaml: str = "",
) -> Path:
    journey_dir = specs / "journeys" / journey_id
    journey_dir.mkdir(parents=True, exist_ok=True)
    preconditions_lines = ["preconditions:"]
    if fixtures:
        preconditions_lines.append("  fixtures:")
        preconditions_lines.extend(f"    - {fixture_id}" for fixture_id in fixtures)
    if mocks:
        preconditions_lines.append("  mocks:")
        preconditions_lines.extend(f"    - {mock_id}" for mock_id in mocks)
    if bootstrap_yaml:
        preconditions_lines.append(bootstrap_yaml.rstrip())
    preconditions = "\n".join(preconditions_lines) if len(preconditions_lines) > 1 else ""
    source = journey_dir / "journey.yaml"
    source.write_text(
        f"""
schema_version: 2
id: {journey_id}
title: Session flow
status: active
description: Fixture-backed session journey.
covers:
  - feature: 001-onboarding
    kind: ac
    ref: AC-001
    reason: Bootstrap proof.
run_policy:
  local: impacted
targets:
  - surface: {surface}
    runner: {runner}
{preconditions}
steps:
  - action: assert
    target:
      test_id: session-title
privacy:
  llm_allowed: false
  retention: none
""".lstrip(),
        encoding="utf-8",
    )
    (journey_dir / "changelog.md").write_text(
        "# Changelog\n\n## 2026-06-11 - Created\n\n- Initial journey.\n",
        encoding="utf-8",
    )
    return source


def _project_with_fixture_journey(
    tmp_path: Path,
    *,
    contract_yaml: str | None = None,
    **journey_kwargs: object,
) -> Path:
    from tests.test_journey_v2_validation import _write_feature

    specs = tmp_path / ".specs"
    specs.mkdir(exist_ok=True)
    _write_feature(specs, "001-onboarding")
    _write_fixture_journey(specs, **journey_kwargs)  # type: ignore[arg-type]  # kwargs forwarded verbatim to the helper.
    if contract_yaml is not None:
        _write_contract(tmp_path, contract_yaml)
    return specs


def test_validation_missing_contract_embeds_skeleton(tmp_path: Path) -> None:
    """AC-006: missing contract blocks with a paste-ready YAML skeleton."""
    from validator.journeys.validator import validate_journeys

    _project_with_fixture_journey(
        tmp_path,
        fixtures=["session-workout"],
        mocks=["storekit-pro"],
    )

    result = validate_journeys(tmp_path)

    assert result.error_count == 1
    issue = result.issues[0]
    assert issue.code == "journey_fixture_contract_missing"
    assert "schema_version: 1" in issue.message
    assert "session-workout" in issue.message
    assert "storekit-pro" in issue.message
    assert "surfaces: [ios]" in issue.message


def test_validation_invalid_contract_is_blocking(tmp_path: Path) -> None:
    """AC-001: an invalid contract blocks validation of fixture journeys."""
    from validator.journeys.validator import validate_journeys

    _project_with_fixture_journey(
        tmp_path,
        contract_yaml="schema_version: 1\nbootstrap:\n  timeout_seconds: 0\n",
        fixtures=["session-workout"],
    )

    result = validate_journeys(tmp_path)

    assert result.error_count == 1
    assert result.issues[0].code == "journey_fixtures_contract_invalid"


def test_validation_unknown_fixture_and_mock_ids_block(tmp_path: Path) -> None:
    """AC-007: fixture or mock ids absent from the contract block validation."""
    from validator.journeys.validator import validate_journeys

    _project_with_fixture_journey(
        tmp_path,
        contract_yaml=FULL_CONTRACT_YAML,
        fixtures=["session-workout", "ghost-fixture"],
        mocks=["ghost-mock"],
    )

    result = validate_journeys(tmp_path)

    codes = [issue.code for issue in result.issues]
    assert codes.count("journey_fixture_unknown") == 2
    messages = " ".join(issue.message for issue in result.issues)
    assert "ghost-fixture" in messages
    assert "ghost-mock" in messages


def test_validation_surface_mismatch_blocks(tmp_path: Path) -> None:
    """AC-007: a journey surface outside the fixture's surfaces blocks."""
    from validator.journeys.validator import validate_journeys

    _project_with_fixture_journey(
        tmp_path,
        contract_yaml="""
schema_version: 1
fixtures:
  watch-only:
    surfaces: [watchos]
""".lstrip(),
        fixtures=["watch-only"],
    )

    result = validate_journeys(tmp_path)

    assert result.error_count == 1
    assert result.issues[0].code == "journey_fixture_surface_unsupported"


def test_validation_ambiguous_screens_block_without_override(tmp_path: Path) -> None:
    """AC-003: ambiguous expected screens block at validation time."""
    from validator.journeys.validator import validate_journeys

    contract_yaml = """
schema_version: 1
fixtures:
  fixture-a:
    surfaces: [ios]
    expected_screen:
      ios: screen-a
  fixture-b:
    surfaces: [ios]
    expected_screen:
      ios: screen-b
""".lstrip()
    _project_with_fixture_journey(
        tmp_path,
        contract_yaml=contract_yaml,
        fixtures=["fixture-a", "fixture-b"],
    )

    result = validate_journeys(tmp_path)

    assert result.error_count == 1
    assert result.issues[0].code == "journey_bootstrap_ambiguous"


def test_validation_ambiguous_screens_pass_with_override(tmp_path: Path) -> None:
    """Review finding #5: an expected_screen override resolves ambiguity."""
    from validator.journeys.validator import validate_journeys

    contract_yaml = """
schema_version: 1
fixtures:
  fixture-a:
    surfaces: [ios]
    expected_screen:
      ios: screen-a
  fixture-b:
    surfaces: [ios]
    expected_screen:
      ios: screen-b
""".lstrip()
    _project_with_fixture_journey(
        tmp_path,
        contract_yaml=contract_yaml,
        fixtures=["fixture-a", "fixture-b"],
        bootstrap_yaml="  bootstrap:\n    expected_screen: custom-screen",
    )

    result = validate_journeys(tmp_path)

    assert result.error_count == 0, [issue.code for issue in result.issues]


def test_validation_correctly_declared_journey_passes(tmp_path: Path) -> None:
    """AC-007: a journey fully covered by the contract passes validation."""
    from validator.journeys.validator import validate_journeys

    _project_with_fixture_journey(
        tmp_path,
        contract_yaml=FULL_CONTRACT_YAML,
        fixtures=["session-workout"],
        mocks=["storekit-pro"],
    )

    result = validate_journeys(tmp_path)

    assert result.error_count == 0, [issue.code for issue in result.issues]
    assert [journey.journey_id for journey in result.journeys] == ["session-flow"]


def test_validation_journey_without_fixtures_needs_no_contract(tmp_path: Path) -> None:
    """AC-014: journeys without fixtures and mocks require no contract."""
    from validator.journeys.validator import validate_journeys

    _project_with_fixture_journey(tmp_path)

    result = validate_journeys(tmp_path)

    assert result.error_count == 0, [issue.code for issue in result.issues]


def test_validation_non_xcuitest_journey_is_not_enforced(tmp_path: Path) -> None:
    """AC-007: enforcement is XCUITest-only in this feature."""
    from validator.journeys.validator import validate_journeys

    _project_with_fixture_journey(
        tmp_path,
        runner="playwright",
        surface="web",
        fixtures=["session-workout"],
    )

    result = validate_journeys(tmp_path)

    assert result.error_count == 0, [issue.code for issue in result.issues]


def test_validation_contract_deleted_after_compile_blocks(tmp_path: Path) -> None:
    """AC-006: deleting the contract after a compile re-blocks validation."""
    from validator.journeys.validator import validate_journeys

    _project_with_fixture_journey(
        tmp_path,
        contract_yaml=FULL_CONTRACT_YAML,
        fixtures=["session-workout"],
    )
    assert validate_journeys(tmp_path).error_count == 0
    fixtures_contract_path(tmp_path).unlink()

    result = validate_journeys(tmp_path)

    assert result.error_count == 1
    assert result.issues[0].code == "journey_fixture_contract_missing"


def test_scaffold_enumerates_ids_and_infers_surfaces(tmp_path: Path) -> None:
    """AC-011: scaffold lists every declared id with surfaces from targets."""
    from tests.test_journey_v2_validation import _write_feature
    from validator.journeys.fixtures import scaffold_fixtures_contract

    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_fixture_journey(
        specs,
        journey_id="session-flow",
        surface="ios",
        fixtures=["imported-workout"],
        mocks=["storekit-pro"],
    )
    _write_fixture_journey(
        specs,
        journey_id="watch-flow",
        surface="watchos",
        fixtures=["imported-workout", "watch-seed"],
    )

    written = scaffold_fixtures_contract(tmp_path)

    assert written == fixtures_contract_path(tmp_path)
    contract, issue = read_fixtures_contract(tmp_path)
    assert issue is None
    assert contract is not None
    assert sorted(contract.fixtures) == ["imported-workout", "watch-seed"]
    assert contract.fixtures["imported-workout"].surfaces == ["ios", "watchos"]
    assert contract.fixtures["watch-seed"].surfaces == ["watchos"]
    assert contract.mocks["storekit-pro"].surfaces == ["ios"]
    # Minimal valid contract: no bootstrap block, no screens, no markers.
    assert contract.bootstrap is None
    assert contract.fixtures["imported-workout"].expected_screen == {}
    assert contract.fixtures["imported-workout"].required_markers == {}


def test_scaffold_never_overwrites_existing_contract(tmp_path: Path) -> None:
    """AC-011: an existing contract is left byte-identical."""
    from validator.journeys.fixtures import scaffold_fixtures_contract

    path = _write_contract(tmp_path, FULL_CONTRACT_YAML)
    before = path.read_bytes()

    assert scaffold_fixtures_contract(tmp_path) is None
    assert path.read_bytes() == before


def test_scaffold_without_fixture_journeys_writes_nothing(tmp_path: Path) -> None:
    """AC-012: projects without fixture journeys get no contract file."""
    from tests.test_journey_v2_validation import _write_feature
    from validator.journeys.fixtures import scaffold_fixtures_contract

    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_fixture_journey(specs)

    assert scaffold_fixtures_contract(tmp_path) is None
    assert not fixtures_contract_path(tmp_path).exists()


def test_scaffold_round_trip_validates_and_compiles_without_waits(tmp_path: Path) -> None:
    """AC-011: the scaffolded contract validates and compiles wait-free."""
    from tests.test_journey_v2_validation import _write_feature
    from validator.journeys.compiler import compile_journeys
    from validator.journeys.fixtures import scaffold_fixtures_contract
    from validator.journeys.validator import validate_journeys

    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_fixture_journey(
        specs,
        fixtures=["imported-workout"],
        mocks=["storekit-pro"],
    )
    assert validate_journeys(tmp_path).error_count == 1  # blocked before scaffold

    written = scaffold_fixtures_contract(tmp_path)

    assert written is not None
    assert validate_journeys(tmp_path).error_count == 0
    result = compile_journeys(tmp_path, journey="session-flow", force=True)
    assert result.error_count == 0, [issue.message for issue in result.issues]
    artifact = tmp_path / "STRAPTUITests" / "Journeys" / "SessionFlowJourney.swift"
    assert "waitForJourneyBootstrap" not in artifact.read_text(encoding="utf-8")


def test_cli_journey_fixtures_scaffold_exit_codes_and_output(tmp_path: Path) -> None:
    """AC-013: the CLI subcommand follows project exit and output conventions."""
    import os

    from typer.testing import CliRunner

    from tests.test_journey_v2_validation import _write_feature
    from validator.cli import app

    cli_runner = CliRunner()
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_fixture_journey(specs, fixtures=["imported-workout"])
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        scaffolded = cli_runner.invoke(app, ["journey", "fixtures", "scaffold"])
        rerun = cli_runner.invoke(app, ["journey", "fixtures", "scaffold"])
    finally:
        os.chdir(cwd)

    assert scaffolded.exit_code == 0, scaffolded.output
    assert "scaffolded: .specs/journeys/fixtures.yaml" in scaffolded.output
    assert rerun.exit_code == 0, rerun.output
    assert "fixtures contract already present" in rerun.output


def test_cli_journey_fixtures_scaffold_no_fixture_journeys(tmp_path: Path) -> None:
    """AC-012: the no-op outcome without fixture journeys exits 0."""
    import os

    from typer.testing import CliRunner

    from tests.test_journey_v2_validation import _write_feature
    from validator.cli import app

    cli_runner = CliRunner()
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_fixture_journey(specs)
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = cli_runner.invoke(app, ["journey", "fixtures", "scaffold"])
    finally:
        os.chdir(cwd)

    assert result.exit_code == 0, result.output
    assert "no fixture journeys found" in result.output
    assert not fixtures_contract_path(tmp_path).exists()


MIGRATION_V21_MD = Path(__file__).resolve().parent.parent / "migrations" / "21" / "migrate.md"
SCAFFOLD_SCRIPT = (
    Path(__file__).resolve().parent.parent / "scripts" / "migrate-journeys-fixtures-scaffold.sh"
)


def test_migration_v21_manifest_structure() -> None:
    """AC-012: migrations/21 chains refresh, scaffold, compile, SET_VERSION 21."""
    assert MIGRATION_V21_MD.exists(), f"migrations/21/migrate.md not found at {MIGRATION_V21_MD}"
    content = MIGRATION_V21_MD.read_text(encoding="utf-8")
    assert "version: 21" in content
    assert "kind: asset-sync" in content
    agent_sync_index = content.index("RUN migrate-agent-sync.sh")
    scaffold_index = content.index("RUN migrate-journeys-fixtures-scaffold.sh")
    compile_index = content.index("RUN migrate-journeys-compile.sh")
    set_version_index = content.index("SET_VERSION 21")
    assert agent_sync_index < scaffold_index < compile_index < set_version_index


def test_migration_v21_scaffold_script_wrapper() -> None:
    """AC-012: the scaffold wrapper runs the versioned CLI via PYTHONPATH."""
    assert SCAFFOLD_SCRIPT.exists(), f"scaffold script not found at {SCAFFOLD_SCRIPT}"
    content = SCAFFOLD_SCRIPT.read_text(encoding="utf-8")
    assert "set -euo pipefail" in content
    assert "PYTHONPATH=" in content
    assert "journey fixtures scaffold" in content


def test_migration_shaped_scaffold_compile_round_trip(tmp_path: Path) -> None:
    """AC-012 / SC-006: version-20 fixture project migrates green end-to-end."""
    from tests.test_journey_v2_validation import _write_feature
    from validator.journeys.compiler import compile_journeys
    from validator.journeys.fixtures import scaffold_fixtures_contract

    specs = tmp_path / ".specs"
    specs.mkdir()
    (specs / "livespec-version").write_text("20\n", encoding="utf-8")
    _write_feature(specs, "001-onboarding")
    _write_fixture_journey(
        specs,
        fixtures=["imported-workout"],
        mocks=["storekit-pro"],
    )

    written = scaffold_fixtures_contract(tmp_path)

    assert written is not None
    first_bytes = written.read_bytes()
    result = compile_journeys(tmp_path, force=True)
    assert result.error_count == 0, [issue.message for issue in result.issues]
    artifact = tmp_path / "STRAPTUITests" / "Journeys" / "SessionFlowJourney.swift"
    assert "waitForJourneyBootstrap" not in artifact.read_text(encoding="utf-8")
    # Re-running the scaffold (e.g. migration replay) leaves the file untouched.
    assert scaffold_fixtures_contract(tmp_path) is None
    assert written.read_bytes() == first_bytes


def test_migration_shaped_project_without_fixture_journeys(tmp_path: Path) -> None:
    """AC-012: projects without fixture journeys migrate without a contract."""
    from tests.test_journey_v2_validation import _write_feature
    from validator.journeys.compiler import compile_journeys
    from validator.journeys.fixtures import scaffold_fixtures_contract

    specs = tmp_path / ".specs"
    specs.mkdir()
    (specs / "livespec-version").write_text("20\n", encoding="utf-8")
    _write_feature(specs, "001-onboarding")
    _write_fixture_journey(specs)

    assert scaffold_fixtures_contract(tmp_path) is None
    assert not fixtures_contract_path(tmp_path).exists()
    result = compile_journeys(tmp_path, force=True)
    assert result.error_count == 0, [issue.message for issue in result.issues]


@pytest.mark.chaos
def test_chaos_contract_binary_content_never_crashes(tmp_path: Path) -> None:
    """FR-001 chaos: binary contract content yields a structured issue."""
    path = fixtures_contract_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x00\xff\xfe\x00binary")

    contract, issue = read_fixtures_contract(tmp_path)

    assert contract is None
    assert issue is not None
    assert issue.code == "journey_fixtures_contract_invalid"


@pytest.mark.chaos
def test_chaos_contract_partial_yaml_never_crashes(tmp_path: Path) -> None:
    """FR-001 chaos: truncated YAML yields a structured issue."""
    _write_contract(tmp_path, "schema_version: 1\nfixtures:\n  broken:\n    surfaces: [ios\n")

    contract, issue = read_fixtures_contract(tmp_path)

    assert contract is None
    assert issue is not None
    assert issue.code == "journey_fixtures_contract_invalid"


@pytest.mark.chaos
def test_chaos_contract_huge_file_never_crashes(tmp_path: Path) -> None:
    """FR-001 chaos: an oversized contract is handled without crashing."""
    entries = "\n".join(f"  fixture-{index}:\n    surfaces: [ios]" for index in range(5000))
    _write_contract(tmp_path, f"schema_version: 1\nfixtures:\n{entries}\n")

    contract, issue = read_fixtures_contract(tmp_path)

    assert issue is None
    assert contract is not None
    assert len(contract.fixtures) == 5000
