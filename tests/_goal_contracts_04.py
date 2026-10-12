"""Preserved test cases and fixtures for test_goal_contracts.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests._goal_contracts_01 import _fixture_roots, _repo_root, _write_execution_task_skill
from tests._goal_contracts_02 import (
    _write_conventions,
    _write_conventions_gates,
    _write_fail_conventions_receipt,
)
from validator.goal_contracts import (
    compile_command_goal,
    prove_goal_task,
    render_goal_contract_file,
    render_goal_state_file,
)


# @spec FR-004: Structured QE proof is accepted
#   — .specs/features/071-qe-analysis-native-module/spec.md#fr-004
def test_goal_prove_accepts_structured_qe_analysis_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    monkeypatch.setattr("validator.integrations.INTEGRATIONS_DIR", tmp_path / "missing-l0")
    monkeypatch.setattr("validator.hook_resolver.GLOBAL_HOOKS_DIR", tmp_path / "missing-global")
    goal = compile_command_goal(
        "spec-test",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))

    result = prove_goal_task(
        contract,
        state,
        "qe.analysis",
        evidence={
            "qe_dimensions_considered": [
                "functional_correctness",
                "regression_risk",
                "api_contract_compatibility",
            ],
            "qe_gates_required": [
                "AC coverage matrix maps every AC to test evidence",
                "resolved test commands exit 0",
            ],
            "qe_expected_evidence": [
                "checks/YYYY-MM-DD-test.md coverage report",
                "test command transcript with pass/fail counts",
            ],
            "qe_gaps_or_missing_evidence": [
                "visual proof not applicable for non-UI feature",
            ],
            "qe_boundary_note": (
                "Defect hunting remains in review/audit; spec-test owns test evidence."
            ),
        },
        project_root=project_root,
    )

    assert result["status"] == "ACCEPTED"
    assert result["state"]["tasks"]["qe.analysis"]["status"] == "complete"


# @spec FR-007: User hooks remain extension-only
#   — .specs/features/071-qe-analysis-native-module/spec.md#fr-007
def test_native_qe_is_primary_and_user_hooks_are_additive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    integrations_dir = tmp_path / "integrations"
    integrations_dir.mkdir()
    (integrations_dir / "qe-analysis.md").write_text(
        """\
---
integration: personal-qe
commands: [plan]
phase: before
mode: extend
order: 60
---
Personal QE addendum only.
""",
        encoding="utf-8",
    )
    monkeypatch.setattr("validator.integrations.INTEGRATIONS_DIR", integrations_dir)
    monkeypatch.setattr("validator.hook_resolver.GLOBAL_HOOKS_DIR", tmp_path / "missing-global")

    goal = compile_command_goal(
        "spec-plan",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))

    assert contract["qe_analysis"]["native"] is True
    assert contract["qe_analysis"]["source_path"] == "system/qe-analysis.md"
    assert contract["hooks"]["before"]["non_empty"] is True
    assert "Personal QE addendum only." in contract["hooks"]["before"]["context"]
    assert "qe.analysis" in [task["id"] for task in contract["tasks"]]


# @spec FR-006: No per-task convention proofs
#   — .specs/features/081-lightweight-outcome-goals/spec.md#fr-006
def test_rendered_goal_tasks_carry_no_per_task_convention_proofs(tmp_path: Path) -> None:
    """081 AC-006: conventions are gated once, never replayed task by task."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_conventions(project_root, tmp_path / "ai")
    _write_execution_task_skill(livespec_root)

    goal = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
        feature="001-demo",
        flags=[],
    )
    contract = json.loads(render_goal_contract_file(goal))

    assert "conventions" not in goal.payload
    for task in contract["tasks"]:
        assert "required_conventions" not in task
        assert not {
            "convention_domains_recorded",
            "convention_sources_read",
            "conventions_applied_to_output",
        } & set(task["required_evidence"])
    assert "Task-level convention replay:" not in goal.objective
    assert "Always task" in contract["checklist"]


def test_goal_prove_rejects_checklist_rows_as_unknown_tasks(tmp_path: Path) -> None:
    """081 AC-001: indicative checklist rows are not proof obligations."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_conventions(project_root, tmp_path / "ai")
    _write_execution_task_skill(livespec_root)
    goal = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))

    assert [task["id"] for task in contract["tasks"]] == ["outcome.verified", "archive.run"]
    result = prove_goal_task(
        contract,
        state,
        "task.001.always_task",
        evidence={"output": "done", "success_criteria_met": True},
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_UNKNOWN_TASK"


@pytest.mark.real_stop_condition
def test_goal_prove_outcome_accepts_passing_stop_condition(tmp_path: Path) -> None:
    """081 AC-002: the goal runs the stop condition; an existing artifact covers a silent check."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_execution_task_skill(livespec_root)
    (project_root / ".specs" / "features" / "001-demo").mkdir(parents=True)
    (project_root / "demo.txt").write_text("done\n", encoding="utf-8")
    goal = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))

    result = prove_goal_task(
        contract,
        state,
        "outcome.verified",
        evidence={"output": "validated"},
        project_root=project_root,
    )
    assert result["missing_evidence"] == ["observable_output_or_artifact"]

    result = prove_goal_task(
        contract,
        result["state"],
        "outcome.verified",
        evidence={"artifact": "demo.txt"},
        project_root=project_root,
    )

    assert result["status"] == "ACCEPTED"
    assert result["observed"]["exit_code"] == 0
    assert result["state"]["tasks"]["outcome.verified"]["status"] == "complete"


