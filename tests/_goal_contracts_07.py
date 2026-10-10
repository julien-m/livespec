"""Preserved test cases and fixtures for test_goal_contracts.py."""

from __future__ import annotations

import json
from pathlib import Path

from tests._goal_contracts_01 import _repo_root
from tests._goal_contracts_02 import _write_complete_check_fix_scenario, _write_conventions
from validator.goal_contracts import (
    compile_command_goal,
    render_goal_contract_file,
)


def test_spec_check_fix_all_goal_keeps_child_spawns_indicative(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "complete-project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions(project_root, tmp_path / "ai")
    feature = _write_complete_check_fix_scenario(project_root)

    goal = compile_command_goal(
        "spec-check",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature=None,
        flags="--fix --all",
    )
    tasks = goal.payload["execution_tasks"]
    contract = json.loads(render_goal_contract_file(goal))

    assert goal.payload["runtime_context"]["is_visual_feature"] is True
    assert goal.payload["runtime_context"]["has_penflow"] is True
    assert goal.payload["runtime_context"]["visual_feature_slugs"] == [feature]
    assert any("tree/spec quality" in task for task in tasks)
    assert any("FR/AC mapping" in task for task in tasks)
    assert any("missing or blocked tests" in task for task in tasks)
    assert any("visual fidelity" in task for task in tasks)
    assert any("absent or stale baseline manifests" in task for task in tasks)
    assert any("Penflow drift" in task for task in tasks)
    assert any("changelog/report drift" in task for task in tasks)
    assert any("README sync" in task for task in tasks)
    assert any("Create missing visual/Penflow prerequisites" in task for task in tasks)
    assert any("Spawn independent native sub-agent to execute `/spec-fix" in task for task in tasks)
    assert any(
        "Spawn independent native sub-agent to re-run `/spec-check" in task for task in tasks
    )
    # 081: nested goals are optional, so child spawns stay in the indicative checklist.
    assert any("/spec-fix <feature> --auto --update" in row for row in contract["checklist"])
    assert not any(str(task["id"]).startswith("fix.child_goal") for task in contract["tasks"])
    assert any(task["id"] == "visual.design_fidelity" for task in contract["tasks"])
    assert feature in (project_root / ".specs" / "design" / "screens" / "index.md").read_text(
        encoding="utf-8"
    )
    assert (project_root / "penflow" / "compare-report.json").exists()
    assert (
        project_root / ".specs" / "features" / feature / "baselines" / "baseline.manifest.yml"
    ).exists()


def test_spec_fix_child_spec_check_spawn_is_indicative(tmp_path: Path) -> None:
    """081 AC-001/AC-004: a child without its own goal cannot falsely block the parent."""
    project_root = tmp_path / "complete-project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions(project_root, tmp_path / "ai")
    feature = _write_complete_check_fix_scenario(project_root)
    goal = compile_command_goal(
        "spec-fix",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature=feature,
        flags="--auto --update",
    )
    contract = json.loads(render_goal_contract_file(goal))

    assert goal.payload["goal_requirement"] == "required"
    assert not any(str(task["id"]).startswith("fix.child_goal") for task in contract["tasks"])
    assert any("/spec-check" in row for row in contract["checklist"])
    assert contract["tasks"][-2]["id"] == "outcome.verified"


def test_spec_check_design_fidelity_contract_rejects_normalized_json_substitute(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "complete-project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions(project_root, tmp_path / "ai")
    _write_complete_check_fix_scenario(project_root)

    goal = compile_command_goal(
        "spec-check",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature=None,
        flags="--fix --all",
    )
    contract = json.loads(render_goal_contract_file(goal))
    visual_task = next(task for task in contract["tasks"] if task["id"] == "visual.design_fidelity")

    assert "visual_evidence_receipt_path" in visual_task["required_evidence"]
    assert "normalized_json_alignment_only" in visual_task["invalid_substitutes"]
    assert "worker_declared_diff_without_receipt" in visual_task["invalid_substitutes"]
    assert any("export mockup PNG" in action for action in visual_task["repair_if_missing"])
