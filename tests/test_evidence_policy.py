"""Current proof purposes cannot be replaced by documentary success assertions."""

import json
from pathlib import Path

import pytest

from validator.evidence_policy import typed_evidence_missing
from validator.goal_contracts import (
    compile_command_goal,
    prove_goal_task,
    render_goal_contract_file,
    render_goal_state_file,
)
from validator.normative_identity import normative_hash


def test_current_execution_rejects_prose_but_old_contract_keeps_original_meaning(tmp_path):
    task = {"evidence_kind": "execution"}
    evidence = {"output": "All tests passed", "success_criteria_met": True}
    assert typed_evidence_missing(
        task, evidence, contract={"evidence_policy_version": "1"}, project_root=tmp_path
    ) == ["execution_receipt_path"]
    assert typed_evidence_missing(task, evidence, contract={}, project_root=tmp_path) == []
    assert typed_evidence_missing(
        task, evidence, contract={"evidence_policy_version": "999"}, project_root=tmp_path
    ) == ["unknown_evidence_policy_version"]


def test_compiled_inventory_explicit_kind_and_scope():
    root = Path(__file__).parents[1]
    goal = compile_command_goal(
        "spec-test",
        project_root=root,
        livespec_root=root,
        feature="078-requirement-evidence-integrity",
        flags="--model=gpt-6-astra",
    )
    tasks = goal.payload["tasks"]
    assert goal.payload["evidence_policy_version"] == "2"
    assert all(t["evidence_kind"] in {"documentary", "review", "execution"} for t in tasks)
    execution = [t for t in tasks if t["evidence_kind"] == "execution"]
    assert execution
    assert all(
        t["expected_evidence"]["feature_slug"] == "078-requirement-evidence-integrity"
        for t in execution
    )
    assert all("execution_receipt_path" in t["required_evidence"] for t in execution)
    assert all("success_criteria_met" not in t["required_evidence"] for t in execution)


def test_serialized_goal_enforces_canonical_policy_even_without_optional_mirror():
    root = Path(__file__).parents[1]
    goal = compile_command_goal(
        "spec-test",
        project_root=root,
        livespec_root=root,
        feature="078-requirement-evidence-integrity",
    )
    contract = json.loads(render_goal_contract_file(goal))
    assert contract["evidence_policy_version"] == "2"
    task = next(t for t in contract["tasks"] if t["evidence_kind"] == "execution")
    for remove_mirror in (False, True):
        if remove_mirror:
            del contract["evidence_policy_version"]
        result = prove_goal_task(
            contract,
            json.loads(render_goal_state_file(goal)),
            task["id"],
            {"output": "All tests passed", "success_criteria_met": True},
            project_root=root,
        )
        assert not result["accepted"]
        assert "execution_receipt_path" in result["missing_evidence"]


@pytest.mark.parametrize(
    "field", ["evidence_policy_version", "tasks", "normalized_flags", "feature"]
)
def test_current_contract_mirrors_cannot_weaken_canonical_proof(field):
    root = Path(__file__).parents[1]
    goal = compile_command_goal(
        "spec-test",
        project_root=root,
        livespec_root=root,
        feature="078-requirement-evidence-integrity",
    )
    contract = json.loads(render_goal_contract_file(goal))
    task = next(t for t in contract["tasks"] if t["evidence_kind"] == "execution")
    if field == "tasks":
        task["evidence_kind"] = "documentary"
    else:
        contract[field] = "legacy" if field != "normalized_flags" else ["--model=forged"]
    result = prove_goal_task(
        contract,
        json.loads(render_goal_state_file(goal)),
        task["id"],
        {"output": "done", "success_criteria_met": True},
        project_root=root,
    )
    assert not result["accepted"]
    assert result["missing_evidence"] == [f"current_contract_mirror_mismatch:{field}"]


def test_lifecycle_identity_rejects_malformed_or_business_metadata():
    def identity(text):
        return normative_hash(text, lifecycle_document=True)

    assert identity("---\nstatus: Approved\nupdated: 2026-09-06\n---\nFR-001 purge\n") == identity(
        "---\nstatus: Implemented\nupdated: 2026-09-07\n---\nFR-001 purge\n"
    )
    for before, after in [
        ("---\nFR-001 purge\nstatus: disabled", "---\nFR-001 purge\nstatus: enabled"),
        ("---\nstatus: {retention: 24}\n---", "---\nstatus: {retention: 48}\n---"),
        (
            "---\nstatus: Approved\nstatus: Draft\n---",
            "---\nstatus: Approved\nstatus: Implemented\n---",
        ),
        ("# Rules\nstatus: Approved", "# Rules\nstatus: Implemented"),
        (
            "## Header\n- **Status:** Approved\n- **Status:** Draft",
            "## Header\n- **Status:** Approved\n- **Status:** Implemented",
        ),
        ("---\ncreated: 2026-09-06\n---", "---\ncreated: 2026-09-07\n---"),
    ]:
        assert identity(before) != identity(after)


def test_explicit_inapplicable_tdd_cannot_be_reused_after_behavioral_ac_added(tmp_path):
    from validator.evidence_policy import apply_evidence_policy

    feature = tmp_path / ".specs/features/001-test"
    feature.mkdir(parents=True)
    spec = feature / "spec.md"
    spec.write_text("# Feature\nFR-001 Export\n")
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        "- [always] Run RED <!-- evidence:execution applicable:behavioral-ac outcome:red -->\n"
    )
    task = {
        "id": "task.red",
        "description": "Run RED",
        "required_evidence": ["observable_output_or_artifact", "success_criteria_met"],
    }
    apply_evidence_policy([task], skill, project_root=tmp_path, feature="001-test")
    assert task["evidence_kind"] == "documentary"
    contract = {"evidence_policy_version": "1", "feature": "001-test"}
    assert typed_evidence_missing(task, {}, contract=contract, project_root=tmp_path) == []
    spec.write_text("# Feature\n## Behavioral AC\nSubmission does not duplicate requests.\n")
    assert typed_evidence_missing(task, {}, contract=contract, project_root=tmp_path) == [
        "task_applicability_changed_recompile_required"
    ]
    apply_evidence_policy([task], skill, project_root=tmp_path, feature="001-test")
    assert task["evidence_kind"] == "execution" and task["evidence_expected_outcome"] == "red"
    assert typed_evidence_missing(
        task,
        {"output": "RED observed", "success_criteria_met": True},
        contract=contract,
        project_root=tmp_path,
    ) == ["execution_receipt_path"]


def test_nonvisual_plan_review_does_not_require_conditional_penflow_artifact():
    root = Path(__file__).parents[1]
    goal = compile_command_goal(
        "spec-feature",
        project_root=root,
        livespec_root=root,
        feature="078-requirement-evidence-integrity",
    )
    matching = [task for task in goal.payload["tasks"] if "--review-result" in task["description"]]
    assert matching
    for task in matching:
        assert "penflow_artifact_path_exists" not in task["required_evidence"]
        assert task["evidence_kind"] == "review"
