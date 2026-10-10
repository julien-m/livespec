"""Focused fixture builders shared by Feature 076 test modules."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path

from typer.testing import CliRunner

from validator.cli import app
from validator.goal_contracts import (
    compile_command_goal,
    render_goal_contract_file,
    render_goal_state_file,
)
from validator.goal_json import JsonObject

_REPO_ROOT = Path(__file__).resolve().parents[1]
_RUNNER = CliRunner()


def compiled_valid_pair(project_root: Path) -> tuple[JsonObject, JsonObject]:
    """Build the complete production-shaped bootstrap pair used by pairing tests."""
    goal = compile_command_goal(
        "spec-init",
        project_root=project_root.resolve(),
        livespec_root=_REPO_ROOT,
        flags="--auto",
    )
    return json.loads(render_goal_contract_file(goal)), json.loads(render_goal_state_file(goal))


def rehash_pair(contract: JsonObject, state: JsonObject) -> None:
    """Rebind a mutated canonical fixture to a matching contract/state hash."""
    canonical_json = json.dumps(
        contract["canonical"], sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    goal_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    contract["canonical_json"] = canonical_json
    contract["goal_hash"] = goal_hash
    state["goal_hash"] = goal_hash


def proof_pair(project_root: Path) -> tuple[JsonObject, JsonObject, str]:
    """Build a one-task bootstrap pair for proof-transition tests."""
    contract, state = compiled_valid_pair(project_root)
    task: JsonObject = {
        "id": "task.001.proof",
        "ordinal": 1,
        "description": "record proof",
        "category": "execution",
        "evidence_kind": "documentary",
        "completion_actor": "goal",
        "required_evidence": ["observable_output_or_artifact"],
        "invalid_substitutes": [],
        "repair_if_missing": ["provide output or artifact"],
        "expected_evidence": {},
    }
    contract["canonical"]["tasks"] = [task]
    contract["tasks"] = [task]
    rehash_pair(contract, state)
    task_id = str(task["id"])
    state = {
        "schema_version": contract["schema_version"],
        "goal_hash": contract["goal_hash"],
        "command": "spec-init",
        "status": "active",
        "tasks": {
            task_id: {
                "ordinal": 1,
                "description": task["description"],
                "status": "pending",
                "attempts": [],
                "accepted_evidence": None,
                "last_rejection": None,
            }
        },
    }
    return contract, state, task_id


def add_other_task(contract: JsonObject, state: JsonObject, *, pending: bool) -> None:
    """Add a second task and rebind the pair for global-status transition tests."""
    task: JsonObject = {
        "id": "task.002.other",
        "ordinal": 2,
        "description": "other task",
        "category": "execution",
        "evidence_kind": "documentary",
        "completion_actor": "goal",
        "required_evidence": ["observable_output_or_artifact"],
        "invalid_substitutes": [],
        "repair_if_missing": ["provide evidence"],
        "expected_evidence": {},
    }
    contract["canonical"]["tasks"].append(task)
    contract["tasks"].append(task)
    rehash_pair(contract, state)
    state["tasks"][str(task["id"])] = {
        "ordinal": 2,
        "description": task["description"],
        "status": "pending" if pending else "complete",
        "attempts": [],
        "accepted_evidence": None if pending else {"output": "other"},
        "last_rejection": None,
    }


def archive_valid_pair(
    project_root: Path,
    *,
    feature: str | None = "076-x",
    pending: bool = False,
) -> tuple[JsonObject, JsonObject]:
    """Build a minimal archive pair with no receipt-bearing tasks."""
    task: JsonObject = {
        "id": "task.001.pending",
        "ordinal": 1,
        "description": "pending",
        "category": "execution",
        "completion_actor": "goal",
        "required_evidence": ["observable_output_or_artifact"],
        "invalid_substitutes": [],
        "repair_if_missing": ["provide evidence"],
        "expected_evidence": {},
    }
    tasks = [deepcopy(task)] if pending else []
    canonical: JsonObject = {
        "schema_version": "2.0",
        "command": "spec-init",
        "feature": feature,
        "project_root": project_root.resolve().as_posix(),
        "normalized_flags": [],
        "tasks": tasks,
        "verify_rules": {"must": [], "may": [], "must_not": [], "when": []},
    }
    canonical_json = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    goal_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    contract: JsonObject = {
        "schema_version": canonical["schema_version"],
        "command": canonical["command"],
        "feature": canonical["feature"],
        "project_root": canonical["project_root"],
        "normalized_flags": canonical["normalized_flags"],
        "tasks": canonical["tasks"],
        "canonical": canonical,
        "canonical_json": canonical_json,
        "goal_hash": goal_hash,
    }
    return contract, _archive_state(tasks, goal_hash)


def write_pair(control_root: Path, pair: tuple[JsonObject, JsonObject]) -> tuple[Path, Path]:
    """Persist explicit contract/state control files for CLI tests."""
    contract_file = control_root / "goal.contract.json"
    state_file = control_root / "goal.state.json"
    contract_file.write_text(json.dumps(pair[0]), encoding="utf-8")
    state_file.write_text(json.dumps(pair[1]), encoding="utf-8")
    return contract_file, state_file


def render_saved_bootstrap(target: Path) -> tuple[Path, Path, JsonObject]:
    """Render and locate a saved bootstrap pair for retargeting tests."""
    result = _RUNNER.invoke(
        app,
        ["goal", "render", "spec-init", "--flags", f"--auto --dir {target}", "--save"],
    )
    assert result.exit_code == 0, result.output
    match = re.search(r"contract-file:(\S+) \| state-file:(\S+)", result.output)
    assert match is not None
    contract_file, state_file = map(Path, match.groups())
    return contract_file, state_file, json.loads(contract_file.read_text(encoding="utf-8"))


def mark_all_tasks_complete(state_file: Path) -> None:
    """Complete a saved test state before archive."""
    state = json.loads(state_file.read_text(encoding="utf-8"))
    state["status"] = "complete"
    for task_state in state["tasks"].values():
        task_state["status"] = "complete"
    state_file.write_text(json.dumps(state), encoding="utf-8")


def prove_relative_artifact(contract_file: Path, state_file: Path, task_id: str) -> None:
    """Prove one target-relative fixture without accepting a blocked result."""
    result = _RUNNER.invoke(
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
            json.dumps({"artifact_path": "proof.txt"}),
        ],
    )
    assert result.exit_code in {0, 1}, result.output
    assert "goal prove blocked:" not in result.stderr


def archive_pair(contract_file: Path, state_file: Path) -> Path:
    """Archive a saved fixture and return its drift artifact path."""
    result = _RUNNER.invoke(
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
    assert result.exit_code == 1, result.output
    envelope = json.loads(result.stdout)
    assert envelope["outcome"] == "drift"
    return Path(envelope["archived"])


def _archive_state(tasks: list[JsonObject], goal_hash: str) -> JsonObject:
    return {
        "schema_version": "2.0",
        "command": "spec-init",
        "goal_hash": goal_hash,
        "status": "active" if tasks else "complete",
        "tasks": {
            str(task["id"]): {
                "ordinal": task["ordinal"],
                "description": task["description"],
                "status": "pending",
                "attempts": [],
                "accepted_evidence": None,
                "last_rejection": None,
            }
            for task in tasks
        },
    }
