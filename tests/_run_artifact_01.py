"""Preserved test cases and fixtures for test_run_artifact.py."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from tests._json_fixture import json_fixture
from validator.conventions_gate import GateResult, GateVerdict, GateViolation
from validator.conventions_gates import gates_path
from validator.conventions_receipt import write_conventions_receipt
from validator.finalize_receipt import write_receipt
from validator.run_artifacts import (
    RUN_ARTIFACT_SCHEMA_VERSION,
    archive_goal_run,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


GOAL_HASH = "a" * 64


FROZEN_NOW = datetime(2026, 6, 10, 10, 0, 0, tzinfo=UTC)


FROZEN_NOW_PLUS_MICROSECOND = datetime(2026, 6, 10, 10, 0, 0, 1, tzinfo=UTC)


def make_contract(
    *,
    command: str = "spec-specify",
    goal_hash: str = GOAL_HASH,
    flags: list[str] | None = None,
    feature: str | None = None,
    verify_rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a minimal goal contract dict matching the 052 file shape."""
    return {
        "schema_version": "2.0",
        "goal_hash": goal_hash,
        "command": command,
        "feature": feature,
        "normalized_flags": flags or [],
        "mode": "enforced",
        "tasks": [],
        "canonical": {
            "verify_rules": verify_rules
            or {
                "must": [{"verb": "must", "kind": "exit_code", "payload": 0}],
                "may": [],
                "must_not": [],
                "when": [],
            }
        },
    }


