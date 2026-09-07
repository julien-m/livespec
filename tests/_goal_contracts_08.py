"""Preserved test cases and fixtures for test_goal_contracts.py."""

from __future__ import annotations

import json
from pathlib import Path

from tests._goal_contracts_01 import _fixture_roots, _repo_root, _write_png
from tests._goal_contracts_02 import _write_complete_check_fix_scenario, _write_conventions
from validator.goal_contracts import (
    compile_command_goal,
    prove_goal_task,
    render_goal_contract_file,
    render_goal_objective,
    render_goal_state_file,
)


def test_goal_prove_rejects_missing_visual_design_fidelity_evidence(
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
    state = json.loads(render_goal_state_file(goal))

    result = prove_goal_task(
        contract,
        state,
        "visual.design_fidelity",
        evidence={
            "normalized_design_path": "penflow/expected-ui-tree.json",
            "normalized_runtime_path": "penflow/actual-ui-tree.json",
        },
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert result["state"]["tasks"]["visual.design_fidelity"]["status"] == "pending"
    assert "normalized_json_alignment_only" in result["invalid_substitutes"]
    assert any("mockup PNG" in action for action in result["required_actions"])


def test_goal_prove_rejects_legacy_visual_design_fidelity_payload(
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
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))

    result = prove_goal_task(
        contract,
        state,
        "visual.design_fidelity",
        evidence={
            "mockup_path": f".specs/design/screens/{feature}/dashboard.png",
            "baseline_path": f".specs/design/baselines/{feature}/dashboard.png",
            "comparison_report": "penflow/compare-report.json",
            "threshold_percent": 5,
            "actual_diff_percent": 3.2,
            "verdict": "PASS",
        },
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert result["state"]["tasks"]["visual.design_fidelity"]["status"] == "pending"
    assert "visual_evidence_receipt_path" in result["missing_evidence"]


def test_goal_prove_accepts_visual_design_fidelity_receipt(
    tmp_path: Path,
) -> None:

    project_root = tmp_path / "complete-project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions(project_root, tmp_path / "ai")
    feature = _write_complete_check_fix_scenario(project_root)
    receipt_path = _write_matching_visual_receipt(project_root, feature)
    goal = compile_command_goal(
        "spec-check",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature=None,
        flags="--fix --all",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))

    result = prove_goal_task(
        contract,
        state,
        "visual.design_fidelity",
        evidence={"visual_evidence_receipt_path": str(receipt_path)},
        project_root=project_root,
    )

    assert result["status"] == "ACCEPTED"
    assert result["state"]["tasks"]["visual.design_fidelity"]["status"] == "complete"


def test_goal_prove_rejects_visual_receipt_from_wrong_feature(
    tmp_path: Path,
) -> None:

    project_root = tmp_path / "complete-project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions(project_root, tmp_path / "ai")
    _write_complete_check_fix_scenario(project_root)
    other_feature = "999-other"
    receipt_path = _write_matching_visual_receipt(project_root, other_feature)
    goal = compile_command_goal(
        "spec-check",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature=None,
        flags="--fix --all",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))

    result = prove_goal_task(
        contract,
        state,
        "visual.design_fidelity",
        evidence={"visual_evidence_receipt_path": str(receipt_path)},
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert any("feature_slug_mismatch" in item for item in result["missing_evidence"])


def test_spec_check_dod_requires_tree_validation_report_not_pass(tmp_path: Path) -> None:
    (tmp_path / ".specs").mkdir()
    goal = compile_command_goal(
        "spec-check", project_root=tmp_path, livespec_root=_repo_root(), flags="--all"
    )
    dod = goal.payload["definition_of_done"]

    assert dod[0] == "Tree validation executed and reported (or skipped by --skip-tree)"
    assert not any("tree validation" in item.lower() and "passed" in item.lower() for item in dod)
    assert "Gap report produced and displayed" in dod
    assert "Gap report saved to `checks/YYYY-MM-DD.md`" in dod
    assert "Feature `changelog.md` has a check entry" in dod
    assert "Global `.specs/changelog.md` has a summary entry" in dod
    assert "If multi-spec: consolidated report produced" in dod


def test_render_goal_objective_is_stable_text_from_payload(tmp_path: Path) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    goal = compile_command_goal(
        "demo",
        project_root=project_root,
        livespec_root=livespec_root,
        feature="001-demo",
        flags="--strict",
    )

    objective = render_goal_objective(goal)

    assert objective == render_goal_objective(goal)
    assert "Goal hash:" in objective
    assert "Command: spec-demo" in objective
    assert "- `demo.txt` exists" in objective
    assert "Filesystem effects:" in objective
    assert "- creates demo.txt." in objective
    assert "- must contains: done" in objective


def test_anti_drift_block_documents_shared_goal_protocol() -> None:
    """AC-007: all imported command protocols share the same goal lifecycle."""
    text = Path("system/anti-drift-block.md").read_text(encoding="utf-8")

    assert "livespec goal render <command-name>" in text
    assert "/goal hash:<" in text  # Exact /goal slash command form with hash+ref
    assert "/goal clear" in text  # Active goal precheck
    assert "already active" in text  # Precheck documentation
    assert "contract-file:" in text
    assert "state-file:" in text
    assert "livespec goal prove" in text
    assert "[ ]` → `[x]" not in text


# ─── finalize.registry evidence family (Feature 058, FR-005/FR-006) ──────────

FINALIZE_SKILL = """\
---
name: spec-demo
description: Demo command
---

# /spec-demo

## Execution Tasks

- [always] Finalize registry via `livespec finalize apply` + `livespec finalize verify` \
and prove finalize.registry with the receipt path

## Definition of Done (Command-Level)

- [ ] Done
"""


def _finalize_fixture(tmp_path: Path) -> tuple[Path, Path]:
    """Fixture roots with the finalize execution-task skill and a .specs tree."""
    from tests.test_finalize import _make_specs_tree

    project_root, livespec_root = _fixture_roots(tmp_path)
    skill_path = livespec_root / ".agent-sync" / "skills" / "spec-demo" / "SKILL.md"
    skill_path.write_text(FINALIZE_SKILL, encoding="utf-8")
    _make_specs_tree(project_root)
    return project_root, livespec_root


def _finalize_contract_and_state(project_root: Path, livespec_root: Path) -> tuple[dict, dict]:
    goal = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
        feature="004-notifications",
        flags="",
    )
    return (
        json.loads(render_goal_contract_file(goal)),
        json.loads(render_goal_state_file(goal)),
    )


