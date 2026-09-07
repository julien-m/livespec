"""Preserved test cases and fixtures for test_run_artifact.py."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests._json_fixture import json_fixture
from tests._run_artifact_01 import (
    FROZEN_NOW,
    FROZEN_NOW_PLUS_MICROSECOND,
    REPO_ROOT,
    _make_conventions_receipt,
    _make_finalize_receipt,
    _state_with_receipt,
    make_contract,
    make_state,
)
from validator.conventions_gate import GateVerdict
from validator.exceptions import ArtifactMalformed
from validator.run_artifacts import (
    archive_goal_run,
    find_latest_artifact,
    load_run_artifact,
)


def _state_with_conventions_receipt(receipt_path: Path, project_root: Path) -> dict[str, Any]:
    tasks = {
        "conventions.gate": {
            "ordinal": 1,
            "description": "conventions",
            "status": "complete",
            "attempts": [],
            "accepted_evidence": {
                "conventions_receipt_path": receipt_path.relative_to(project_root).as_posix()
            },
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
        receipts = json_fixture(result.artifact)["receipts"]
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
        assert json_fixture(result.artifact)["receipts"][0]["verified"] is False
        assert json_fixture(result.artifact)["receipts"][0]["error"]
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
        assert json_fixture(result.artifact)["receipts"][0]["verified"] is False
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
        assert json_fixture(scoped.artifact)["receipts"][0]["verified"] is False
        assert scoped.outcome == "error"
        unscoped = archive_goal_run(
            make_contract(),
            state,
            project_root=project_root,
            exit_code=0,
            now=FROZEN_NOW,
        )
        assert unscoped.artifact is not None
        assert json_fixture(unscoped.artifact)["receipts"][0]["verified"] is True
        assert unscoped.outcome == "success"

    def test_conventions_fail_receipt_is_drift_not_error(self, project_root: Path) -> None:
        receipt = _make_conventions_receipt(project_root, verdict=GateVerdict.FAIL)
        rules = {
            "must": [
                {
                    "verb": "must",
                    "kind": "receipt_verdict",
                    "payload": {
                        "kind": "conventions",
                        "verdict": "PASS",
                        "required_if_exists": True,
                    },
                }
            ],
            "may": [],
            "must_not": [],
            "when": [],
        }

        result = archive_goal_run(
            make_contract(feature="001-x", verify_rules=rules),
            _state_with_conventions_receipt(receipt, project_root),
            project_root=project_root,
            feature="001-x",
            exit_code=0,
            now=FROZEN_NOW,
        )

        assert result.artifact is not None
        assert json_fixture(result.artifact)["receipts"][0]["verified"] is True
        assert json_fixture(result.artifact)["receipts"][0]["verdict"] == "FAIL"
        assert result.outcome == "drift"


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
        snapshot_ids = {
            task["id"]: task["status"] for task in json_fixture(result.artifact)["goal"]["tasks"]
        }
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
