"""Pairing and input-boundary tests for ``spec-init`` goal control files."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Literal

import pytest
from typer.testing import CliRunner

from tests.goal_bootstrap_support import compiled_valid_pair as valid_pair
from tests.goal_bootstrap_support import rehash_pair as _rehash
from validator.cli import app
from validator.goal_json import JsonObject
from validator.goal_pairing import GoalPairError, claims_spec_init, validate_goal_pair

runner = CliRunner()


def _apply_schema_defect(contract: JsonObject, state: JsonObject, defect: str) -> None:
    canonical = contract["canonical"]
    task = canonical["tasks"][0]
    task_id = task["id"]
    if defect == "schema_type":
        canonical["schema_version"] = contract["schema_version"] = state["schema_version"] = 2
    elif defect == "flags_type":
        canonical["normalized_flags"] = contract["normalized_flags"] = "--auto"
    elif defect == "duplicate_task_id":
        duplicate = deepcopy(task)
        duplicate["ordinal"] = 2
        canonical["tasks"] = contract["tasks"] = [task, duplicate]
    elif defect == "state_bool_ordinal":
        state["tasks"][task_id]["ordinal"] = True
    elif defect == "state_float_ordinal":
        state["tasks"][task_id]["ordinal"] = 1.0
    elif defect == "missing_required_evidence":
        task.pop("required_evidence")
        contract["tasks"] = canonical["tasks"]
    elif defect in {"attempts", "accepted_evidence", "last_rejection"}:
        state["tasks"][task_id][defect] = "invalid"
    _rehash(contract, state)


@pytest.mark.parametrize("operation", ["prove", "archive"])
@pytest.mark.parametrize(
    "defect",
    [
        "schema_type",
        "flags_type",
        "duplicate_task_id",
        "state_bool_ordinal",
        "state_float_ordinal",
        "missing_required_evidence",
        "attempts",
        "accepted_evidence",
        "last_rejection",
    ],
)
def test_rehashed_invalid_schema_types_fail_before_root_access(
    tmp_path: Path, operation: Literal["prove", "archive"], defect: str
) -> None:
    contract, state = valid_pair(tmp_path)
    _apply_schema_defect(contract, state, defect)
    with pytest.raises(GoalPairError, match=f"before {operation}"):
        validate_goal_pair(contract, state, operation=operation)


def test_unhashable_command_claims_fail_closed_without_type_error(tmp_path: Path) -> None:
    contract, state = valid_pair(tmp_path)
    contract["command"] = ["spec-init"]

    assert claims_spec_init(contract, state)
    with pytest.raises(GoalPairError):
        validate_goal_pair(contract, state, operation="prove")


def _apply_pair_defect(contract: JsonObject, state: JsonObject, defect: str) -> None:
    task_id = next(iter(state["tasks"]))
    if defect == "missing_contract":
        contract.pop("normalized_flags")
    elif defect == "missing_state":
        state.pop("status")
    elif defect == "canonical_json_malformed":
        contract["canonical_json"] = "{"
    elif defect == "canonical_json_different":
        contract["canonical_json"] = "{}"
    elif defect == "contract_hash":
        contract["goal_hash"] = "0" * 64
    elif defect == "state_hash":
        state["goal_hash"] = "0" * 64
    elif defect == "state_task_key":
        state["tasks"][f"{task_id}.foreign"] = state["tasks"].pop(task_id)
    elif defect == "state_description":
        state["tasks"][task_id]["description"] = "foreign"
    elif defect == "legacy_rootless":
        contract["canonical"].pop("project_root")
    elif defect == "complete_with_pending":
        state["status"] = "complete"
    elif defect == "active_with_complete":
        state["status"] = "complete"
        for task_state in state["tasks"].values():
            task_state["status"] = "complete"
        state["status"] = "active"


@pytest.mark.parametrize("operation", ["prove", "archive"])
@pytest.mark.parametrize(
    "defect",
    [
        "missing_contract",
        "missing_state",
        "canonical_json_malformed",
        "canonical_json_different",
        "contract_hash",
        "state_hash",
        "state_task_key",
        "state_description",
        "legacy_rootless",
        "complete_with_pending",
        "active_with_complete",
    ],
)
def test_pairing_identity_matrix_rejects_every_atomic_defect(
    tmp_path: Path, operation: Literal["prove", "archive"], defect: str
) -> None:
    contract, state = valid_pair(tmp_path)
    _apply_pair_defect(contract, state, defect)
    before = deepcopy(state)

    with pytest.raises(GoalPairError, match=f"before {operation}"):
        validate_goal_pair(contract, state, operation=operation)

    assert state == before


@pytest.mark.parametrize(
    ("target", "key", "value"),
    [
        ("contract", "schema_version", "9.9"),
        ("contract", "command", "spec-plan"),
        ("contract", "feature", "foreign"),
        ("contract", "project_root", "/foreign"),
        ("contract", "normalized_flags", ["--foreign"]),
        ("contract", "tasks", []),
        ("state", "schema_version", "9.9"),
        ("state", "command", "spec-plan"),
        ("state", "goal_hash", "0" * 64),
        ("state", "status", "invalid"),
    ],
)
@pytest.mark.parametrize("operation", ["prove", "archive"])
def test_atomic_pair_defects_fail_closed(
    tmp_path: Path,
    target: str,
    key: str,
    value: object,
    operation: Literal["prove", "archive"],
) -> None:
    contract, state = valid_pair(tmp_path)
    mutated = contract if target == "contract" else state
    mutated[key] = value
    before = deepcopy(state)

    with pytest.raises(GoalPairError, match="rerender"):
        validate_goal_pair(contract, state, operation=operation)

    assert state == before


@pytest.mark.parametrize("operation", ["prove", "archive"])
@pytest.mark.parametrize("defect", ["ordinal", "task_status"])
def test_task_and_status_defects_fail_closed(
    tmp_path: Path, operation: Literal["prove", "archive"], defect: str
) -> None:
    contract, state = valid_pair(tmp_path)
    task_id = next(iter(state["tasks"]))
    if defect == "ordinal":
        state["tasks"][task_id]["ordinal"] += 1
    else:
        state["tasks"][task_id]["status"] = "invalid"
    before = deepcopy(state)

    with pytest.raises(GoalPairError):
        validate_goal_pair(contract, state, operation=operation)

    assert state == before


def test_complete_status_requires_all_tasks_complete(tmp_path: Path) -> None:
    contract, state = valid_pair(tmp_path)
    state["status"] = "complete"

    with pytest.raises(GoalPairError):
        validate_goal_pair(contract, state, operation="archive")


def test_any_spec_init_claim_selects_bootstrap_validator(tmp_path: Path) -> None:
    contract, state = valid_pair(tmp_path)
    contract["command"] = "spec-plan"

    assert claims_spec_init(contract, state)
    with pytest.raises(GoalPairError):
        validate_goal_pair(contract, state, operation="prove")


@pytest.mark.parametrize("operation", ["prove", "archive"])
@pytest.mark.parametrize("option", ["--contract", "--state"])
@pytest.mark.parametrize("value", [None, ""])
def test_missing_or_empty_pair_option_uses_blocked_boundary(
    tmp_path: Path, operation: str, option: str, value: str | None
) -> None:
    contract, state = valid_pair(tmp_path)
    contract_file = tmp_path / "goal.contract.json"
    state_file = tmp_path / "goal.state.json"
    contract_file.write_text(json.dumps(contract), encoding="utf-8")
    state_file.write_text(json.dumps(state), encoding="utf-8")
    args = ["goal", operation]
    if operation == "prove":
        args += ["--task", next(iter(state["tasks"])), "--evidence", "{}"]
    for name, path in (("--contract", contract_file), ("--state", state_file)):
        if name != option:
            args += [name, str(path)]
        elif value is not None:
            args += [name, value]

    result = runner.invoke(app, args)

    assert result.exit_code == 2
    assert f"goal {operation} blocked:" in result.output
    assert "Traceback" not in result.output


def test_archive_json_block_is_one_envelope(tmp_path: Path) -> None:
    result = runner.invoke(app, ["goal", "archive", "--contract", "", "--json"])

    assert result.exit_code == 2
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 1
    assert json.loads(lines[0])["outcome"] == "blocked"


@pytest.mark.parametrize("operation", ["prove", "archive"])
@pytest.mark.parametrize("option", ["--contract", "--state"])
@pytest.mark.parametrize("kind", ["nonfile", "malformed", "unreadable"])
def test_invalid_control_files_have_actionable_blocked_boundary(
    tmp_path: Path, operation: str, option: str, kind: str
) -> None:
    contract, state = valid_pair(tmp_path)
    paths = {
        "--contract": tmp_path / "goal.contract.json",
        "--state": tmp_path / "goal.state.json",
    }
    paths["--contract"].write_text(json.dumps(contract), encoding="utf-8")
    paths["--state"].write_text(json.dumps(state), encoding="utf-8")
    target = paths[option]
    if kind == "nonfile":
        target.unlink()
        target.mkdir()
    elif kind == "malformed":
        target.write_text("{", encoding="utf-8")
    else:
        target.chmod(0)
    args = [
        "goal",
        operation,
        "--contract",
        str(paths["--contract"]),
        "--state",
        str(paths["--state"]),
    ]
    if operation == "prove":
        args += ["--task", next(iter(state["tasks"])), "--evidence", "{}"]
    result = runner.invoke(app, args)
    if kind == "unreadable":
        target.chmod(0o600)
    assert result.exit_code == 2
    assert f"goal {operation} blocked:" in result.output
    assert f"rerender the goal before {operation}" in result.output
    assert "Traceback" not in result.output