@pytest.mark.real_stop_condition
def test_goal_prove_outcome_rejects_missing_feature_target(tmp_path: Path) -> None:
    """A feature that was never created cannot be certified by an unrelated artifact."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_execution_task_skill(livespec_root)
    (project_root / "demo.txt").write_text("stale\n", encoding="utf-8")
    goal = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))

    result = prove_goal_task(
        contract,
        state,
        "outcome.verified",
        evidence={"artifact": "demo.txt"},
        project_root=project_root,
    )

    assert result["status"] != "ACCEPTED"
    assert result["state"]["tasks"]["outcome.verified"]["status"] != "complete"


def test_conventions_gate_not_required_for_unlisted_command(tmp_path: Path) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_conventions(project_root, tmp_path / "ai")
    _write_conventions_gates(project_root)
    _write_execution_task_skill(livespec_root)

    goal = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))
    final_tasks = [task for task in contract["tasks"] if task["id"] != "archive.run"]

    assert final_tasks
    assert all("conventions_receipt_path" not in task["required_evidence"] for task in final_tasks)


def test_conventions_gate_not_required_for_spec_plan(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions_gates(project_root)

    goal = compile_command_goal(
        "spec-plan",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))
    final_tasks = [task for task in contract["tasks"] if task["id"] != "archive.run"]

    assert final_tasks
    assert all("conventions_receipt_path" not in task["required_evidence"] for task in final_tasks)


def test_spec_feature_gates_conventions_once_at_feature_scope(
    tmp_path: Path,
) -> None:
    """081 AC-006: the supervisor gets one end-of-run gate, matching its expectations."""
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions(project_root, tmp_path / "ai")
    _write_conventions_gates(project_root)

    goal = compile_command_goal(
        "spec-feature",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))
    supervisor_tasks = [
        task for task in contract["tasks"] if task["id"] not in {"archive.run", "hooks.before"}
    ]

    gated = [
        task["id"]
        for task in supervisor_tasks
        if "conventions_receipt_path" in task["required_evidence"]
    ]
    assert gated == ["conventions.gate"]
    assert all(
        "convention_sources_read" not in task["required_evidence"] for task in supervisor_tasks
    )


def test_conventions_gate_required_for_spec_implement(tmp_path: Path) -> None:
    """081 AC-006: one feature-scope conventions receipt task replaces per-task receipts."""
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions_gates(project_root)

    goal = compile_command_goal(
        "spec-implement",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))
    gated = [
        task["id"]
        for task in contract["tasks"]
        if "conventions_receipt_path" in task["required_evidence"]
    ]

    assert gated == ["conventions.gate"]
    ids = [task["id"] for task in contract["tasks"]]
    assert ids[-3:] == ["conventions.gate", "outcome.verified", "archive.run"]


def test_goal_prove_rejects_non_pass_conventions_receipt(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".specs").mkdir()
    _write_conventions(project_root, tmp_path / "ai")
    receipt = _write_fail_conventions_receipt(project_root)
    goal = compile_command_goal(
        "spec-implement",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))
    task_id = next(
        task["id"]
        for task in contract["tasks"]
        if "conventions_receipt_path" in task["required_evidence"]
    )

    result = prove_goal_task(
        contract,
        state,
        task_id,
        evidence={
            "output": "done",
            "success_criteria_met": True,
            "convention_domains": ["code"],
            "convention_sources": [
                "$AIRESOURCES/code-conventions/general.md",
                "$AIRESOURCES/code-conventions/python.md",
            ],
            "conventions_applied_to_output": True,
            "conventions_receipt_path": receipt.relative_to(project_root).as_posix(),
        },
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "conventions_receipt_verdict_pass" in result["missing_evidence"]


def test_goal_prove_rejects_conventions_receipt_outside_project(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".specs").mkdir()
    _write_conventions(project_root, tmp_path / "ai")
    _write_conventions_gates(project_root)
    outside = tmp_path / "outside-receipt.json"
    outside.write_text("{}", encoding="utf-8")
    goal = compile_command_goal(
        "spec-implement",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))
    task_id = next(
        task["id"]
        for task in contract["tasks"]
        if "conventions_receipt_path" in task["required_evidence"]
    )

    result = prove_goal_task(
        contract,
        state,
        task_id,
        evidence={
            "output": "done",
            "success_criteria_met": True,
            "convention_domains": ["code"],
            "convention_sources": [
                "$AIRESOURCES/code-conventions/general.md",
                "$AIRESOURCES/code-conventions/python.md",
            ],
            "conventions_applied_to_output": True,
            "conventions_receipt_path": outside.as_posix(),
        },
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert any(
        item.startswith("conventions_receipt_valid:path_outside_project")
        for item in result["missing_evidence"]
    )
