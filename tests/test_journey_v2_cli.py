# LiveSpec traceability anchors
# @spec(AC-021)
# @spec(AC-023)
# @spec(AC-024)
# @spec(AC-025)
# @spec(AC-026)
# @spec(AC-028)
# @spec(AC-031)

"""CLI tests for User Journeys v2 commands."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from pytest import MonkeyPatch
from typer.testing import CliRunner

from tests.test_journey_v2_impact import _write_text_target_journey
from tests.test_journey_v2_runner import _setup_xcuitest_compiled_project
from tests.test_journey_v2_validation import _write_feature
from validator.cli import app
from validator.journeys.compiler import compile_journeys

runner = CliRunner()


def _setup_project(tmp_path: Path) -> Path:
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_text_target_journey(specs)
    return specs


def test_journey_validate_json_and_list_inspect(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """AC-023: validate/list/inspect expose v2 JSON output."""
    _setup_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    validate_result = runner.invoke(app, ["journey", "validate", "--json"])
    list_result = runner.invoke(app, ["journey", "list", "--json"])
    inspect_result = runner.invoke(
        app,
        ["journey", "inspect", "onboarding-first-project", "--json"],
    )

    assert validate_result.exit_code == 0, validate_result.output
    assert json.loads(validate_result.output)["summary"]["valid"] == 1
    assert json.loads(list_result.output)["journeys"][0]["id"] == "onboarding-first-project"
    assert json.loads(inspect_result.output)["id"] == "onboarding-first-project"


def test_journey_run_json_reports_stale_without_compiling(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """AC-028: CLI run reports stale compiled artifacts without compile side effects."""
    specs = _setup_project(tmp_path)
    compile_journeys(tmp_path, journey="onboarding-first-project")
    source = specs / "journeys" / "onboarding-first-project" / "journey.yaml"
    source.write_text(source.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["journey", "run", "--journey", "onboarding-first-project", "--json"],
    )

    assert result.exit_code == 1
    assert json.loads(result.output)["issues"][0]["code"] == "journey_compiled_stale"


def test_journey_run_json_includes_runs_array(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """FR-002: CLI JSON exposes destination and UDID records."""
    _setup_xcuitest_compiled_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LIVESPEC_XCODE_DESTINATION", "platform=iOS Simulator,id=IPHONE-17")

    def fake_run(
        argv: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    monkeypatch.setattr("validator.journeys.runner.subprocess.run", fake_run)

    result = runner.invoke(
        app,
        ["journey", "run", "--journey", "onboarding-first-project", "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.splitlines()[-1])
    assert payload["runs"][0]["udid"] == "IPHONE-17"
    assert payload["runs"][0]["destination"] == "platform=iOS Simulator,id=IPHONE-17"


def test_journey_impact_json_reports_changed_file(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """AC-026: impact command returns structured impacted journey records."""
    _setup_project(tmp_path)
    changed = tmp_path / "src" / "ProjectButton.tsx"
    changed.parent.mkdir()
    changed.write_text('"Create project"', encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["journey", "impact", "--changed-file", str(changed), "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output)["impacts"]
