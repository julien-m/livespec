"""Actual native gate commands terminate locally and accept canonical phase aliases."""

import json
import shlex
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.execution_evidence_support import FEATURE
from tests.execution_evidence_support import project as project
from tests.review_support import reviewed_project
from validator.cli import app


@pytest.mark.parametrize("mode", ["prepare", "ingest", "execute"])
def test_execution_mode_emits_one_json_without_coverage_fallthrough(
    project: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    monkeypatch.chdir(project)
    command = ["test", "--feature", FEATURE, "--acceptance-mapping", "mapping.json"]
    if mode == "prepare":
        command += ["--prepare-mapping-review"]
    elif mode == "ingest":
        receipt = json.loads((project / "acceptance-review.json").read_text())
        bundle = project / "bundle.json"
        bundle.write_text(json.dumps({"raw_results": receipt["raw_results"]}))
        command += ["--ingest-mapping-review", str(bundle)]
    else:
        command += [
            "--execution-command",
            f"{shlex.quote(sys.executable)} -m pytest test_app.py -q",
        ]
    result = CliRunner().invoke(app, command, catch_exceptions=False)
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    if mode == "prepare":
        assert payload["prepared"]["errors"] == []
    elif mode == "ingest":
        assert payload["ready"] is True
    else:
        assert payload["valid"] is True
        assert payload["certified_acs"] == [f"{FEATURE}:AC-001"]
    assert not (project / ".specs/features" / FEATURE / "checks").exists()


def test_ready_clarify_returns_one_inventory_without_review_fallthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    feature = reviewed_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        app, ["validate", str(feature), "--clarify"], catch_exceptions=False
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["blocking"] is False
    assert payload["review_complete"] is True


@pytest.mark.parametrize("phase, destination", [("clarify", "plan"), ("analyze", "implement")])
@pytest.mark.parametrize("stale", [False, True])
def test_phase_alias_uses_same_current_gate_as_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str, destination: str, stale: bool
) -> None:
    feature = reviewed_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    assert runner.invoke(app, ["pipeline", "init", "--feature", feature.name]).exit_code == 0
    if stale:
        source = feature / ("spec.md" if phase == "clarify" else "plan.md")
        source.write_text(source.read_text().replace("24 hours", "48 hours"))
    direct = runner.invoke(app, ["validate", str(feature), "--progression", destination])
    nested = runner.invoke(
        app, ["pipeline", "update", "--feature", feature.name, "--phase", phase, "--status", "done"]
    )
    assert direct.exit_code == nested.exit_code == (1 if stale else 0)
    expected = "Pending" if stale else "Done"
    assert f"| {phase.title()} | {expected} |" in (feature / "pipeline.md").read_text()
    if stale:
        reason = "clarify_not_ready" if phase == "clarify" else "analyze_not_ready"
        assert reason in direct.output and reason in nested.output
