# LiveSpec traceability anchors
# @spec(AC-001)
# @spec(AC-003)
# @spec(AC-004)
# @spec(AC-006)
# @spec(AC-012)

"""Unit tests for the RunArtifact v2 data layer (``validator/run_artifacts.py``).

Covers the archive pipeline (hash gate, goal snapshot, transcripts, receipt
re-verification, outcome classification, atomic write) plus the documentation
truth-fix assertions from feature 039.1.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from validator.exceptions import ArtifactMalformed
from validator.finalize_receipt import write_receipt
from validator.run_artifacts import (
    RUN_ARTIFACT_SCHEMA_VERSION,
    archive_goal_run,
    find_latest_artifact,
    load_run_artifact,
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
        goal = result.artifact["goal"]
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
        assert result.artifact["exit_code"] is None
        rules = result.artifact["verify_result"]["rules"]
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
        rule_results = result.artifact["verify_result"]["rules"]
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


class TestReceiptIntegrity:
    def test_valid_receipt_recorded_as_verified(self, project_root: Path) -> None:
        receipt = _make_finalize_receipt(project_root)
        result = archive_goal_run(
            make_contract(),
            _state_with_receipt(receipt, project_root),
            project_root=project_root,
            exit_code=0,
            now=FROZEN_NOW,
        )
        assert result.artifact is not None
        receipts = result.artifact["receipts"]
        assert len(receipts) == 1
        assert receipts[0]["kind"] == "finalize"
        assert receipts[0]["verified"] is True
        assert receipts[0]["verdict"] == "PASS"
        assert result.outcome == "success"

    def test_tampered_receipt_forces_error(self, project_root: Path) -> None:
        receipt = _make_finalize_receipt(project_root)
        payload = json.loads(receipt.read_text(encoding="utf-8"))
        payload["verdict"] = "PASS "  # corrupt one byte
        receipt.write_text(json.dumps(payload), encoding="utf-8")
        result = archive_goal_run(
            make_contract(),
            _state_with_receipt(receipt, project_root),
            project_root=project_root,
            exit_code=0,
            now=FROZEN_NOW,
        )
        assert result.artifact is not None
        assert result.artifact["receipts"][0]["verified"] is False
        assert result.artifact["receipts"][0]["error"]
        assert result.outcome == "error"

    def test_missing_receipt_file_is_error(self, project_root: Path) -> None:
        receipt = _make_finalize_receipt(project_root)
        receipt.unlink()
        result = archive_goal_run(
            make_contract(),
            _state_with_receipt(receipt, project_root),
            project_root=project_root,
            exit_code=0,
            now=FROZEN_NOW,
        )
        assert result.artifact is not None
        assert result.artifact["receipts"][0]["verified"] is False
        assert result.outcome == "error"

    def test_feature_scoping_only_with_feature(self, project_root: Path) -> None:
        receipt = _make_finalize_receipt(project_root, feature_slug="001-x")
        state = _state_with_receipt(receipt, project_root)
        scoped = archive_goal_run(
            make_contract(),
            state,
            project_root=project_root,
            feature="002-other",
            exit_code=0,
            now=FROZEN_NOW,
        )
        assert scoped.artifact is not None
        assert scoped.artifact["receipts"][0]["verified"] is False
        assert scoped.outcome == "error"
        unscoped = archive_goal_run(
            make_contract(),
            state,
            project_root=project_root,
            exit_code=0,
            now=FROZEN_NOW,
        )
        assert unscoped.artifact is not None
        assert unscoped.artifact["receipts"][0]["verified"] is True
        assert unscoped.outcome == "success"


class TestArtifactHelpers:
    def test_find_latest_artifact_picks_lex_last(self, tmp_path: Path) -> None:
        runs = tmp_path / ".runs"
        runs.mkdir()
        early = runs / "spec-specify-2026-06-10T10-00-00-aaaaaaaa.json"
        late = runs / "spec-specify-2026-06-10T11-00-00-bbbbbbbb.json"
        other = runs / "spec-test-2026-06-10T12-00-00-cccccccc.json"
        for f in (early, late, other):
            f.write_text("{}", encoding="utf-8")
        assert find_latest_artifact("spec-specify", runs) == late

    def test_find_latest_artifact_none_when_empty(self, tmp_path: Path) -> None:
        assert find_latest_artifact("spec-specify", tmp_path / "nope") is None

    def test_load_run_artifact_names_malformed_path(self, tmp_path: Path) -> None:
        bad = tmp_path / "spec-specify-x.json"
        bad.write_text("{truncated", encoding="utf-8")
        with pytest.raises(ArtifactMalformed) as exc_info:
            load_run_artifact(bad)
        assert bad.as_posix() in str(exc_info.value)

    def test_load_run_artifact_validates_v2_schema(self, tmp_path: Path) -> None:
        bad = tmp_path / "spec-specify-x.json"
        bad.write_text('{"schema_version":"2.0"}', encoding="utf-8")
        with pytest.raises(ArtifactMalformed) as exc_info:
            load_run_artifact(bad)
        assert "goal_hash" in str(exc_info.value)

    def test_same_second_archives_coexist(self, project_root: Path) -> None:
        first = archive_goal_run(
            make_contract(goal_hash="a" * 64),
            make_state(goal_hash="a" * 64),
            project_root=project_root,
            exit_code=0,
            now=FROZEN_NOW,
        )
        second = archive_goal_run(
            make_contract(goal_hash="c" * 64),
            make_state(goal_hash="c" * 64),
            project_root=project_root,
            exit_code=0,
            now=FROZEN_NOW,
        )
        assert first.path != second.path
        assert first.path is not None and first.path.exists()
        assert second.path is not None and second.path.exists()

    def test_same_goal_same_second_archives_coexist(self, project_root: Path) -> None:
        first = archive_goal_run(
            make_contract(),
            make_state(),
            project_root=project_root,
            exit_code=0,
            now=FROZEN_NOW,
        )
        second = archive_goal_run(
            make_contract(),
            make_state(),
            project_root=project_root,
            exit_code=0,
            now=FROZEN_NOW_PLUS_MICROSECOND,
        )
        assert first.path != second.path
        assert first.path is not None and first.path.exists()
        assert second.path is not None and second.path.exists()


class TestTruthFixes:
    """Static assertions for the 039.1 documentation truth-fixes (FR-010)."""

    def test_system_expectations_documents_run_artifact_v2(self) -> None:
        text = (REPO_ROOT / "system" / "expectations.md").read_text(encoding="utf-8")
        assert "RunArtifact v2 (goal archive)" in text
        assert "039 FR-005" in text

    def test_spec_feature_skill_uses_goal_archive(self) -> None:
        text = (REPO_ROOT / ".agent-sync" / "skills" / "spec-feature" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        assert "livespec goal archive" in text
        assert "livespec run record" not in text

    def test_verify_output_expectations_contradiction_resolved(self) -> None:
        text = (
            REPO_ROOT / ".agent-sync" / "skills" / "spec-verify-output" / "expectations.md"
        ).read_text(encoding="utf-8")
        assert ".specs/.previews/" in text
        assert "livespec run wrap" not in text

    @pytest.mark.parametrize(
        "feature_dir",
        [
            "039-command-expectations-and-verify-output",
            "040-expectations-rich-and-verify-preview",
        ],
    )
    def test_implementation_md_references_existing_files(self, feature_dir: str) -> None:
        text = (REPO_ROOT / ".specs" / "features" / feature_dir / "implementation.md").read_text(
            encoding="utf-8"
        )
        for module in ("validator/run_artifacts.py", "validator/preview.py"):
            if module in text:
                assert (REPO_ROOT / module).exists()
        assert (
            "tests/test_run_artifact.py" not in text
            or (REPO_ROOT / "tests" / "test_run_artifact.py").exists()
        )
        assert (
            "tests/test_preview.py" not in text
            or (REPO_ROOT / "tests" / "test_preview.py").exists()
        )


def _task(task_id: str, *, ordinal: int, status: str) -> dict[str, Any]:
    return {
        "ordinal": ordinal,
        "description": task_id,
        "status": status,
        "attempts": [],
        "accepted_evidence": {"output": "x"} if status == "complete" else None,
        "last_rejection": None,
    }


class TestArchiveRunExclusion:
    """Feature 059 AC-006/EC-001: archive.run never forces a drift outcome."""

    def test_only_archive_run_pending_is_success(self, project_root: Path) -> None:
        """SC-004: the snapshot legitimately shows archive.run pending."""
        tasks = {
            "task.001.do_thing": _task("task.001.do_thing", ordinal=1, status="complete"),
            "archive.run": _task("archive.run", ordinal=2, status="pending"),
        }
        result = archive_goal_run(
            make_contract(),
            make_state(tasks=tasks),
            project_root=project_root,
            exit_code=0,
            now=FROZEN_NOW,
        )
        assert result.outcome == "success"
        assert result.artifact is not None
        snapshot_ids = {task["id"]: task["status"] for task in result.artifact["goal"]["tasks"]}
        assert snapshot_ids["archive.run"] == "pending"

    def test_other_pending_with_archive_run_pending_is_drift(self, project_root: Path) -> None:
        tasks = {
            "task.001.do_thing": _task("task.001.do_thing", ordinal=1, status="pending"),
            "archive.run": _task("archive.run", ordinal=2, status="pending"),
        }
        result = archive_goal_run(
            make_contract(),
            make_state(tasks=tasks),
            project_root=project_root,
            exit_code=0,
            now=FROZEN_NOW,
        )
        assert result.outcome == "drift"

    def test_pre_059_snapshot_with_pending_task_stays_drift(self, project_root: Path) -> None:
        """AC-007: snapshots without archive.run keep their pre-059 classification."""
        tasks = {
            "task.001.pending": _task("task.001.pending", ordinal=1, status="pending"),
        }
        result = archive_goal_run(
            make_contract(),
            make_state(tasks=tasks),
            project_root=project_root,
            exit_code=0,
            now=FROZEN_NOW,
        )
        assert result.outcome == "drift"

    def test_pre_059_fully_complete_snapshot_stays_success(self, project_root: Path) -> None:
        result = archive_goal_run(
            make_contract(),
            make_state(),
            project_root=project_root,
            exit_code=0,
            now=FROZEN_NOW,
        )
        assert result.outcome == "success"

    def test_goal_tasks_incomplete_helper_excludes_archive_run(self) -> None:
        """AC-006: the shared helper is the single classification rule."""
        from validator.run_artifacts import goal_tasks_incomplete

        assert goal_tasks_incomplete([{"id": "task.001", "status": "pending"}]) is True
        assert goal_tasks_incomplete([{"id": "task.001", "status": "complete"}]) is False
        assert goal_tasks_incomplete([{"id": "archive.run", "status": "pending"}]) is False
        assert (
            goal_tasks_incomplete(
                [
                    {"id": "task.001", "status": "complete"},
                    {"id": "archive.run", "status": "pending"},
                ]
            )
            is False
        )
