"""Preserved test cases and fixtures for test_goal_contracts.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests._goal_contracts_01 import _fixture_roots, _repo_root
from tests._goal_contracts_09 import _archive_fixture_artifact, _demo_contract_and_state
from tests._json_fixture import json_fixture
from validator.goal_contracts import (
    compile_command_goal,
    prove_goal_task,
    render_goal_contract_file,
)


def test_archive_run_prove_rejects_malformed_artifact_file(tmp_path: Path) -> None:
    """AC-004 (chaos-style fixture, unmarked so it runs at every level): a
    malformed v2 file is named in the rejection."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    contract, state = _demo_contract_and_state(project_root, livespec_root)
    runs_dir = project_root / ".specs" / ".runs"
    runs_dir.mkdir(parents=True)
    bad = runs_dir / "spec-demo-2026-06-11T10-00-00.000000-deadbeef.json"
    bad.write_text("{truncated", encoding="utf-8")

    result = prove_goal_task(
        contract,
        state,
        "archive.run",
        evidence={"run_artifact_path": str(bad)},
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert any(item.startswith("run_artifact_valid:") for item in result["missing_evidence"])


def test_archive_run_prove_rejects_foreign_goal_artifact(tmp_path: Path) -> None:
    """AC-004: an artifact archived under another goal hash is rejected."""
    from tests.test_run_artifact import make_contract, make_state

    project_root, livespec_root = _fixture_roots(tmp_path)
    contract, state = _demo_contract_and_state(project_root, livespec_root)
    foreign = _archive_fixture_artifact(
        project_root,
        make_contract(command="spec-demo", goal_hash="f" * 64),
        make_state(command="spec-demo", goal_hash="f" * 64),
    )

    result = prove_goal_task(
        contract,
        state,
        "archive.run",
        evidence={"run_artifact_path": str(foreign)},
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "run_artifact_goal_hash_match" in result["missing_evidence"]


def test_archive_run_prove_rejects_foreign_command_artifact(tmp_path: Path) -> None:
    """AC-004: an artifact archived for another command is rejected."""
    from tests.test_run_artifact import make_contract, make_state

    project_root, livespec_root = _fixture_roots(tmp_path)
    contract, state = _demo_contract_and_state(project_root, livespec_root)
    goal_hash = str(contract["goal_hash"])
    foreign = _archive_fixture_artifact(
        project_root,
        make_contract(command="spec-other", goal_hash=goal_hash),
        make_state(command="spec-other", goal_hash=goal_hash),
    )

    result = prove_goal_task(
        contract,
        state,
        "archive.run",
        evidence={"run_artifact_path": str(foreign)},
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "run_artifact_command_match" in result["missing_evidence"]


def test_archive_run_prove_accepts_matching_artifact_read_only(tmp_path: Path) -> None:
    """AC-004/AC-005: a matching .specs/.runs/ artifact is accepted without re-archiving."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    contract, state = _demo_contract_and_state(project_root, livespec_root)
    artifact_path = _archive_fixture_artifact(project_root, contract, state)
    runs_dir = project_root / ".specs" / ".runs"
    listing_before = sorted(path.name for path in runs_dir.iterdir())

    result = prove_goal_task(
        contract,
        state,
        "archive.run",
        evidence={"run_artifact_path": str(artifact_path)},
        project_root=project_root,
    )

    assert result["status"] == "ACCEPTED"
    assert result["state"]["tasks"]["archive.run"]["status"] == "complete"
    # Read-only bootstrap: the proof never writes anything under .specs/.runs/.
    assert sorted(path.name for path in runs_dir.iterdir()) == listing_before


def test_archive_run_prove_accepts_non_latest_matching_artifact(tmp_path: Path) -> None:
    """EC-002: any artifact with a matching goal hash is accepted, not only the latest."""
    from tests.test_run_artifact import make_contract, make_state

    project_root, livespec_root = _fixture_roots(tmp_path)
    contract, state = _demo_contract_and_state(project_root, livespec_root)
    matching = _archive_fixture_artifact(project_root, contract, state)
    # A later artifact for the same command but another goal makes `matching` non-latest.
    _archive_fixture_artifact(
        project_root,
        make_contract(command="spec-demo", goal_hash="9" * 64),
        make_state(command="spec-demo", goal_hash="9" * 64),
    )

    result = prove_goal_task(
        contract,
        state,
        "archive.run",
        evidence={"run_artifact_path": str(matching)},
        project_root=project_root,
    )

    assert result["status"] == "ACCEPTED"
    # Meaningful postcondition: the accepted evidence records the non-latest
    # matching artifact path, proving EC-002 (no latest-only restriction).
    accepted = result["state"]["tasks"]["archive.run"]["accepted_evidence"]
    assert accepted["run_artifact_path"] == str(matching)


def test_archive_run_prove_rejects_deleted_artifact_with_repair(tmp_path: Path) -> None:
    """EC-003: artifact deleted between archive and prove → repair instructs re-archive."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    contract, state = _demo_contract_and_state(project_root, livespec_root)
    artifact_path = _archive_fixture_artifact(project_root, contract, state)
    artifact_path.unlink()

    result = prove_goal_task(
        contract,
        state,
        "archive.run",
        evidence={"run_artifact_path": str(artifact_path)},
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert any(item.startswith("run_artifact_valid:") for item in result["missing_evidence"])
    assert any("livespec goal archive" in action for action in result["required_actions"])


# ─── Feature 059 Step 9 — registry sweep + end-to-end proof chain ─────────────


@pytest.mark.level_3a
def test_every_registry_command_contract_ends_with_archive_run(tmp_path: Path) -> None:
    """SC-001: sweep over the real command registry — every goal-locked
    contract's max-ordinal task id is archive.run."""
    from validator.command_registry import discover_commands

    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    commands = discover_commands(_repo_root() / ".agent-sync" / "skills")
    assert commands, "registry discovery returned no commands"

    for info in commands:
        goal = compile_command_goal(
            info.name,
            project_root=project_root,
            livespec_root=_repo_root(),
            feature=None,
            flags="",
        )
        contract = json.loads(render_goal_contract_file(goal))
        last_task = max(contract["tasks"], key=lambda task: int(task["ordinal"]))
        assert last_task["id"] == "archive.run", (
            f"{info.name} contract max-ordinal task is {last_task['id']!r}"
        )


def test_archive_run_end_to_end_drill(tmp_path: Path) -> None:
    """SC-002/SC-004 drill: prove prior tasks → archive → prove archive.run
    → ACCEPTED on first attempt; the artifact outcome is success while its
    snapshot still shows archive.run pending (self-reference exclusion)."""
    from validator.run_artifacts import archive_goal_run

    project_root, livespec_root = _fixture_roots(tmp_path)
    contract, state = _demo_contract_and_state(project_root, livespec_root, flags="")

    # Prove every prior (non-archive) task with generic evidence.
    for task in contract["tasks"]:
        if task["id"] == "archive.run":
            continue
        result = prove_goal_task(
            contract,
            state,
            str(task["id"]),
            evidence={"output": "done", "success_criteria_met": True},
            project_root=project_root,
        )
        assert result["status"] == "ACCEPTED", result
        state = result["state"]

    archive = archive_goal_run(contract, state, project_root=project_root, exit_code=0)
    assert archive.path is not None
    # SC-004: success despite archive.run pending in the embedded snapshot.
    assert archive.outcome == "success"
    assert archive.artifact is not None
    snapshot = {
        task["id"]: task["status"] for task in json_fixture(archive.artifact)["goal"]["tasks"]
    }
    assert snapshot["archive.run"] == "pending"
    assert json_fixture(archive.artifact)["verify_result"]["outcome"] == "success"

    # SC-002: the printed artifact path is accepted on the first attempt.
    proof = prove_goal_task(
        contract,
        state,
        "archive.run",
        evidence={"run_artifact_path": str(archive.path)},
        project_root=project_root,
    )
    assert proof["status"] == "ACCEPTED"
    final_state = proof["state"]
    assert all(task["status"] == "complete" for task in final_state["tasks"].values())
    assert final_state["status"] == "complete"