def make_state(
    *,
    command: str = "spec-specify",
    goal_hash: str = GOAL_HASH,
    tasks: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a minimal goal state dict matching the 052 file shape."""
    if tasks is None:
        tasks = {
            "task.001.do_thing": {
                "ordinal": 1,
                "description": "do thing",
                "status": "complete",
                "attempts": [],
                "accepted_evidence": {"output": "did thing"},
                "last_rejection": None,
            }
        }
    return {
        "schema_version": "2.0",
        "goal_hash": goal_hash,
        "command": command,
        "status": "active",
        "tasks": tasks,
    }


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    (tmp_path / ".specs").mkdir()
    return tmp_path


class TestArchiveHappyPath:
    def test_complete_goal_archives_as_success(self, project_root: Path) -> None:
        result = archive_goal_run(
            make_contract(),
            make_state(),
            project_root=project_root,
            exit_code=0,
            now=FROZEN_NOW,
        )
        assert result.outcome == "success"
        assert result.path is not None
        assert result.path.exists()
        artifact = json.loads(result.path.read_text(encoding="utf-8"))
        assert artifact["schema_version"] == RUN_ARTIFACT_SCHEMA_VERSION
        assert artifact["goal_hash"] == GOAL_HASH
        assert artifact["command"] == "spec-specify"
        assert artifact["exit_code"] == 0
        assert artifact["verify_result"]["outcome"] == "success"

    def test_filename_is_timestamp_led_with_hash8(self, project_root: Path) -> None:
        result = archive_goal_run(
            make_contract(),
            make_state(),
            project_root=project_root,
            exit_code=0,
            now=FROZEN_NOW,
        )
        assert result.path is not None
        assert result.path.name == f"spec-specify-2026-06-10T10-00-00.000000-{GOAL_HASH[:8]}.json"
        assert result.path.parent == project_root / ".specs" / ".runs"

    def test_atomic_write_leaves_no_tmp_residue(self, project_root: Path) -> None:
        archive_goal_run(
            make_contract(),
            make_state(),
            project_root=project_root,
            exit_code=0,
            now=FROZEN_NOW,
        )
        runs_dir = project_root / ".specs" / ".runs"
        assert not list(runs_dir.glob("*.tmp"))

    def test_v1_unobservable_fields_absent(self, project_root: Path) -> None:
        result = archive_goal_run(
            make_contract(),
            make_state(),
            project_root=project_root,
            exit_code=0,
            now=FROZEN_NOW,
        )
        assert result.path is not None
        text = result.path.read_text(encoding="utf-8")
        for forbidden in ("git_state_before", "git_state_after", "fs_observed", "duration_ms"):
            assert forbidden not in text

    def test_inputs_not_mutated(self, project_root: Path, tmp_path: Path) -> None:
        contract_file = tmp_path / "c.json"
        state_file = tmp_path / "s.json"
        contract_file.write_text(json.dumps(make_contract()), encoding="utf-8")
        state_file.write_text(json.dumps(make_state()), encoding="utf-8")
        before = (contract_file.read_bytes(), state_file.read_bytes())
        archive_goal_run(
            json.loads(contract_file.read_text(encoding="utf-8")),
            json.loads(state_file.read_text(encoding="utf-8")),
            project_root=project_root,
            exit_code=0,
            now=FROZEN_NOW,
        )
        assert (contract_file.read_bytes(), state_file.read_bytes()) == before

    def test_goal_snapshot_fields(self, project_root: Path) -> None:
        result = archive_goal_run(
            make_contract(),
            make_state(),
            project_root=project_root,
            exit_code=0,
            now=FROZEN_NOW,
        )
        assert result.artifact is not None
        goal = json_fixture(result.artifact)["goal"]
        assert goal["status"] == "active"
        assert goal["tasks"] == [
            {
                "id": "task.001.do_thing",
                "ordinal": 1,
                "status": "complete",
                "accepted_evidence": {"output": "did thing"},
            }
        ]


class TestArchiveOutcomes:
    def test_incomplete_goal_is_drift(self, project_root: Path) -> None:
        tasks = {
            "task.001.pending": {
                "ordinal": 1,
                "description": "pending task",
                "status": "pending",
                "attempts": [],
                "accepted_evidence": None,
                "last_rejection": None,
            }
        }
        result = archive_goal_run(
            make_contract(),
            make_state(tasks=tasks),
            project_root=project_root,
            exit_code=0,
            now=FROZEN_NOW,
        )
        assert result.outcome == "drift"
        assert result.path is not None and result.path.exists()

    def test_nonzero_exit_code_is_error(self, project_root: Path) -> None:
        result = archive_goal_run(
            make_contract(),
            make_state(),
            project_root=project_root,
            exit_code=3,
            now=FROZEN_NOW,
        )
        assert result.outcome == "error"

    def test_hash_mismatch_blocks_and_writes_nothing(self, project_root: Path) -> None:
        result = archive_goal_run(
            make_contract(goal_hash="a" * 64),
            make_state(goal_hash="b" * 64),
            project_root=project_root,
            exit_code=0,
            now=FROZEN_NOW,
        )
        assert result.outcome == "blocked"
        assert result.path is None
        assert result.blocked_reason is not None and "goal_hash" in result.blocked_reason
        runs_dir = project_root / ".specs" / ".runs"
        assert not runs_dir.exists() or not list(runs_dir.iterdir())

    def test_invalid_archive_identity_blocks_and_writes_nothing(self, project_root: Path) -> None:
        result = archive_goal_run(
            make_contract(command="../escape", goal_hash="A" * 64),
            make_state(goal_hash="A" * 64),
            project_root=project_root,
            exit_code=0,
            now=FROZEN_NOW,
        )
        assert result.outcome == "blocked"
        assert result.path is None
        assert result.blocked_reason is not None
        runs_dir = project_root / ".specs" / ".runs"
        assert not runs_dir.exists() or not list(runs_dir.iterdir())

    def test_null_exit_code_records_null_and_skips_exit_rules(self, project_root: Path) -> None:
        result = archive_goal_run(
            make_contract(),
            make_state(),
            project_root=project_root,
            exit_code=None,
            now=FROZEN_NOW,
        )
        assert result.artifact is not None
        assert json_fixture(result.artifact)["exit_code"] is None
        rules = json_fixture(result.artifact)["verify_result"]["rules"]
        exit_rules = [r for r in rules if r["kind"] == "exit_code"]
        assert exit_rules and all(r["status"] == "SKIP" for r in exit_rules)
        # SKIP never counts toward failed must rules (EC-011).
        assert result.outcome == "success"


class TestArchiveTranscripts:
    def test_transcripts_embedded_only_when_given(self, project_root: Path) -> None:
        without = archive_goal_run(
            make_contract(),
            make_state(),
            project_root=project_root,
            exit_code=0,
            now=FROZEN_NOW,
        )
        assert without.artifact is not None
        assert "stdout" not in without.artifact
        assert "stderr" not in without.artifact
        with_streams = archive_goal_run(
            make_contract(),
            make_state(),
            project_root=project_root,
            exit_code=0,
            stdout_text="hello out",
            stderr_text="hello err",
            now=FROZEN_NOW,
        )
        assert with_streams.artifact is not None
        assert with_streams.artifact["stdout"] == "hello out"
        assert with_streams.artifact["stderr"] == "hello err"

    def test_contains_rules_skip_without_transcript(self, project_root: Path) -> None:
        rules = {
            "must": [{"verb": "must", "kind": "contains", "payload": "spec.md created"}],
            "may": [],
            "must_not": [],
            "when": [],
        }
        result = archive_goal_run(
            make_contract(verify_rules=rules),
            make_state(),
            project_root=project_root,
            exit_code=0,
            now=FROZEN_NOW,
        )
        assert result.artifact is not None
        rule_results = json_fixture(result.artifact)["verify_result"]["rules"]
        assert all(r["status"] == "SKIP" for r in rule_results)
        # EC-005: all-contains, no transcript -> outcome may legitimately be success.
        assert result.outcome == "success"


def _make_finalize_receipt(project_root: Path, *, feature_slug: str = "001-x") -> Path:
    tracked = project_root / ".specs" / "tracked.md"
    tracked.write_text("tracked content\n", encoding="utf-8")
    return write_receipt(
        project_root=project_root,
        feature_slug=feature_slug,
        command="spec-test",
        run_id="r1",
        payload_hash="0" * 64,
        outcome="applied",
        verdict="PASS",
        files=[tracked],
        violations=[],
    )


def _state_with_receipt(receipt_path: Path, project_root: Path) -> dict[str, Any]:
    rel = receipt_path.relative_to(project_root).as_posix()
    tasks = {
        "finalize.registry": {
            "ordinal": 1,
            "description": "finalize",
            "status": "complete",
            "attempts": [],
            "accepted_evidence": {"finalize_receipt_path": rel},
            "last_rejection": None,
        }
    }
    return make_state(tasks=tasks)


def _write_conventions_gates(project_root: Path) -> Path:
    path = gates_path(project_root)
    constitution = project_root / ".specs" / "constitution.md"
    constitution.parent.mkdir(parents=True, exist_ok=True)
    constitution.write_text("# Constitution\n", encoding="utf-8")
    path.write_text(
        """\
schema_version: 1
generated_from:
  constitution: .specs/constitution.md
  constitution_sha256: 1e573f647f46d0e508830de88db17ac2b096487ad15f73dbd608d5d35640ed94
  stack: .specs/stacks/_default.md
commands: {}
builtin: {}
coverage: {}
exclusions: []
scope: repo
""",
        encoding="utf-8",
    )
    return path


def _make_conventions_receipt(project_root: Path, *, verdict: GateVerdict) -> Path:
    gates = _write_conventions_gates(project_root)
    return write_conventions_receipt(
        project_root=project_root,
        feature_slug="001-x",
        run_id=f"r-{verdict.value.lower()}",
        result=GateResult(
            verdict=verdict,
            violations=[
                GateViolation(
                    rule_id="max_file_lines",
                    path="src/too_long.py",
                    line=501,
                    severity="error",
                    message="file too long",
                    source="builtin",
                )
            ],
            blockers=[],
        ),
        gates_path=gates,
    )
