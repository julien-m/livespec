"""Existing suites remain the only source of fixtures and assertions (feature 123)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError
from typer.testing import CliRunner

from tests.test_journey_v2_schema import _valid_source
from tests.test_journey_v2_validation import _write_feature
from validator.cli import app
from validator.journeys.compiler import compile_journeys
from validator.journeys.impact import analyze_journey_impacts
from validator.journeys.runner import run_journeys
from validator.journeys.scanner import scan_journeys
from validator.journeys.schema import JourneySourceV2
from validator.journeys.validator import validate_journeys


def _reference_project(root: Path, *, runner: str = "pytest", journey_id: str = "existing") -> Path:
    """Register an original test with its own fixture and nondefault test collection config."""
    _write_feature(root / ".specs", "001-onboarding")
    tests = root / "checks"
    tests.mkdir(exist_ok=True)
    (tests / "original.py").write_text(
        "from pathlib import Path\nimport pytest\n"
        "@pytest.fixture\ndef owned():\n    return 'owned-fixture'\n"
        "def case_original(owned):\n    assert owned == 'owned-fixture'\n"
        "    with Path('calls.txt').open('a') as out: out.write('ran\\n')\n"
        "def case_unselected():\n    raise AssertionError('must not run')\n"
    )
    (root / "suite.ini").write_text("[pytest]\npython_functions = case_*\n")
    data = JourneySourceV2.model_validate(_valid_source()).model_dump(mode="json")
    data.update(
        {
            "id": journey_id,
            "covers": [data["covers"][0]],
            "steps": [],
            "preconditions": {},
            "visual_checks": [],
            "targets": [{"surface": "web", "runner": runner}],
            "existing_test": {
                "path": "checks/original.py",
                "config": "suite.ini",
                "test_name": "case_original",
                "evidence_level": "unit-fixture",
            },
        }
    )
    directory = root / ".specs" / "journeys" / journey_id
    directory.mkdir(parents=True)
    source = directory / "journey.yaml"
    source.write_text(yaml.safe_dump(data))
    (directory / "changelog.md").write_text("# Adopted original suite\n")
    return source


@pytest.mark.integration
def test_real_pytest_suite_is_discovered_impacted_and_executed_once(tmp_path: Path) -> None:
    """Reference uses the real configured pytest collector and original fixture without codegen."""
    source = _reference_project(tmp_path)
    original = tmp_path / "checks/original.py"
    before = original.read_bytes()
    assert validate_journeys(tmp_path).error_count == 0
    assert compile_journeys(tmp_path).artifacts == []
    assert original.read_bytes() == before
    assert not (tmp_path / "tests/e2e/journeys").exists()
    assert not (source.parent / "compiled").exists()
    assert not any(f.code == "journey_compiled_missing" for f in scan_journeys(tmp_path).findings)
    impacts = analyze_journey_impacts(tmp_path, changed_files=[tmp_path / "suite.ini"])
    assert {impact.journey_id for impact in impacts} == {source.parent.name}
    _reference_project(tmp_path, journey_id="same-suite")
    result = run_journeys(tmp_path)
    assert result.error_count == 0, result.issues
    assert result.selection_status == "completed"
    assert len(result.runs) == 1
    assert result.reused == {"same-suite": "existing"}
    assert set(result.executed) == {"existing", "same-suite"}
    assert (tmp_path / "calls.txt").read_text() == "ran\n"
    assert original.read_bytes() == before
    assert result.runs[0].evidence_level == "unit-fixture"
    receipt = json.loads((source.parent / "runs/last-run.json").read_text())
    assert "suite.ini" in receipt["command"]
    assert receipt["evidence_level"] == "unit-fixture"


def test_empty_and_dry_run_never_claim_execution(tmp_path: Path) -> None:
    """An empty catalogue and a planned reference are observable distinct outcomes."""
    assert run_journeys(tmp_path).selection_status == "no_selection"
    _reference_project(tmp_path)
    result = run_journeys(tmp_path, execute=False)
    assert result.selection_status == "planned"
    assert result.executed == result.runs == []
    assert result.planned == ["existing"]
    assert result.planned_commands["existing"][-2:] == ["-k", "case_original"]
    assert not (tmp_path / "calls.txt").exists()
    assert run_journeys(tmp_path, feature="unknown").selection_status == "no_selection"


@pytest.mark.parametrize(
    "change",
    [
        {"steps": [{"action": "back"}]},
        {"preconditions": {"fixtures": ["invented"]}},
        {"existing_test": {"path": "../outside.py", "evidence_level": "unit"}},
        {"existing_test": {"path": "--help", "evidence_level": "unit"}},
        {"existing_test": {"path": "checks/original.py", "evidence_level": " "}},
        {"targets": [{"surface": "ios", "runner": "xcuitest"}]},
    ],
)
def test_reference_rejects_mixed_or_unsafe_configuration(tmp_path: Path, change: dict) -> None:
    source = _reference_project(tmp_path)
    data = yaml.safe_load(source.read_text())
    data.update(change)
    with pytest.raises(ValidationError):
        JourneySourceV2.model_validate(data)


@pytest.mark.parametrize("field", ["path", "config"])
def test_missing_and_external_symlink_files_fail_without_execution(
    tmp_path: Path, field: str
) -> None:
    source = _reference_project(tmp_path)
    data = yaml.safe_load(source.read_text())
    data["existing_test"][field] = "missing.py"
    source.write_text(yaml.safe_dump(data))
    assert run_journeys(tmp_path).selection_status == "failed"
    outside = tmp_path.parent / (tmp_path.name + "-external.py")
    outside.write_text("raise AssertionError('outside')\n")
    try:
        (tmp_path / "missing.py").symlink_to(outside)
        assert validate_journeys(tmp_path).error_count > 0
        assert run_journeys(tmp_path).executed == []
    finally:
        outside.unlink()
    assert not (tmp_path / "calls.txt").exists()


@pytest.mark.integration
def test_real_runner_failure_and_empty_test_selector_are_not_success(tmp_path: Path) -> None:
    source = _reference_project(tmp_path)
    data = yaml.safe_load(source.read_text())
    for selector in ("unselected", "does_not_exist"):
        data["existing_test"]["test_name"] = selector
        source.write_text(yaml.safe_dump(data))
        result = run_journeys(tmp_path)
        assert result.selection_status == "failed"
        assert result.executed == []
        assert result.issues[0].code == "journey_native_run_failed"


def test_cli_lists_reference_and_reports_empty_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _reference_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    cli = CliRunner()
    listing = cli.invoke(app, ["journey", "list", "--json"])
    assert listing.exit_code == 0, listing.output
    item = json.loads(listing.output)["journeys"][0]
    assert item["execution_mode"] == "reference"
    assert item["existing_test"]["config"] == "suite.ini"
    result = cli.invoke(app, ["journey", "run", "--feature", "missing", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["selection_status"] == "no_selection"


def test_deleted_reference_still_has_impact(tmp_path: Path) -> None:
    _reference_project(tmp_path)
    original = tmp_path / "checks/original.py"
    original.unlink()
    assert analyze_journey_impacts(tmp_path, changed_files=[original])


def test_vitest_and_playwright_build_literal_owned_runner_commands(tmp_path: Path) -> None:
    from validator.journeys.existing_tests import reference_command
    from validator.journeys.schema import ExistingTestReference

    _reference_project(tmp_path)
    reference = ExistingTestReference(
        path="checks/original.py",
        config="suite.ini",
        test_name="one & two",
        evidence_level="mocked-web",
    )
    assert reference_command(tmp_path, "playwright", reference) == [
        "npx",
        "--no-install",
        "playwright",
        "test",
        f"^{re.escape(str((tmp_path / 'checks/original.py').resolve()))}$",
        "--config",
        "suite.ini",
        "--grep",
        "one & two",
    ]
    command = reference_command(tmp_path, "vitest", reference)
    assert command[0] == "node"
    assert command[1].endswith("vitest-reference.mjs")
    assert json.loads(command[2]) == {
        "path": "checks/original.py",
        "config": "suite.ini",
        "test_name": "one & two",
    }


@pytest.mark.integration
@pytest.mark.parametrize("runner", ["playwright", "vitest"])
def test_real_node_runner_preserves_original_suite_and_setup(tmp_path: Path, runner: str) -> None:
    """Run actual local Node runners; no browser/native display proof is claimed."""
    import os

    modules = os.environ.get("LIVESPEC_NODE_TEST_MODULES")
    if not modules:
        pytest.skip("Set LIVESPEC_NODE_TEST_MODULES to existing local runner dependencies")
    source = _reference_project(tmp_path, runner=runner)
    (tmp_path / "node_modules").symlink_to(Path(modules), target_is_directory=True)
    suite = tmp_path / "checks" / "original.spec.mjs"
    config = tmp_path / "owned.config.mjs"
    if runner == "playwright":
        config.write_text("export default {testDir:'./checks',workers:1};\n")
        suite.write_text(
            "import {test as base,expect} from '@playwright/test';\n"
            "import {appendFileSync} from 'node:fs';\n"
            "const test=base.extend({owned:async({},use)=>{await use('fixture');}});\n"
            "test('selected original',async({owned})=>{expect(owned).toBe('fixture');"
            "appendFileSync('calls.txt','ran\\n');});\n"
            "test('unselected',()=>{throw Error('wrong selection');});\n"
        )
    else:
        config.write_text(
            "export default {test:{include:['checks/*.spec.mjs'],"
            "passWithNoTests:true,outputFile:'report.json'}};\n"
        )
        suite.write_text(
            "import {test,expect,beforeEach} from 'vitest';\n"
            "import {appendFileSync} from 'node:fs';\n"
            "let owned;beforeEach(()=>{owned='fixture';});\n"
            "test('selected original',()=>{expect(owned).toBe('fixture');"
            "appendFileSync('calls.txt','ran\\n');});\n"
            "test('unselected',()=>{throw Error('wrong selection');});\n"
        )
    data = yaml.safe_load(source.read_text())
    data["existing_test"].update(
        path="checks/original.spec.mjs",
        config="owned.config.mjs",
        test_name="selected original",
        evidence_level="runner-only",
    )
    source.write_text(yaml.safe_dump(data))
    _reference_project(tmp_path, runner=runner, journey_id="second")
    second = source.parent.parent / "second" / "journey.yaml"
    second_data = yaml.safe_load(second.read_text())
    second_data["existing_test"] = data["existing_test"]
    second.write_text(yaml.safe_dump(second_data))
    sibling = suite.with_name(suite.name + "-extra.spec.mjs")
    sibling.write_text("throw Error('neighbor suite must not be imported');\n")
    before = suite.read_bytes()
    result = run_journeys(tmp_path)
    assert result.error_count == 0, [issue.message for issue in result.issues]
    assert result.reused == {"second": "existing"}
    assert len(result.runs) == 1
    assert (tmp_path / "calls.txt").read_text() == "ran\n"
    assert suite.read_bytes() == before
    assert not (tmp_path / "report.json").exists()
    assert not (tmp_path / "tests/e2e/journeys").exists()
    data["existing_test"]["test_name"] = "not present"
    source.write_text(yaml.safe_dump(data))
    missing = run_journeys(tmp_path, journey="existing")
    assert missing.error_count > 0
    assert missing.executed == []


def test_structured_results_accept_successful_retries_and_reject_empty_or_invalid(
    tmp_path: Path,
) -> None:
    from validator.journeys.existing_tests import reference_result_error

    missing = tmp_path / "unused.xml"
    flaky = json.dumps({"stats": {"expected": 0, "flaky": 1}})
    assert reference_result_error("playwright", flaky, missing) is None
    for runner, output in [
        ("playwright", '{"stats":{"expected":0,"flaky":0,"skipped":1}}'),
        ("vitest", '{"numPassedTests":0}'),
    ]:
        error = reference_result_error(runner, output, missing)
        assert error is not None and error[0] == "journey_no_tests_executed"
    for runner in ("playwright", "vitest", "pytest"):
        error = reference_result_error(runner, "not a result", missing)
        assert error is not None and error[0] == "journey_test_results_invalid"


@pytest.mark.integration
def test_shared_failed_reference_executes_once_and_preserves_failure(tmp_path: Path) -> None:
    _reference_project(tmp_path)
    _reference_project(tmp_path, journey_id="second")
    original = tmp_path / "checks/original.py"
    original.write_text(
        original.read_text().replace("out.write('ran\\n')", "out.write('ran\\n'); assert False")
    )
    result = run_journeys(tmp_path)
    assert result.selection_status == "failed"
    assert result.executed == []
    assert result.reused == {"second": "existing"}
    assert len(result.runs) == 1
    assert len(result.issues) == 2
    assert (tmp_path / "calls.txt").read_text() == "ran\n"
