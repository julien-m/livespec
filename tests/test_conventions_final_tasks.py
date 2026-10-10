"""Regressions for final conventions obligations and preparatory read/apply proof."""

import json
from pathlib import Path
from typing import Any

import pytest

from tests.test_conventions_verify_scope import _write_empty_gates
from tests.test_goal_contracts import _repo_root, _write_conventions
from validator.goal_contracts import (
    compile_command_goal,
    prove_goal_task,
    render_goal_contract_file,
    render_goal_state_file,
)


# The public goal facade exposes heterogeneous legacy JSON dictionaries.
def _goal(tmp_path: Path, command: str) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    project = tmp_path / "project"
    project.mkdir()
    _write_conventions(project, tmp_path / "ai")
    _write_empty_gates(project)
    goal = compile_command_goal(
        command,
        project_root=project,
        livespec_root=_repo_root(),
        feature="001-demo",
        flags="--functional --model=gpt-6.1-sol",
    )
    return (
        project,
        json.loads(render_goal_contract_file(goal)),
        json.loads(render_goal_state_file(goal)),
    )


def _read_apply() -> dict[str, object]:
    return {
        "output": "Preparatory directory check completed without final certification.",
        "success_criteria_met": True,
        "convention_domains": ["code", "design-tokens"],
        "convention_sources": [
            "$AIRESOURCES/code-conventions/general.md",
            "$AIRESOURCES/code-conventions/python.md",
            "$AIRESOURCES/design/tokens.md",
        ],
        "conventions_applied_to_output": True,
    }


@pytest.mark.parametrize("command", ["spec-implement", "spec-test", "spec-fix", "spec-ship"])
def test_ac004_only_final_declared_row_requires_both_receipts(tmp_path: Path, command: str) -> None:
    _, contract, _ = _goal(tmp_path, command)
    tasks = contract["tasks"]
    final = [task for task in tasks if "conventions_receipt_path" in task["required_evidence"]]
    assert len(final) == 1
    assert "repo_conventions_receipt_path" in final[0]["required_evidence"]
    assert tasks[-2]["id"] == final[0]["id"]
    assert tasks[-1]["id"] == "archive.run"
    early = [task for task in tasks if task.get("required_conventions") and task not in final]
    assert early
    assert all("convention_sources_read" in task["required_evidence"] for task in early)
    assert all("repo_conventions_receipt_path" not in task["required_evidence"] for task in early)


def test_ac004_early_read_apply_accepts_without_pass(tmp_path: Path) -> None:
    project, contract, state = _goal(tmp_path, "spec-fix")
    task = next(task for task in contract["tasks"] if task.get("required_conventions"))
    result = prove_goal_task(contract, state, task["id"], _read_apply(), project_root=project)
    assert result["accepted"] is True


@pytest.mark.parametrize(
    "missing", ["convention_domains", "convention_sources", "conventions_applied_to_output"]
)
def test_ac004_early_missing_read_apply_still_rejects(tmp_path: Path, missing: str) -> None:
    project, contract, state = _goal(tmp_path, "spec-fix")
    task = next(task for task in contract["tasks"] if task.get("required_conventions"))
    evidence = _read_apply()
    del evidence[missing]
    result = prove_goal_task(contract, state, task["id"], evidence, project_root=project)
    assert result["accepted"] is False
    assert result["missing_evidence"]
