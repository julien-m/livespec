"""A pre-spec coordinator closes only with current reviewed and executed acceptance."""

# @spec(FR-009)
# @spec(AC-007)
# @spec(AC-015)

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.acceptance_review_support import add_documentary_acceptance
from tests.execution_evidence_support import FEATURE, _review_response, run
from tests.execution_evidence_support import project as project
from tests.review_support import review_existing_project
from tests.test_acceptance_execution_join import _archive, _complete_goal
from tests.test_goal_contracts import EXPECTATIONS
from validator.cli import app
from validator.execution_mapping import ingest_mapping_review, prepare_mapping_review
from validator.goal_contracts import (
    compile_command_goal,
    prove_goal_task,
    render_goal_contract_file,
    render_goal_state_file,
)


def _compile_before_spec(project: Path, metadata: str = " ac-binding:reviewed-spec"):
    spec = project / ".specs/features" / FEATURE / "spec.md"
    text = spec.read_text()
    spec.unlink()
    skill = project / "producer/.agent-sync/skills/spec-demo"
    skill.mkdir(parents=True)
    (skill / "expectations.md").write_text(EXPECTATIONS)
    (skill / "SKILL.md").write_text(
        "# /spec-demo\n## Execution Tasks\n"
        f"- [always] Verify acceptance <!-- evidence:execution ac-scope:feature{metadata} -->\n"
        "## Definition of Done (Command-Level)\n"
        "- [ ] Output prepared <!-- evidence:documentary -->\n"
    )
    goal = compile_command_goal(
        "spec-demo",
        project_root=project,
        livespec_root=project / "producer",
        feature=FEATURE,
        flags="--model=reviewer/v1",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))
    spec.write_text(text)
    return contract, state


def _evidence(project: Path):
    documentary = add_documentary_acceptance(project, FEATURE)
    review_existing_project(project, FEATURE)
    prepared = prepare_mapping_review(project, FEATURE, project / "mapping.json")
    assert ingest_mapping_review(
        prepared, [_review_response(prepared)], project / "acceptance-review.json"
    ).ready
    (project / "stdout.txt").write_text("done")
    return {
        "execution_receipt_path": str(run(project)),
        "acceptance_review_receipt_path": str(documentary),
        "spec_review_receipt_path": str(
            project / ".specs/features" / FEATURE / ".reviews/spec.json"
        ),
    }


def test_pre_spec_contract_proves_archives_and_rechecks_all_later_acceptance(project, monkeypatch):
    contract, state = _compile_before_spec(project)
    original = json.dumps(contract, sort_keys=True)
    evidence = _evidence(project)
    state = _complete_goal(contract, state, evidence, project)
    archived = _archive(project, contract, state, monkeypatch)
    assert archived.exit_code == 0, archived.output
    path = json.loads(archived.output)["archived"]
    verified = CliRunner().invoke(app, ["verify-output", "spec-demo", "--run", path])
    assert verified.exit_code == 0, verified.output
    assert json.dumps(contract, sort_keys=True) == original
    assert json.loads(Path(path).read_text())["goal_hash"] == contract["goal_hash"]
    Path(evidence["spec_review_receipt_path"]).unlink()
    rejected = CliRunner().invoke(app, ["verify-output", "spec-demo", "--run", path])
    assert rejected.exit_code == 1, rejected.output


@pytest.mark.parametrize("change", ["missing", "forged", "plan", "foreign", "stale", "documentary"])
def test_current_spec_review_and_documentary_conjunction_cannot_be_bypassed(project, change):
    contract, state = _compile_before_spec(project)
    evidence = _evidence(project)
    review = Path(evidence["spec_review_receipt_path"])
    if change == "missing":
        evidence.pop("spec_review_receipt_path")
    elif change == "forged":
        review.write_text('{"complete":true,"ready":true}')
    elif change == "plan":
        evidence["spec_review_receipt_path"] = str(review.with_name("plan.json"))
    elif change == "foreign":
        evidence["spec_review_receipt_path"] = str(project.parent / "foreign.json")
    elif change == "documentary":
        evidence.pop("acceptance_review_receipt_path")
    else:
        spec = project / ".specs/features" / FEATURE / "spec.md"
        spec.write_text(spec.read_text() + "\n## AC-003\nAdding zero preserves its argument.\n")
    task = next(t for t in contract["tasks"] if t.get("acceptance_scope") == "feature")
    result = prove_goal_task(contract, state, task["id"], evidence, project_root=project)
    assert not result["accepted"]
    assert result["state"]["tasks"][task["id"]]["status"] == "pending"


def test_fresh_review_cannot_certify_new_unexecuted_criterion(project):
    contract, state = _compile_before_spec(project)
    evidence = _evidence(project)
    spec = project / ".specs/features" / FEATURE / "spec.md"
    spec.write_text(spec.read_text() + "\n## AC-003\nAdding zero preserves its argument.\n")
    review_existing_project(project, FEATURE)
    task = next(t for t in contract["tasks"] if t.get("acceptance_scope") == "feature")
    result = prove_goal_task(contract, state, task["id"], evidence, project_root=project)
    assert not result["accepted"]
    assert "spec_review_incomplete_or_stale" not in str(result)


def test_old_frozen_empty_inventory_keeps_its_original_meaning(project):
    contract, state = _compile_before_spec(project, metadata="")
    evidence = _evidence(project)
    task = next(t for t in contract["tasks"] if t.get("acceptance_scope") == "feature")
    result = prove_goal_task(contract, state, task["id"], evidence, project_root=project)
    assert not result["accepted"]
    assert "acceptance_declarations_changed_recompile_required" in str(result)


@pytest.mark.parametrize(
    "metadata", [" ac-binding:unknown", " outcome:red ac-binding:reviewed-spec"]
)
def test_invalid_coordinator_binding_is_rejected_during_compilation(project, metadata):
    with pytest.raises(ValueError, match=r"acceptance|reviewed_spec"):
        _compile_before_spec(project, metadata)


def test_production_coordinator_declares_reviewed_spec_before_feature_exists(tmp_path):
    root = Path(__file__).resolve().parents[1]
    (tmp_path / ".specs/features").mkdir(parents=True)
    goal = compile_command_goal(
        "spec-feature",
        project_root=tmp_path,
        livespec_root=root,
        feature="001-later",
        flags="--auto --model=reviewer/v1",
    )
    final = [t for t in goal.payload["tasks"] if t.get("acceptance_scope") == "feature"]
    assert final and all(t.get("acceptance_binding") == "reviewed-spec" for t in final)
    assert all("spec_review_receipt_path" in t["required_evidence"] for t in final)
    assert all("acceptance_inventory" not in t["expected_evidence"] for t in final)
