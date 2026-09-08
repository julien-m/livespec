"""Preserved test cases and fixtures for test_goal_contracts.py."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests._goal_contracts_01 import _fixture_roots, _repo_root
from validator.goal_contracts import (
    compile_command_goal,
    prove_goal_task,
    render_goal_contract_file,
    render_goal_state_file,
)


def test_compile_command_goal_embeds_non_empty_before_hook_context(
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
integration: qe-analysis
commands: [plan]
phase: before
mode: extend
order: 60
---
# QE Analysis

Apply the QE analysis protocol before planning tests.
""",
        encoding="utf-8",
    )
    monkeypatch.setattr("validator.integrations.INTEGRATIONS_DIR", integrations_dir)

    goal = compile_command_goal(
        "spec-plan",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))

    before_hook = contract["hooks"]["before"]
    assert before_hook["non_empty"] is True
    assert "qe-analysis" in goal.canonical_json
    assert "# QE Analysis" in before_hook["context"]
    assert contract["tasks"][0]["id"] == "hooks.before"
    assert "resolved_hook_context_sha256" in contract["tasks"][0]["required_evidence"]
    assert "Hook context to apply:" in goal.objective


def test_goal_prove_requires_resolved_before_hook_context(tmp_path: Path) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    contract, state = _historical_hook_pair(project_root, livespec_root)

    rejected = prove_goal_task(
        contract,
        state,
        "hooks.before",
        evidence={
            "config_file_exists": True,
            "summary": "qe-analysis configured",
        },
        project_root=project_root,
    )

    assert rejected["status"] == "REJECTED_NEEDS_ACTION"
    assert "hook_resolution_command" in rejected["missing_evidence"]
    assert "resolved_hook_context_sha256" in rejected["missing_evidence"]
    assert "hook_context_applied" in rejected["missing_evidence"]
    assert "config_file_exists_without_resolved_context" in rejected["invalid_substitutes"]

    accepted = prove_goal_task(
        contract,
        state,
        "hooks.before",
        evidence={
            "hook_resolution_command": "livespec hooks resolve --event before --command demo",
            "resolved_hook_context_sha256": "abc123",
            "hook_context_applied": True,
        },
        project_root=project_root,
    )

    assert accepted["status"] == "ACCEPTED"


@pytest.mark.parametrize("malformation", ["contract_tasks", "contract_task"])
def test_non_init_proof_preserves_unknown_task_for_malformed_contract_tasks(
    tmp_path: Path, malformation: str
) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    goal = compile_command_goal("spec-demo", project_root=project_root, livespec_root=livespec_root)
    contract = json.loads(render_goal_contract_file(goal))
    # This fixture exercises the preserved historical validator contract.
    contract.pop("evidence_policy_version", None)
    contract["canonical"].pop("evidence_policy_version", None)
    contract["canonical_json"] = json.dumps(contract["canonical"])
    state = json.loads(render_goal_state_file(goal))
    task_id = contract["tasks"][0]["id"]
    if malformation == "contract_tasks":
        contract["tasks"] = "invalid"
    else:
        contract["tasks"] = ["invalid"]

    result = prove_goal_task(contract, state, task_id, {"output": "done"})

    assert result["status"] == "REJECTED_UNKNOWN_TASK"
    assert result["state"] == state


@pytest.mark.parametrize("malformation", ["state_tasks", "state_task", "attempts"])
def test_non_init_proof_rejects_present_malformed_state_shapes(
    tmp_path: Path, malformation: str
) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    goal = compile_command_goal("spec-demo", project_root=project_root, livespec_root=livespec_root)
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))
    task_id = contract["tasks"][0]["id"]
    if malformation == "state_tasks":
        state["tasks"] = []
    elif malformation == "state_task":
        state["tasks"][task_id] = []
    else:
        state["tasks"][task_id]["attempts"] = {}

    with pytest.raises(TypeError):
        prove_goal_task(contract, state, task_id, {"output": "done"})


