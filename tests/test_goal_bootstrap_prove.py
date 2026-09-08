"""Proof transition and evidence confinement tests for bootstrap goals."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from tests.goal_bootstrap_support import (
    add_other_task as _add_other_task,
)
from tests.goal_bootstrap_support import (
    compiled_valid_pair,
    proof_pair,
)
from validator import goal_pairing
from validator.cli import app
from validator.goal_contracts import prove_goal_task
from validator.goal_evidence_paths import GoalEvidencePathError
from validator.goal_pairing import GoalPairError

runner = CliRunner()


@pytest.mark.parametrize("initial_complete", [False, True])
@pytest.mark.parametrize("accepted", [False, True])
@pytest.mark.parametrize("other_pending", [False, True])
def test_complete_proof_transition_matrix(
    tmp_path: Path, initial_complete: bool, accepted: bool, other_pending: bool
) -> None:
    contract, state, task_id = proof_pair(tmp_path)
    _add_other_task(contract, state, pending=other_pending)
    task_before = state["tasks"][task_id]
    if initial_complete:
        task_before["status"] = "complete"
        task_before["accepted_evidence"] = {"output": "A"}
    state["status"] = "active" if other_pending or not initial_complete else "complete"
    other_before = json.dumps(state["tasks"]["task.002.other"], sort_keys=True)

    result = prove_goal_task(contract, state, task_id, {"output": "B"} if accepted else {})

    task = result["state"]["tasks"][task_id]
    assert result["status"] == ("ACCEPTED" if accepted else "REJECTED_NEEDS_ACTION")
    assert task["status"] == ("complete" if accepted else "pending")
    expected_proof = (
        {"output": "B"} if accepted else ({"output": "A"} if initial_complete else None)
    )
    assert task["accepted_evidence"] == expected_proof
    assert result["state"]["status"] == ("active" if other_pending or not accepted else "complete")
    assert json.dumps(result["state"]["tasks"]["task.002.other"], sort_keys=True) == other_before
    assert len(task["attempts"]) == 1


def test_pending_acceptance_completes_named_task(tmp_path: Path) -> None:
    contract, state, task_id = proof_pair(tmp_path)

    result = prove_goal_task(contract, state, task_id, {"output": "B"})

    task = result["state"]["tasks"][task_id]
    assert result["status"] == "ACCEPTED"
    assert task["status"] == "complete"
    assert task["accepted_evidence"] == {"output": "B"}
    assert result["state"]["status"] == "complete"
    assert state["tasks"][task_id]["status"] == "pending"


def test_complete_rejection_reopens_and_retains_evidence(tmp_path: Path) -> None:
    contract, state, task_id = proof_pair(tmp_path)
    state["status"] = "complete"
    state["tasks"][task_id]["status"] = "complete"
    state["tasks"][task_id]["accepted_evidence"] = {"output": "A"}

    result = prove_goal_task(contract, state, task_id, {})

    task = result["state"]["tasks"][task_id]
    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert task["status"] == "pending"
    assert task["accepted_evidence"] == {"output": "A"}
    assert result["state"]["status"] == "active"


def test_contained_relative_artifact_is_accepted(tmp_path: Path) -> None:
    contract, state, task_id = proof_pair(tmp_path)
    (tmp_path / "proof.txt").write_text("proof", encoding="utf-8")

    result = prove_goal_task(contract, state, task_id, {"path": "proof.txt"})

    assert result["status"] == "ACCEPTED"


@pytest.mark.parametrize("kind", ["absolute", "parent", "symlink", "broken"])
def test_project_evidence_escape_blocks_without_state_mutation(tmp_path: Path, kind: str) -> None:
    project = tmp_path / "project"
    outside = tmp_path / "outside.txt"
    project.mkdir()
    outside.write_text("outside", encoding="utf-8")
    contract, state, task_id = proof_pair(project)
    before = json.dumps(state, sort_keys=True)
    if kind == "absolute":
        evidence_path = outside.as_posix()
    elif kind == "parent":
        evidence_path = "../outside.txt"
    else:
        link = project / "proof.txt"
        link.symlink_to(outside if kind == "symlink" else tmp_path / "missing")
        evidence_path = "proof.txt"

    with pytest.raises(GoalEvidencePathError):
        prove_goal_task(contract, state, task_id, {"artifact_path": evidence_path})

    assert json.dumps(state, sort_keys=True) == before


def test_external_control_pair_paths_remain_allowed(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    contract, state, task_id = proof_pair(project)

    result = prove_goal_task(
        contract,
        state,
        task_id,
        {
            "output": "child complete",
            "child_contract_file": str(tmp_path / "goal.contract.json"),
            "child_state_file": str(tmp_path / "goal.state.json"),
        },
    )

    assert result["status"] == "ACCEPTED"


def test_external_evidence_file_uses_persisted_root_after_cwd_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    control = tmp_path / "control"
    caller = tmp_path / "caller"
    project.mkdir()
    control.mkdir()
    caller.mkdir()
    contract, state, task_id = proof_pair(project)
    contract_file = control / "goal.contract.json"
    state_file = control / "goal.state.json"
    evidence_file = control / "evidence.json"
    contract_file.write_text(json.dumps(contract), encoding="utf-8")
    state_file.write_text(json.dumps(state), encoding="utf-8")
    evidence_file.write_text(json.dumps({"output": "external B"}), encoding="utf-8")
    monkeypatch.chdir(caller)

    result = runner.invoke(
        app,
        [
            "goal",
            "prove",
            "--contract",
            str(contract_file),
            "--state",
            str(state_file),
            "--task",
            task_id,
            "--evidence",
            str(evidence_file),
        ],
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["status"] == "ACCEPTED"
    assert json.loads(state_file.read_text())["tasks"][task_id]["status"] == "complete"


@pytest.mark.parametrize("evidence_key", ["artifact_path", "conventions_receipt_path"])
@pytest.mark.parametrize("escape_kind", ["absolute", "parent", "symlink", "broken"])
def test_external_evidence_file_confines_payload_paths(
    tmp_path: Path,
    evidence_key: str,
    escape_kind: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    control = tmp_path / "control"
    caller = tmp_path / "caller"
    outside = tmp_path / "outside.json"
    project.mkdir()
    control.mkdir()
    caller.mkdir()
    outside.write_text("{}", encoding="utf-8")
    contract, state, task_id = proof_pair(project)
    contract_file = control / "goal.contract.json"
    state_file = control / "goal.state.json"
    evidence_file = control / "evidence.json"
    contract_file.write_text(json.dumps(contract), encoding="utf-8")
    state_file.write_text(json.dumps(state), encoding="utf-8")
    before = state_file.read_bytes()
    payload_path = _escaped_payload_path(tmp_path, project, outside, escape_kind)
    evidence_file.write_text(
        json.dumps({"output": "external B", evidence_key: payload_path}),
        encoding="utf-8",
    )
    monkeypatch.chdir(caller)

    result = runner.invoke(
        app,
        [
            "goal",
            "prove",
            "--contract",
            str(contract_file),
            "--state",
            str(state_file),
            "--task",
            task_id,
            "--evidence",
            str(evidence_file),
        ],
    )

    _assert_confined_rejection(result, escape_kind, state_file, before)


def _escaped_payload_path(tmp_path: Path, project: Path, outside: Path, escape_kind: str) -> str:
    if escape_kind == "absolute":
        return outside.as_posix()
    if escape_kind == "parent":
        return "../outside.json"
    project_link = project / "submitted.json"
    link_target = outside if escape_kind == "symlink" else tmp_path / "missing.json"
    project_link.symlink_to(link_target)
    return project_link.name


def _assert_confined_rejection(
    result: Result, escape_kind: str, state_file: Path, before: bytes
) -> None:
    assert result.exit_code == 2
    assert result.stdout == ""
    stderr = result.stderr
    assert stderr.startswith("goal prove blocked:")
    expected_reason = "unreadable" if escape_kind == "broken" else "escapes project_root"
    assert expected_reason in stderr
    assert "Traceback" not in result.output
    assert state_file.read_bytes() == before


def test_receipt_symlink_escape_is_blocked_without_state_mutation(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "receipt.json"
    outside.write_text("{}", encoding="utf-8")
    (project / "receipt.json").symlink_to(outside)
    contract, state, task_id = proof_pair(project)
    before = deepcopy(state)

    with pytest.raises(GoalEvidencePathError, match="escapes project_root"):
        prove_goal_task(
            contract,
            state,
            task_id,
            {"output": "B", "conventions_receipt_path": "receipt.json"},
        )

    assert state == before


def test_non_json_pair_is_rejected_before_project_root_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contract, state = compiled_valid_pair(tmp_path)
    task_id = next(iter(state["tasks"]))
    state["tasks"][task_id]["attempts"] = [object()]

    def fail_if_resolved(value: object, operation: object) -> Path:
        pytest.fail("project root was resolved before JSON closure")

    monkeypatch.setattr(goal_pairing, "_resolve_project_root", fail_if_resolved)

    with pytest.raises(GoalPairError, match="contains a non-JSON value"):
        goal_pairing.validate_goal_pair(contract, state, operation="prove")
