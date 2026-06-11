# LiveSpec traceability anchors
# @spec(AC-007)

"""CLI tests for ``livespec verify-output`` (``validator/cli_commands/verify_output_cmd.py``)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from validator.cli import app

runner = CliRunner()


def write_artifact(
    runs_dir: Path,
    *,
    name: str = "spec-specify-2026-06-10T10-00-00-aaaaaaaa.json",
    command: str = "spec-specify",
    exit_code: int | None = 0,
    flags: list[str] | None = None,
    stdout: str | None = None,
    verify_rules: dict[str, Any] | None = None,
) -> Path:
    runs_dir.mkdir(parents=True, exist_ok=True)
    artifact: dict[str, Any] = {
        "schema_version": "2.0",
        "goal_hash": "a" * 64,
        "command": command,
        "feature": None,
        "flags": flags or [],
        "exit_code": exit_code,
        "timestamp": "2026-06-10T10:00:00+00:00",
        "goal": {
            "status": "active",
            "tasks": [
                {
                    "id": "task.001",
                    "ordinal": 1,
                    "status": "complete",
                    "accepted_evidence": {"output": "done"},
                }
            ],
        },
        "receipts": [],
        "verify_rules": verify_rules
        or {
            "must": [{"verb": "must", "kind": "exit_code", "payload": 0}],
            "may": [],
            "must_not": [],
            "when": [],
        },
        "verify_result": {"outcome": "success", "rules": []},
    }
    if stdout is not None:
        artifact["stdout"] = stdout
    path = runs_dir / name
    path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    return path


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / ".specs").mkdir()
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestArtifactSelection:
    def test_latest_artifact_selected_lexicographically(self, project: Path) -> None:
        runs = project / ".specs" / ".runs"
        write_artifact(runs, name="spec-specify-2026-06-10T10-00-00-aaaaaaaa.json")
        write_artifact(runs, name="spec-specify-2026-06-10T11-00-00-bbbbbbbb.json")
        result = runner.invoke(app, ["verify-output", "specify", "--json"])
        assert result.exit_code == 0, result.output
        envelope = json.loads(result.output)
        assert "11-00-00" in envelope["artifact"]

    def test_run_flag_overrides_latest(self, project: Path) -> None:
        runs = project / ".specs" / ".runs"
        early = write_artifact(runs, name="spec-specify-2026-06-10T10-00-00-aaaaaaaa.json")
        write_artifact(runs, name="spec-specify-2026-06-10T11-00-00-bbbbbbbb.json")
        result = runner.invoke(app, ["verify-output", "specify", "--run", str(early), "--json"])
        assert result.exit_code == 0, result.output
        assert "10-00-00" in json.loads(result.output)["artifact"]

    def test_missing_artifact_blocks_exit_2(self, project: Path) -> None:
        result = runner.invoke(app, ["verify-output", "specify"])
        assert result.exit_code == 2
        assert "blocked" in result.output

    def test_missing_artifact_with_json_emits_blocked_envelope(self, project: Path) -> None:
        result = runner.invoke(app, ["verify-output", "specify", "--json"])
        assert result.exit_code == 2
        envelope = json.loads(result.output.splitlines()[0])
        assert envelope["outcome"] == "blocked"
        assert "no run artifact" in envelope["reason"]

    def test_malformed_artifact_blocks_naming_path(self, project: Path) -> None:
        runs = project / ".specs" / ".runs"
        runs.mkdir(parents=True)
        bad = runs / "spec-specify-2026-06-10T10-00-00-aaaaaaaa.json"
        bad.write_text("{not json", encoding="utf-8")
        result = runner.invoke(app, ["verify-output", "specify"])
        assert result.exit_code == 2
        assert bad.name in result.output

    def test_malformed_artifact_with_json_emits_blocked_envelope(self, project: Path) -> None:
        runs = project / ".specs" / ".runs"
        runs.mkdir(parents=True)
        bad = runs / "spec-specify-2026-06-10T10-00-00-aaaaaaaa.json"
        bad.write_text("{not json", encoding="utf-8")
        result = runner.invoke(app, ["verify-output", "specify", "--json"])
        assert result.exit_code == 2
        envelope = json.loads(result.output.splitlines()[0])
        assert envelope["outcome"] == "blocked"
        assert bad.name in envelope["reason"]

    def test_alias_resolution(self, project: Path) -> None:
        write_artifact(project / ".specs" / ".runs")
        for alias in ("specify", "spec-specify", "/spec-specify", "/spec.specify"):
            result = runner.invoke(app, ["verify-output", alias])
            assert result.exit_code == 0, f"{alias}: {result.output}"


class TestReportOutput:
    def test_table_output_lists_rules_and_outcome(self, project: Path) -> None:
        write_artifact(project / ".specs" / ".runs")
        result = runner.invoke(app, ["verify-output", "specify"])
        assert result.exit_code == 0
        assert "verify-output" in result.output
        assert "outcome" in result.output
        assert "exit_code" in result.output

    def test_json_envelope(self, project: Path) -> None:
        write_artifact(project / ".specs" / ".runs")
        result = runner.invoke(app, ["verify-output", "specify", "--json"])
        assert result.exit_code == 0
        envelope = json.loads(result.output)
        assert envelope["outcome"] == "success"
        assert envelope["command"] == "spec-specify"
        assert isinstance(envelope["rules"], list)

    def test_drift_exits_1(self, project: Path) -> None:
        rules = {
            "must": [{"verb": "must", "kind": "contains", "payload": "absent"}],
            "may": [],
            "must_not": [],
            "when": [],
        }
        write_artifact(
            project / ".specs" / ".runs",
            stdout="other text",
            verify_rules=rules,
        )
        result = runner.invoke(app, ["verify-output", "specify"])
        assert result.exit_code == 1
        assert "drift" in result.output


class TestScenarioFlag:
    def test_scenario_replaces_artifact_flags(self, project: Path) -> None:
        rules = {
            "must": [],
            "may": [],
            "must_not": [],
            "when": [
                {
                    "flag": "--visual",
                    "must": [{"verb": "must", "kind": "contains", "payload": "visual run"}],
                    "may": [],
                    "must_not": [],
                }
            ],
        }
        # Artifact flags do NOT include --visual; --scenario activates the branch.
        write_artifact(
            project / ".specs" / ".runs",
            flags=[],
            stdout="no gate here",
            verify_rules=rules,
        )
        without = runner.invoke(app, ["verify-output", "specify", "--json"])
        assert json.loads(without.output)["outcome"] == "success"
        with_scenario = runner.invoke(
            app, ["verify-output", "specify", "--scenario=--visual", "--json"]
        )
        assert json.loads(with_scenario.output)["outcome"] == "drift"


class TestArchiveRunExclusion:
    """Feature 059 AC-006/AC-007: the CLI re-derivation shares the classifier rule."""

    def test_only_archive_run_pending_verifies_as_success(self, project: Path) -> None:
        runs = project / ".specs" / ".runs"
        path = write_artifact(runs)
        artifact = json.loads(path.read_text(encoding="utf-8"))
        artifact["goal"]["tasks"].append(
            {
                "id": "archive.run",
                "ordinal": 2,
                "status": "pending",
                "accepted_evidence": None,
            }
        )
        path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")

        result = runner.invoke(app, ["verify-output", "specify", "--json"])

        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["outcome"] == "success"

    def test_other_pending_task_still_drifts(self, project: Path) -> None:
        runs = project / ".specs" / ".runs"
        path = write_artifact(runs)
        artifact = json.loads(path.read_text(encoding="utf-8"))
        artifact["goal"]["tasks"][0]["status"] = "pending"
        path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")

        result = runner.invoke(app, ["verify-output", "specify", "--json"])

        assert result.exit_code == 1
        assert json.loads(result.output)["outcome"] == "drift"

    def test_pre_059_artifact_without_archive_run_verifies_cleanly(self, project: Path) -> None:
        """AC-007: pre-059 artifacts never require the archive task's presence."""
        write_artifact(project / ".specs" / ".runs")

        result = runner.invoke(app, ["verify-output", "specify", "--json"])

        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["outcome"] == "success"