@pytest.mark.parametrize("missing_field", ["ordinal", "description"])
def test_non_init_proof_preserves_missing_task_field_key_error(
    tmp_path: Path, missing_field: str
) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    goal = compile_command_goal("spec-demo", project_root=project_root, livespec_root=livespec_root)
    contract = json.loads(render_goal_contract_file(goal))
    # This fixture exercises the preserved historical validator contract.
    contract.pop("evidence_policy_version", None)
    contract["canonical"].pop("evidence_policy_version", None)
    contract["canonical_json"] = json.dumps(contract["canonical"])
    state = json.loads(render_goal_state_file(goal))
    task = contract["tasks"][0]
    task_id = task["id"]
    del task[missing_field]

    with pytest.raises(KeyError) as error:
        prove_goal_task(contract, state, task_id, {"output": "done"})

    assert error.value.args == (missing_field,)


# @spec FR-002: Native QE render, FR-006: No user config/global skill dependency
#   — .specs/features/071-qe-analysis-native-module/spec.md#fr-002
def test_spec_plan_goal_embeds_native_qe_without_user_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    monkeypatch.setattr("validator.integrations.INTEGRATIONS_DIR", tmp_path / "missing-l0")
    monkeypatch.setattr("validator.hook_resolver.GLOBAL_HOOKS_DIR", tmp_path / "missing-global")

    goal = compile_command_goal(
        "spec-plan",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature="001-demo",
        flags="",
    )
    contract = json.loads(render_goal_contract_file(goal))

    qe_context = contract["qe_analysis"]
    assert qe_context["native"] is True
    assert qe_context["source_path"] == "system/qe-analysis.md"
    assert qe_context["user_hooks_role"] == "extension_only"
    assert "Quality Engineering" in qe_context["content"]
    assert "~/.config/livespec/qe-analysis.md" not in qe_context["content"]
    assert "$qe-analysis" not in qe_context["content"]

    qe_task = next(task for task in contract["tasks"] if task["id"] == "qe.analysis")
    assert qe_task["required_evidence"] == [
        "qe_dimensions_considered",
        "qe_gates_required",
        "qe_expected_evidence",
        "qe_gaps_or_missing_evidence",
        "qe_boundary_note",
    ]
    assert "Native QE Analysis:" in goal.objective


# @spec FR-003: Affected commands receive qe.analysis
#   — .specs/features/071-qe-analysis-native-module/spec.md#fr-003
@pytest.mark.parametrize("command", ["spec-specify", "spec-plan", "spec-test"])
def test_native_qe_analysis_task_is_injected_for_quality_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command: str,
) -> None:
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    monkeypatch.setattr("validator.integrations.INTEGRATIONS_DIR", tmp_path / "missing-l0")
    monkeypatch.setattr("validator.hook_resolver.GLOBAL_HOOKS_DIR", tmp_path / "missing-global")

    goal = compile_command_goal(
        command,
        project_root=project_root,
        livespec_root=_repo_root(),
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))

    task_ids = [task["id"] for task in contract["tasks"]]
    assert "qe.analysis" in task_ids
    assert task_ids.index("qe.analysis") < task_ids.index("archive.run")


# @spec FR-003: Unaffected commands do not receive qe.analysis
#   — .specs/features/071-qe-analysis-native-module/spec.md#fr-003
def test_native_qe_analysis_task_is_not_injected_for_unaffected_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    monkeypatch.setattr("validator.integrations.INTEGRATIONS_DIR", tmp_path / "missing-l0")
    monkeypatch.setattr("validator.hook_resolver.GLOBAL_HOOKS_DIR", tmp_path / "missing-global")

    goal = compile_command_goal(
        "spec-check",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))

    assert "qe_analysis" not in contract
    assert "qe.analysis" not in [task["id"] for task in contract["tasks"]]


