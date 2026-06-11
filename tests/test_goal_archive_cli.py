# LiveSpec traceability anchors
# @spec(AC-001)
# @spec(AC-002)

"""End-to-end CLI tests for ``livespec goal archive`` and the verify round-trip."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from validator.cli import app

runner = CliRunner()

GOAL_HASH = "d" * 64


def write_pair(
    tmp_path: Path,
    *,
    complete: bool = True,
    contract_hash: str = GOAL_HASH,
    state_hash: str = GOAL_HASH,
) -> tuple[Path, Path]:
    contract: dict[str, Any] = {
        "schema_version": "2.0",
        "goal_hash": contract_hash,
        "command": "spec-specify",
        "feature": None,
        "normalized_flags": [],
        "mode": "enforced",
        "tasks": [],
        "canonical": {
            "verify_rules": {
                "must": [{"verb": "must", "kind": "exit_code", "payload": 0}],
                "may": [],
                "must_not": [],
                "when": [],
            }
        },
    }
    state: dict[str, Any] = {
        "schema_version": "2.0",
        "goal_hash": state_hash,
        "command": "spec-specify",
        "status": "active",
        "tasks": {
            "task.001.do": {
                "ordinal": 1,
                "description": "do",
                "status": "complete" if complete else "pending",
                "attempts": [],
                "accepted_evidence": {"output": "x"} if complete else None,
                "last_rejection": None,
            }
        },
    }
    contract_file = tmp_path / "goal.contract.json"
    state_file = tmp_path / "goal.state.json"
    contract_file.write_text(json.dumps(contract), encoding="utf-8")
    state_file.write_text(json.dumps(state), encoding="utf-8")
    return contract_file, state_file


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / ".specs").mkdir()
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestGoalArchiveCli:
    def test_archive_success_round_trip(self, project: Path) -> None:
        contract_file, state_file = write_pair(project)
        before = (contract_file.read_bytes(), state_file.read_bytes())
        result = runner.invoke(
            app,
            [
                "goal",
                "archive",
                "--contract",
                str(contract_file),
                "--state",
                str(state_file),
                "--exit-code",
                "0",
            ],
        )
        assert result.exit_code == 0, result.output
        match = re.search(r"archived: (\S+) \| outcome:success", result.output)
        assert match, result.output
        artifact_path = Path(match.group(1))
        assert artifact_path.exists()
        assert (contract_file.read_bytes(), state_file.read_bytes()) == before
        # SC-001 round trip: verify-output reads the freshly archived artifact.
        verify = runner.invoke(app, ["verify-output", "specify"])
        assert verify.exit_code == 0, verify.output
        assert "success" in verify.output

    def test_archive_incomplete_goal_is_drift_exit_1(self, project: Path) -> None:
        contract_file, state_file = write_pair(project, complete=False)
        result = runner.invoke(
            app,
            [
                "goal",
                "archive",
                "--contract",
                str(contract_file),
                "--state",
                str(state_file),
                "--exit-code",
                "0",
            ],
        )
        assert result.exit_code == 1
        assert "outcome:drift" in result.output

    def test_archive_missing_contract_blocks_exit_2(self, project: Path) -> None:
        _, state_file = write_pair(project)
        result = runner.invoke(
            app,
            [
                "goal",
                "archive",
                "--contract",
                str(project / "nope.json"),
                "--state",
                str(state_file),
            ],
        )
        assert result.exit_code == 2
        runs_dir = project / ".specs" / ".runs"
        assert not runs_dir.exists() or not list(runs_dir.iterdir())

    def test_archive_hash_mismatch_blocks_exit_2(self, project: Path) -> None:
        contract_file, state_file = write_pair(project, state_hash="e" * 64)
        result = runner.invoke(
            app,
            [
                "goal",
                "archive",
                "--contract",
                str(contract_file),
                "--state",
                str(state_file),
                "--exit-code",
                "0",
            ],
        )
        assert result.exit_code == 2
        runs_dir = project / ".specs" / ".runs"
        assert not runs_dir.exists() or not list(runs_dir.iterdir())

    def test_archive_json_envelope(self, project: Path) -> None:
        contract_file, state_file = write_pair(project)
        result = runner.invoke(
            app,
            [
                "goal",
                "archive",
                "--contract",
                str(contract_file),
                "--state",
                str(state_file),
                "--exit-code",
                "0",
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        envelope = json.loads(result.output)
        assert envelope["outcome"] == "success"
        assert Path(envelope["archived"]).exists()

    def test_archive_exit_code_out_of_range_blocks_exit_2(self, project: Path) -> None:
        # Invariant: artifact `exit_code` is a real process exit code (0-255);
        # accepting arbitrary integers would poison exit_code verify rules.
        contract_file, state_file = write_pair(project)
        result = runner.invoke(
            app,
            [
                "goal",
                "archive",
                "--contract",
                str(contract_file),
                "--state",
                str(state_file),
                "--exit-code",
                "300",
            ],
        )
        assert result.exit_code == 2
        assert "--exit-code must be between 0 and 255" in result.output
        runs_dir = project / ".specs" / ".runs"
        assert not runs_dir.exists() or not list(runs_dir.iterdir())

    def test_archive_oversized_transcript_blocks_exit_2(
        self, project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Invariant: embedded transcripts are size-bounded so a runaway stdout
        # capture cannot balloon the artifact (general.md §18 limits).
        from validator.cli_commands import goal_cmd

        monkeypatch.setattr(goal_cmd, "MAX_TRANSCRIPT_BYTES", 16)
        contract_file, state_file = write_pair(project)
        big = project / "stdout.txt"
        big.write_text("x" * 64, encoding="utf-8")
        result = runner.invoke(
            app,
            [
                "goal",
                "archive",
                "--contract",
                str(contract_file),
                "--state",
                str(state_file),
                "--stdout-file",
                str(big),
            ],
        )
        assert result.exit_code == 2
        assert "max 16 bytes" in result.output
        runs_dir = project / ".specs" / ".runs"
        assert not runs_dir.exists() or not list(runs_dir.iterdir())

    def test_archive_blocked_with_json_emits_envelope(self, project: Path) -> None:
        # Invariant: --json callers always get machine-readable stdout, even on
        # blocked outcomes (cli.md: every data command supports --json).
        contract_file, state_file = write_pair(project, state_hash="e" * 64)
        result = runner.invoke(
            app,
            [
                "goal",
                "archive",
                "--contract",
                str(contract_file),
                "--state",
                str(state_file),
                "--json",
            ],
        )
        assert result.exit_code == 2
        first_line = result.output.strip().splitlines()[0]
        envelope = json.loads(first_line)
        assert envelope["outcome"] == "blocked"
        assert "goal_hash mismatch" in envelope["reason"]

    def test_archive_embeds_transcripts_from_files(self, project: Path) -> None:
        contract_file, state_file = write_pair(project)
        out_file = project / "captured.out"
        err_file = project / "captured.err"
        out_file.write_text("stdout text", encoding="utf-8")
        err_file.write_text("stderr text", encoding="utf-8")
        result = runner.invoke(
            app,
            [
                "goal",
                "archive",
                "--contract",
                str(contract_file),
                "--state",
                str(state_file),
                "--exit-code",
                "0",
                "--stdout-file",
                str(out_file),
                "--stderr-file",
                str(err_file),
            ],
        )
        assert result.exit_code == 0, result.output
        artifact_path = next((project / ".specs" / ".runs").glob("spec-specify-*.json"))
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        assert artifact["stdout"] == "stdout text"
        assert artifact["stderr"] == "stderr text"

    def test_real_render_then_archive_smoke(self, project: Path) -> None:
        """SC-001 smoke: real ``goal render`` output is archivable as-is."""
        render = runner.invoke(app, ["goal", "render", "spec-status", "--flags", "", "--save"])
        assert render.exit_code == 0, render.output
        match = re.search(r"contract-file:(\S+) \| state-file:(\S+)", render.output)
        assert match, render.output
        result = runner.invoke(
            app,
            [
                "goal",
                "archive",
                "--contract",
                match.group(1),
                "--state",
                match.group(2),
                "--exit-code",
                "0",
            ],
        )
        # Freshly rendered goals have pending tasks -> honest drift, exit 1.
        assert result.exit_code == 1, result.output
        assert "outcome:drift" in result.output
        artifacts = list((project / ".specs" / ".runs").glob("spec-status-*.json"))
        assert len(artifacts) == 1