class TestVerifyMatrixSubstrate:
    """Feature 059 FR-007 (AC-009/AC-010): one fixture artifact per outcome
    class — the exact machine verdicts the supervisor Verify matrix consumes."""

    def test_outcome_success_exit_0(self, project: Path) -> None:
        path = write_artifact(project / ".specs" / ".runs")
        result = runner.invoke(app, ["verify-output", "specify", "--run", str(path), "--json"])
        assert result.exit_code == 0
        assert json.loads(result.output)["outcome"] == "success"

    def test_outcome_drift_exit_1(self, project: Path) -> None:
        rules = {
            "must": [{"verb": "must", "kind": "contains", "payload": "absent needle"}],
            "may": [],
            "must_not": [],
            "when": [],
        }
        path = write_artifact(project / ".specs" / ".runs", stdout="other text", verify_rules=rules)
        result = runner.invoke(app, ["verify-output", "specify", "--run", str(path), "--json"])
        assert result.exit_code == 1
        assert json.loads(result.output)["outcome"] == "drift"

    def test_outcome_error_exit_1(self, project: Path) -> None:
        path = write_artifact(project / ".specs" / ".runs", exit_code=3)
        result = runner.invoke(app, ["verify-output", "specify", "--run", str(path), "--json"])
        assert result.exit_code == 1
        assert json.loads(result.output)["outcome"] == "error"

    def test_outcome_blocked_exit_2_on_malformed_artifact(self, project: Path) -> None:
        runs = project / ".specs" / ".runs"
        runs.mkdir(parents=True)
        bad = runs / "spec-specify-2026-06-11T10-00-00-aaaaaaaa.json"
        bad.write_text("{not json", encoding="utf-8")
        result = runner.invoke(app, ["verify-output", "specify", "--run", str(bad), "--json"])
        assert result.exit_code == 2
        assert json.loads(result.output.splitlines()[0])["outcome"] == "blocked"

    def test_outcome_blocked_exit_2_on_missing_run_path(self, project: Path) -> None:
        result = runner.invoke(
            app,
            ["verify-output", "specify", "--run", str(project / "nope.json"), "--json"],
        )
        assert result.exit_code == 2
        assert json.loads(result.output.splitlines()[0])["outcome"] == "blocked"

    def test_foreign_command_artifact_requires_explicit_supervisor_check(
        self, project: Path
    ) -> None:
        """EC-005 substrate: verify-output does NOT compare the artifact command
        to the requested command — the supervisor Verify phase performs that
        identity check explicitly by reading the artifact's command field."""
        path = write_artifact(
            project / ".specs" / ".runs",
            name="spec-plan-2026-06-11T10-00-00-aaaaaaaa.json",
            command="spec-plan",
        )
        result = runner.invoke(app, ["verify-output", "specify", "--run", str(path), "--json"])
        assert result.exit_code == 0
        envelope = json.loads(result.output)
        assert envelope["command"] == "spec-specify"
        artifact = json.loads(path.read_text(encoding="utf-8"))
        # The mismatch is observable from the artifact itself (supervisor step 3).
        assert artifact["command"] == "spec-plan"
        assert artifact["command"] != envelope["command"]
