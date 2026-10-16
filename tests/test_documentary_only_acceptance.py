"""Policy2 final acceptance supports nonempty inventories of reviewed ACs only."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.acceptance_review_support import add_documentary_acceptance
from tests.execution_evidence_support import FEATURE
from tests.execution_evidence_support import project as project
from tests.review_support import review_existing_project
from tests.test_acceptance_execution_join import _archive, _complete_goal
from tests.test_goal_contracts import EXPECTATIONS
from validator.acceptance_evidence import archived_policy2_evidence_errors
from validator.cli import app
from validator.evidence_policy import typed_evidence_missing
from validator.goal_contracts import (
    compile_command_goal,
    prove_goal_task,
    render_goal_contract_file,
    render_goal_state_file,
)


def _goal(project: Path, binding: bool = True):
    spec = project / ".specs/features" / FEATURE / "spec.md"
    spec.write_text("# Configuration contract\n")
    add_documentary_acceptance(project, FEATURE, "AC-001")
    documentary = add_documentary_acceptance(project, FEATURE, "AC-002")
    review_existing_project(project, FEATURE)
    skill = project / "producer/.agent-sync/skills/spec-demo"
    skill.mkdir(parents=True)
    (skill / "expectations.md").write_text(EXPECTATIONS)
    metadata = " ac-binding:reviewed-spec" if binding else ""
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
    (project / "stdout.txt").write_text("done")
    evidence = {
        "acceptance_review_receipt_path": str(documentary),
        "spec_review_receipt_path": str(spec.parent / ".reviews/spec.json"),
    }
    return (
        json.loads(render_goal_contract_file(goal)),
        json.loads(render_goal_state_file(goal)),
        evidence,
    )


@pytest.mark.parametrize("binding", [True, False])
def test_documentary_only_goal_proves_archives_and_rechecks(project, monkeypatch, binding):
    contract, state, evidence = _goal(project, binding)
    original = json.dumps(contract, sort_keys=True)
    state = _complete_goal(contract, state, evidence, project)
    archived = _archive(project, contract, state, monkeypatch)
    assert archived.exit_code == 0, archived.output
    path = json.loads(archived.output)["archived"]
    verified = CliRunner().invoke(app, ["verify-output", "spec-demo", "--run", path])
    assert verified.exit_code == 0, verified.output
    assert json.dumps(contract, sort_keys=True) == original
    assert "execution_receipt_path" not in evidence


@pytest.mark.parametrize("change", ["missing", "input", "foreign", "runtime"])
def test_documentary_only_goal_rejects_missing_stale_foreign_or_runtime(project, change):
    contract, state, evidence = _goal(project)
    if change == "missing":
        evidence.pop("acceptance_review_receipt_path")
    elif change == "input":
        (project / "migration.md").write_text("Changed review input.\n")
    elif change == "foreign":
        evidence["acceptance_review_receipt_path"] = str(project.parent / "foreign.json")
    else:
        spec = project / ".specs/features" / FEATURE / "spec.md"
        spec.write_text(spec.read_text() + "\n## AC-003\nA runtime assertion must execute.\n")
        review_existing_project(project, FEATURE)
    task = next(t for t in contract["tasks"] if t.get("acceptance_scope") == "feature")
    result = prove_goal_task(contract, state, task["id"], evidence, project_root=project)
    assert not result["accepted"]


@pytest.mark.parametrize("change", ["input", "runtime"])
def test_documentary_only_archive_rechecks_review_inputs(project, monkeypatch, change):
    contract, state, evidence = _goal(project)
    state = _complete_goal(contract, state, evidence, project)
    archived = _archive(project, contract, state, monkeypatch)
    assert archived.exit_code == 0, archived.output
    path = json.loads(archived.output)["archived"]
    if change == "input":
        (project / "migration.md").write_text("Changed review input.\n")
    else:
        spec = project / ".specs/features" / FEATURE / "spec.md"
        spec.write_text(spec.read_text() + "\n## AC-003\nA runtime assertion must execute.\n")
        review_existing_project(project, FEATURE)
    rejected = CliRunner().invoke(app, ["verify-output", "spec-demo", "--run", path])
    assert rejected.exit_code == 1, rejected.output
    if change == "runtime":
        assert "execution_receipt_path" in archived_policy2_evidence_errors(
            json.loads(Path(path).read_text()), project
        )


def test_empty_acceptance_inventory_never_passes_without_execution(project):
    spec = project / ".specs/features" / FEATURE / "spec.md"
    spec.write_text("# No acceptance declarations\n")
    missing = typed_evidence_missing(
        {
            "evidence_kind": "execution",
            "acceptance_scope": "feature",
            "expected_evidence": {"acceptance_inventory": []},
        },
        {},
        contract={"evidence_policy_version": "2", "feature": FEATURE},
        project_root=project,
    )
    assert "feature_acceptance_scope_empty" in missing