# @spec FR-005: Generic QE proof is rejected
#   — .specs/features/071-qe-analysis-native-module/spec.md#fr-005
def test_goal_prove_rejects_generic_qe_analysis_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    monkeypatch.setattr("validator.integrations.INTEGRATIONS_DIR", tmp_path / "missing-l0")
    monkeypatch.setattr("validator.hook_resolver.GLOBAL_HOOKS_DIR", tmp_path / "missing-global")
    goal = compile_command_goal(
        "spec-plan",
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
            "output": "quality checked",
            "success_criteria_met": True,
            "summary": "QE looks good",
        },
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert result["missing_evidence"] == [
        "qe_dimensions_considered",
        "qe_gates_required",
        "qe_expected_evidence",
        "qe_gaps_or_missing_evidence",
        "qe_boundary_note",
    ]
    assert "generic_quality_claim" in result["invalid_substitutes"]


# @spec FR-006: Skill/config substitutes are rejected
#   — .specs/features/071-qe-analysis-native-module/spec.md#fr-006
@pytest.mark.parametrize(
    ("extra_evidence", "invalid_substitute"),
    [
        ({"skill": "qe-analysis"}, "skill_global_qe_analysis_invocation"),
        ({"qe_analysis_skill_invoked": True}, "skill_global_qe_analysis_invocation"),
        ({"config_path": "~/.config/livespec/qe-analysis.md"}, "user_config_qe_analysis_only"),
        ({"user_config_qe_analysis": True}, "user_config_qe_analysis_only"),
    ],
)
def test_goal_prove_rejects_qe_analysis_substitutes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    extra_evidence: dict[str, object],
    invalid_substitute: str,
) -> None:
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    monkeypatch.setattr("validator.integrations.INTEGRATIONS_DIR", tmp_path / "missing-l0")
    monkeypatch.setattr("validator.hook_resolver.GLOBAL_HOOKS_DIR", tmp_path / "missing-global")
    goal = compile_command_goal(
        "spec-plan",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))

    evidence: dict[str, object] = {
        "qe_dimensions_considered": ["functional_correctness"],
        "qe_gates_required": ["AC coverage matrix maps every AC to test evidence"],
        "qe_expected_evidence": ["test command transcript with pass/fail counts"],
        "qe_gaps_or_missing_evidence": ["no visual proof required for CLI-only change"],
        "qe_boundary_note": "Review/audit owns defect hunting; tests own evidence sufficiency.",
        **extra_evidence,
    }
    result = prove_goal_task(
        contract,
        state,
        "qe.analysis",
        evidence=evidence,
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert result["missing_evidence"] == []
    assert invalid_substitute in result["invalid_substitutes"]


def _historical_hook_pair(
    project_root: Path, livespec_root: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    goal = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
    )
    hook_task = {
        "id": "hooks.before",
        "ordinal": 1,
        "category": "injected",
        "description": "Resolve hooks",
        "required_evidence": [
            "hook_resolution_command",
            "resolved_hook_context_sha256",
            "hook_context_applied",
        ],
        "invalid_substitutes": [
            "manual_integration_summary",
            "config_file_exists_without_resolved_context",
        ],
        "repair_if_missing": ["run hooks resolve"],
        "completion_actor": "goal",
        "expected_evidence": {
            "hook_resolution_command": "livespec hooks resolve --event before --command demo",
            "resolved_hook_context_sha256": "abc123",
        },
    }
    contract = json.loads(render_goal_contract_file(goal))
    # This fixture exercises the preserved historical validator contract.
    contract.pop("evidence_policy_version", None)
    contract["canonical"].pop("evidence_policy_version", None)
    contract["canonical_json"] = json.dumps(contract["canonical"])
    contract["tasks"].insert(0, hook_task)
    state = json.loads(render_goal_state_file(goal))
    state["tasks"]["hooks.before"] = {
        "ordinal": 1,
        "description": "Resolve hooks",
        "status": "pending",
        "attempts": [],
        "accepted_evidence": None,
        "last_rejection": None,
    }

    return contract, state
