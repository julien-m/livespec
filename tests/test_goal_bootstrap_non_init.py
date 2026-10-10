"""Compatibility tests for strict non-``spec-init`` goal operations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import pytest
from typer.testing import CliRunner

from validator.cli import app
from validator.goal_contracts import compile_command_goal, render_goal_contract_file

runner = CliRunner()
GOAL_HASH = "b" * 64
REPO_ROOT = Path(__file__).resolve().parents[1]


def write_non_init_pair(root: Path, *, flags: list[str] | None = None) -> tuple[Path, Path, str]:
    task_id = "task.001.compatibility"
    task = {
        "id": task_id,
        "ordinal": 1,
        "description": "preserve compatibility",
        "required_evidence": ["observable_output_or_artifact", "success_criteria_met"],
        "invalid_substitutes": [],
        "repair_if_missing": ["supply complete evidence"],
    }
    contract: dict[str, Any] = {
        "schema_version": "2.0",
        "goal_hash": GOAL_HASH,
        "command": "spec-plan",
        "feature": None,
        "normalized_flags": flags or [],
        "tasks": [task],
        "canonical": {"verify_rules": {"must": [], "may": [], "must_not": [], "when": []}},
    }
    state = {
        "schema_version": "2.0",
        "goal_hash": GOAL_HASH,
        "command": "spec-plan",
        "status": "active",
        "tasks": {
            task_id: {
                "ordinal": 1,
                "description": "preserve compatibility",
                "status": "pending",
                "attempts": [],
                "accepted_evidence": None,
                "last_rejection": None,
            }
        },
    }
    contract_file = root / "goal.contract.json"
    state_file = root / "goal.state.json"
    contract_file.write_text(json.dumps(contract), encoding="utf-8")
    state_file.write_text(json.dumps(state), encoding="utf-8")
    return contract_file, state_file, task_id


@pytest.mark.parametrize("operation", ["render", "prove", "archive"])
def test_non_init_operations_require_initialized_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: Literal["render", "prove", "archive"],
) -> None:
    control = tmp_path / "control"
    fresh = tmp_path / "fresh"
    control.mkdir()
    fresh.mkdir()
    contract_file, state_file, task_id = write_non_init_pair(control)
    state_before = state_file.read_bytes()
    monkeypatch.chdir(fresh)
    if operation == "render":
        args = ["goal", "render", "spec-plan", "--save"]
    elif operation == "prove":
        args = [
            "goal",
            "prove",
            "--contract",
            str(contract_file),
            "--state",
            str(state_file),
            "--task",
            task_id,
            "--evidence",
            '{"output":"done","success_criteria_met":true}',
        ]
    else:
        args = [
            "goal",
            "archive",
            "--contract",
            str(contract_file),
            "--state",
            str(state_file),
        ]

    result = runner.invoke(app, args)

    assert result.exit_code == 2
    assert ".specs/ directory not found" in result.output
    assert "Traceback" not in result.output
    assert state_file.read_bytes() == state_before
    assert not (fresh / ".specs").exists()
    assert not list(fresh.iterdir())


@pytest.mark.parametrize("operation", ["prove", "archive"])
def test_dir_shaped_flags_do_not_relax_non_init_pair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: Literal["prove", "archive"],
) -> None:
    control = tmp_path / "control"
    fresh = tmp_path / "fresh"
    foreign = tmp_path / "foreign"
    control.mkdir()
    fresh.mkdir()
    foreign.mkdir()
    contract_file, state_file, task_id = write_non_init_pair(control, flags=[f"--dir={foreign}"])
    monkeypatch.chdir(fresh)
    args = [
        "goal",
        operation,
        "--contract",
        str(contract_file),
        "--state",
        str(state_file),
    ]
    if operation == "prove":
        args += ["--task", task_id, "--evidence", "{}"]

    result = runner.invoke(app, args)

    assert result.exit_code == 2
    assert ".specs/ directory not found" in result.output
    assert not (fresh / ".specs").exists()
    assert not (foreign / ".specs").exists()


def test_initialized_non_init_proof_keeps_external_path_classification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    control = tmp_path / "control"
    external = tmp_path / "external.txt"
    (project / ".specs").mkdir(parents=True)
    control.mkdir()
    external.write_text("proof", encoding="utf-8")
    contract_file, state_file, task_id = write_non_init_pair(control)
    monkeypatch.chdir(project)

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
            json.dumps(
                {
                    "output": "done",
                    "success_criteria_met": True,
                    "artifact_path": str(external),
                }
            ),
        ],
    )

    assert result.exit_code == 0, result.output
    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["tasks"][task_id]["accepted_evidence"]["artifact_path"] == str(external)


def test_initialized_non_init_rejected_proof_keeps_existing_semantics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    control = tmp_path / "control"
    (project / ".specs").mkdir(parents=True)
    control.mkdir()
    contract_file, state_file, task_id = write_non_init_pair(control)
    before = json.loads(state_file.read_text())
    monkeypatch.chdir(project)

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
            "{}",
        ],
    )

    state = json.loads(state_file.read_text())
    assert result.exit_code == 1
    assert json.loads(result.stdout)["status"] == "REJECTED_NEEDS_ACTION"
    assert state["tasks"][task_id]["status"] == "pending"
    assert (
        state["tasks"][task_id]["accepted_evidence"]
        == before["tasks"][task_id]["accepted_evidence"]
    )


@pytest.mark.parametrize(
    ("complete", "exit_code", "outcome", "expected_exit"),
    [(True, 0, "success", 0), (False, 0, "drift", 1), (True, 1, "error", 1)],
)
def test_initialized_non_init_archive_outcomes_are_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    complete: bool,
    exit_code: int,
    outcome: str,
    expected_exit: int,
) -> None:
    project = tmp_path / "project"
    control = tmp_path / "control"
    (project / ".specs").mkdir(parents=True)
    control.mkdir()
    contract_file, state_file, task_id = write_non_init_pair(control)
    if complete:
        state = json.loads(state_file.read_text())
        state["status"] = "complete"
        state["tasks"][task_id]["status"] = "complete"
        state_file.write_text(json.dumps(state), encoding="utf-8")
    before = state_file.read_bytes()
    monkeypatch.chdir(project)

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
            str(exit_code),
            "--json",
        ],
    )

    assert result.exit_code == expected_exit, result.output
    assert json.loads(result.stdout)["outcome"] == outcome
    assert state_file.read_bytes() == before


def test_non_init_contract_hash_and_bytes_do_not_gain_project_root(tmp_path: Path) -> None:
    (tmp_path / ".specs").mkdir()

    first = compile_command_goal("spec-plan", project_root=tmp_path, livespec_root=REPO_ROOT)
    second = compile_command_goal("spec-plan", project_root=tmp_path, livespec_root=REPO_ROOT)
    contract = json.loads(render_goal_contract_file(first))

    assert first.goal_hash == second.goal_hash
    assert first.canonical_json == second.canonical_json
    assert "project_root" not in first.payload
    assert "project_root" not in contract