def test_finalize_registry_task_requires_receipt_path(tmp_path: Path) -> None:
    """AC-007: the finalize execution-task line must compile to the
    finalize.registry task whose only accepted evidence is the receipt path."""
    project_root, livespec_root = _finalize_fixture(tmp_path)
    contract, _state = _finalize_contract_and_state(project_root, livespec_root)
    task = next(task for task in contract["tasks"] if task["id"] == "finalize.registry")
    assert "finalize_receipt_path" in task["required_evidence"]
    assert "prose_finalization_claim" in task["invalid_substitutes"]
    assert any("livespec finalize apply" in action for action in task["repair_if_missing"])


def test_goal_prove_rejects_prose_finalization_claim(tmp_path: Path) -> None:
    """AC-008: prose claims without a receipt are invalid substitutes."""
    project_root, livespec_root = _finalize_fixture(tmp_path)
    contract, state = _finalize_contract_and_state(project_root, livespec_root)
    result = prove_goal_task(
        contract,
        state,
        "finalize.registry",
        evidence={"output": "All registry files were updated", "success_criteria_met": True},
        project_root=project_root,
    )
    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "finalize_receipt_path" in result["missing_evidence"]
    assert "prose_finalization_claim" in result["invalid_substitutes"]
    assert result["state"]["tasks"]["finalize.registry"]["status"] == "pending"


def test_goal_prove_rejects_exit_code_and_file_list_substitutes(tmp_path: Path) -> None:
    """AC-008: exit codes and declared file lists are not finalization proof."""
    project_root, livespec_root = _finalize_fixture(tmp_path)
    contract, state = _finalize_contract_and_state(project_root, livespec_root)
    result = prove_goal_task(
        contract,
        state,
        "finalize.registry",
        evidence={"exit_code": 0, "files": [".specs/README.md", ".specs/changelog.md"]},
        project_root=project_root,
    )
    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "exit_code_without_receipt" in result["invalid_substitutes"]
    assert "declared_file_list_without_receipt" in result["invalid_substitutes"]


def _write_matching_visual_receipt(project_root: Path, feature: str) -> Path:
    from validator.visual_evidence import compare_visual_images, write_visual_receipt

    mockup = project_root / ".specs" / "design" / "screens" / feature / "dashboard.png"
    runtime = (
        project_root / ".specs" / "features" / feature / "run" / "manual" / "web" / "dashboard.png"
    )
    _write_png(mockup, (10, 20, 30))
    _write_png(runtime, (10, 20, 30))
    comparison = compare_visual_images(
        project_root=project_root,
        feature_slug=feature,
        screen="dashboard",
        target="web",
        comparison_kind="mockup_runtime",
        reference_path=mockup,
        actual_path=runtime,
        threshold_percent=5.0,
        diff_path=(
            project_root
            / ".specs"
            / "features"
            / feature
            / "run"
            / "manual"
            / "visual-evidence"
            / "dashboard.diff.png"
        ),
    )
    receipt_path = write_visual_receipt(
        project_root=project_root,
        feature_slug=feature,
        command="spec-check",
        target="web",
        run_id="manual",
        comparisons=[comparison],
        output_dir=(
            project_root / ".specs" / "features" / feature / "run" / "manual" / "visual-evidence"
        ),
    )
    return receipt_path
