"""Preserved test cases and fixtures for test_goal_contracts.py."""

from __future__ import annotations

import json
from pathlib import Path

from tests._goal_contracts_01 import _repo_root
from tests._goal_contracts_02 import _write_complete_check_fix_scenario, _write_conventions
from validator.goal_contracts import (
    compile_command_goal,
    prove_goal_task,
    render_goal_contract_file,
    render_goal_state_file,
)


def test_spec_check_fix_all_complete_scenario_goal_requires_child_goals(
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
    task_descriptions = [task["description"] for task in contract["tasks"]]

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
    assert any("Inspect child goal state files" in task for task in tasks)
    assert any("canonical BLOCKED" in task for task in tasks)
    assert any("/spec-fix <feature> --auto --update" in task for task in task_descriptions)
    assert any("/spec-check <feature>" in task for task in task_descriptions)
    assert any(task["id"] == "visual.design_fidelity" for task in contract["tasks"])
    assert feature in (project_root / ".specs" / "design" / "screens" / "index.md").read_text(
        encoding="utf-8"
    )
    assert (project_root / "penflow" / "compare-report.json").exists()
    assert (
        project_root / ".specs" / "features" / feature / "baselines" / "baseline.manifest.yml"
    ).exists()


def test_spec_fix_child_spec_check_goal_cannot_be_skipped_with_zero_gap_report(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "complete-project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions(project_root, tmp_path / "ai")
    feature = _write_complete_check_fix_scenario(project_root)
    report_path = project_root / ".specs" / "features" / feature / "checks" / "2026-06-03.md"
    report_path.write_text(
        "# Spec Fix Report\n\nNo Feature gaps remain after verification.\n",
        encoding="utf-8",
    )
    goal = compile_command_goal(
        "spec-fix",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature=feature,
        flags="--auto --update",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))
    child_tasks = [
        task
        for task in contract["tasks"]
        if str(task["id"]).startswith("fix.child_goal.spec_check")
    ]
    assert child_tasks

    evidence = {
        "child_goal_skipped": True,
        "skip_reason": "zero_gap_report",
        "report_path": report_path.relative_to(project_root).as_posix(),
        "convention_domains": ["code", "design-tokens"],
        "convention_sources": [
            "$AIRESOURCES/code-conventions/general.md",
            "$AIRESOURCES/code-conventions/python.md",
            "$AIRESOURCES/design/tokens.md",
        ],
        "conventions_applied_to_output": True,
    }
    result = prove_goal_task(
        contract,
        state,
        str(child_tasks[0]["id"]),
        evidence,
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "child_goal_hash_recorded" in result["missing_evidence"]
    assert "child_contract_file_exists" in result["missing_evidence"]
    assert "child_state_file_exists" in result["missing_evidence"]
    assert "child_final_status_recorded" in result["missing_evidence"]


def test_spec_fix_child_spec_check_skip_requires_zero_gap_report(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "complete-project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions(project_root, tmp_path / "ai")
    feature = _write_complete_check_fix_scenario(project_root)
    report_path = project_root / ".specs" / "features" / feature / "checks" / "2026-06-03.md"
    report_path.write_text(
        "# Spec Fix Report\n\n- FR/AC mapping: one gap remains.\n",
        encoding="utf-8",
    )
    goal = compile_command_goal(
        "spec-fix",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature=feature,
        flags="--auto --update",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))
    child_task = next(
        task
        for task in contract["tasks"]
        if str(task["id"]).startswith("fix.child_goal.spec_check")
    )

    result = prove_goal_task(
        contract,
        state,
        str(child_task["id"]),
        {
            "child_goal_skipped": True,
            "skip_reason": "zero_gap_report",
            "report_path": report_path.relative_to(project_root).as_posix(),
            "convention_domains": ["code", "design-tokens"],
            "convention_sources": [
                "$AIRESOURCES/code-conventions/general.md",
                "$AIRESOURCES/code-conventions/python.md",
                "$AIRESOURCES/design/tokens.md",
            ],
            "conventions_applied_to_output": True,
        },
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "child_goal_hash_recorded" in result["missing_evidence"]


def test_child_goal_contract_and_state_paths_may_use_goal_artifacts_outside_project(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions(project_root, tmp_path / "ai")
    feature = _write_complete_check_fix_scenario(project_root)
    child_hash = "abc12345"
    child_dir = tmp_path / "livespec-goals"
    child_dir.mkdir()
    child_contract = child_dir / "goal-spec-check-abc12345.contract.json"
    child_state = child_dir / "goal-spec-check-abc12345.state.json"
    child_contract.write_text(
        json.dumps({"goal_hash": child_hash, "tasks": []}),
        encoding="utf-8",
    )
    child_state.write_text(
        json.dumps({"goal_hash": child_hash, "status": "complete"}),
        encoding="utf-8",
    )
    goal = compile_command_goal(
        "spec-fix",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature=feature,
        flags="--auto --update",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))
    child_task = next(
        task
        for task in contract["tasks"]
        if str(task["id"]).startswith("fix.child_goal.spec_check")
    )

    result = prove_goal_task(
        contract,
        state,
        str(child_task["id"]),
        {
            "child_goal_hash": child_hash,
            "child_contract_file": child_contract.as_posix(),
            "child_state_file": child_state.as_posix(),
            "child_final_status": "complete",
            "convention_domains": ["code", "design-tokens"],
            "convention_sources": [
                "$AIRESOURCES/code-conventions/general.md",
                "$AIRESOURCES/code-conventions/python.md",
                "$AIRESOURCES/design/tokens.md",
            ],
            "conventions_applied_to_output": True,
        },
        project_root=project_root,
    )

    assert result["status"] == "ACCEPTED"


def test_child_goal_contract_rejects_nested_goal_artifact_path(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions(project_root, tmp_path / "ai")
    feature = _write_complete_check_fix_scenario(project_root)
    child_hash = "abc12345"
    child_dir = tmp_path / "livespec-goals" / "child"
    child_dir.mkdir(parents=True)
    child_contract = child_dir / "goal-spec-check-abc12345.contract.json"
    child_state = child_dir / "goal-spec-check-abc12345.state.json"
    child_contract.write_text(
        json.dumps({"goal_hash": child_hash, "tasks": []}),
        encoding="utf-8",
    )
    child_state.write_text(
        json.dumps({"goal_hash": child_hash, "status": "complete"}),
        encoding="utf-8",
    )
    goal = compile_command_goal(
        "spec-fix",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature=feature,
        flags="--auto --update",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))
    child_task = next(
        task
        for task in contract["tasks"]
        if str(task["id"]).startswith("fix.child_goal.spec_check")
    )

    result = prove_goal_task(
        contract,
        state,
        str(child_task["id"]),
        {
            "child_goal_hash": child_hash,
            "child_contract_file": child_contract.as_posix(),
            "child_state_file": child_state.as_posix(),
            "child_final_status": "complete",
            "convention_domains": ["code", "design-tokens"],
            "convention_sources": [
                "$AIRESOURCES/code-conventions/general.md",
                "$AIRESOURCES/code-conventions/python.md",
                "$AIRESOURCES/design/tokens.md",
            ],
            "conventions_applied_to_output": True,
        },
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "child_contract_file_exists" in result["missing_evidence"]
    assert "child_state_file_exists" in result["missing_evidence"]


def test_child_goal_contract_rejects_arbitrary_absolute_path(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions(project_root, tmp_path / "ai")
    feature = _write_complete_check_fix_scenario(project_root)
    child_contract = tmp_path / "child.contract.json"
    child_state = tmp_path / "child.state.json"
    child_contract.write_text(
        json.dumps({"goal_hash": "abc123", "tasks": []}),
        encoding="utf-8",
    )
    child_state.write_text(
        json.dumps({"goal_hash": "abc123", "status": "complete"}),
        encoding="utf-8",
    )
    goal = compile_command_goal(
        "spec-fix",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature=feature,
        flags="--auto --update",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))
    child_task = next(
        task
        for task in contract["tasks"]
        if str(task["id"]).startswith("fix.child_goal.spec_check")
    )

    result = prove_goal_task(
        contract,
        state,
        str(child_task["id"]),
        {
            "child_goal_hash": "abc123",
            "child_contract_file": child_contract.as_posix(),
            "child_state_file": child_state.as_posix(),
            "child_final_status": "complete",
            "convention_domains": ["code", "design-tokens"],
            "convention_sources": [
                "$AIRESOURCES/code-conventions/general.md",
                "$AIRESOURCES/code-conventions/python.md",
                "$AIRESOURCES/design/tokens.md",
            ],
            "conventions_applied_to_output": True,
        },
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "child_contract_file_exists" in result["missing_evidence"]
    assert "child_state_file_exists" in result["missing_evidence"]


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
