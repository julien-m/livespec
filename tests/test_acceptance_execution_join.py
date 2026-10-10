"""Real pytest captures and independent documentary review remain conjunctive at every boundary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from tests.acceptance_review_support import add_documentary_acceptance
from tests.execution_evidence_support import AC, FEATURE, _review_response, run
from tests.execution_evidence_support import project as project
from tests.test_goal_contracts import EXPECTATIONS
from validator.cli import app
from validator.execution_evidence import verify_execution_receipt
from validator.execution_mapping import ingest_mapping_review, prepare_mapping_review
from validator.goal_contracts import (
    compile_command_goal,
    prove_goal_task,
    render_goal_contract_file,
    render_goal_state_file,
)


def _joined_goal(project: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    documentary = add_documentary_acceptance(project, FEATURE)
    prepared = prepare_mapping_review(project, FEATURE, project / "mapping.json")
    assert ingest_mapping_review(
        prepared, [_review_response(prepared)], project / "acceptance-review.json"
    ).ready
    skill = project / "producer/.agent-sync/skills/spec-demo"
    skill.mkdir(parents=True)
    (skill / "expectations.md").write_text(EXPECTATIONS)
    (skill / "SKILL.md").write_text(
        "# /spec-demo\n## Execution Tasks\n"
        "- [always] Verify all acceptance <!-- evidence:execution ac-scope:feature -->\n"
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
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))
    evidence = {
        "execution_receipt_path": str(run(project)),
        "acceptance_review_receipt_path": str(documentary),
    }
    return contract, state, evidence


def _complete_goal(contract, state, evidence, project):
    for task in contract["tasks"]:
        if task["id"] == "archive.run":
            continue
        proof = (
            evidence
            if task["evidence_kind"] == "execution"
            else {
                "output": "done",
                "success_criteria_met": True,
            }
        )
        result = prove_goal_task(contract, state, task["id"], proof, project_root=project)
        assert result["accepted"], result
        state = result["state"]
    return state


def _archive(project, contract, state, monkeypatch):
    outside = project.parent / (project.name + "-goal")
    outside.mkdir()
    contract_path, state_path = outside / "contract.json", outside / "state.json"
    contract_path.write_text(json.dumps(contract))
    state_path.write_text(json.dumps(state))
    monkeypatch.chdir(project)
    return CliRunner().invoke(
        app,
        [
            "goal",
            "archive",
            "--contract",
            str(contract_path),
            "--state",
            str(state_path),
            "--exit-code",
            "0",
            "--stdout-file",
            str(project / "stdout.txt"),
            "--json",
        ],
    )


def test_real_execution_and_documentary_review_jointly_prove_archive_and_verify(
    project, monkeypatch
):
    contract, state, evidence = _joined_goal(project)
    state = _complete_goal(contract, state, evidence, project)
    runtime = verify_execution_receipt(Path(evidence["execution_receipt_path"]), project, FEATURE)
    assert runtime.valid and runtime.certified_acs == [AC]
    archived = _archive(project, contract, state, monkeypatch)
    assert archived.exit_code == 0, archived.output
    path = json.loads(archived.output)["archived"]
    verified = CliRunner().invoke(app, ["verify-output", "spec-demo", "--run", path])
    assert verified.exit_code == 0, verified.output


@pytest.mark.parametrize("change", ["missing", "forged", "stale"])
def test_real_runtime_cannot_replace_missing_forged_or_stale_documentary_review(project, change):
    contract, state, evidence = _joined_goal(project)
    if change == "missing":
        evidence.pop("acceptance_review_receipt_path")
    elif change == "forged":
        Path(evidence["acceptance_review_receipt_path"]).write_text('{"reviewed":true}')
    else:
        (project / "migration.md").write_text("Unrelated contracts were changed.")
    task = next(task for task in contract["tasks"] if task.get("acceptance_scope") == "feature")
    result = prove_goal_task(contract, state, task["id"], evidence, project_root=project)
    assert not result["accepted"]
    assert result["state"]["tasks"][task["id"]]["status"] == "pending"


def test_archive_and_terminal_read_recheck_documentary_review_after_real_execution(
    project, monkeypatch
):
    contract, state, evidence = _joined_goal(project)
    state = _complete_goal(contract, state, evidence, project)
    archived = _archive(project, contract, state, monkeypatch)
    assert archived.exit_code == 0, archived.output
    path = json.loads(archived.output)["archived"]
    Path(evidence["acceptance_review_receipt_path"]).write_text('{"reviewed":true}')
    rejected = CliRunner().invoke(app, ["verify-output", "spec-demo", "--run", path])
    assert rejected.exit_code == 1, rejected.output
    repeated = CliRunner().invoke(
        app,
        [
            "goal",
            "archive",
            "--contract",
            str(project.parent / (project.name + "-goal") / "contract.json"),
            "--state",
            str(project.parent / (project.name + "-goal") / "state.json"),
            "--exit-code",
            "0",
            "--stdout-file",
            str(project / "stdout.txt"),
            "--json",
        ],
    )
    assert repeated.exit_code != 0, repeated.output


def _legacy_goal(project):
    import hashlib

    from validator.execution_mapping import AcceptanceMapping, _prepare_mapping_review

    spec = project / ".specs/features" / FEATURE / "spec.md"
    spec.write_text(spec.read_text().replace("# Addition", "## Historical contract"))
    path = project / "mapping.json"
    mapping = AcceptanceMapping.model_validate_json(path.read_bytes())
    prepared = _prepare_mapping_review(project, FEATURE, path, mapping, evidence_policy="1")
    assert ingest_mapping_review(
        prepared, [_review_response(prepared)], project / "acceptance-review.json"
    ).ready
    skill = project / "producer/.agent-sync/skills/spec-demo"
    skill.mkdir(parents=True)
    (skill / "expectations.md").write_text(EXPECTATIONS)
    (skill / "SKILL.md").write_text(
        "# /spec-demo\n## Execution Tasks\n"
        "- [always] Verify all acceptance <!-- evidence:execution ac-scope:feature -->\n"
    )
    goal = compile_command_goal(
        "spec-demo",
        project_root=project,
        livespec_root=project / "producer",
        feature=FEATURE,
    )
    contract = json.loads(render_goal_contract_file(goal))
    canonical = contract["canonical"]
    canonical["evidence_policy_version"] = "1"
    for task in canonical["tasks"]:
        task.get("expected_evidence", {}).pop("acceptance_inventory", None)
    raw = json.dumps(canonical, sort_keys=True)
    contract.update(
        canonical_json=raw,
        evidence_policy_version="1",
        tasks=canonical["tasks"],
        goal_hash=hashlib.sha256(raw.encode()).hexdigest(),
    )
    state = json.loads(render_goal_state_file(goal))
    state["goal_hash"] = contract["goal_hash"]
    (project / "stdout.txt").write_text("done")
    return contract, state, {"execution_receipt_path": str(run(project))}


def test_unchanged_policy1_real_capture_archives_and_rechecks_without_current_exemption(
    project, monkeypatch
):
    contract, state, evidence = _legacy_goal(project)
    spec = project / ".specs/features" / FEATURE / "spec.md"
    before = spec.read_bytes()
    state = _complete_goal(contract, state, evidence, project)
    archived = _archive(project, contract, state, monkeypatch)
    assert archived.exit_code == 0, archived.output
    path = json.loads(archived.output)["archived"]
    verified = CliRunner().invoke(app, ["verify-output", "spec-demo", "--run", path])
    assert verified.exit_code == 0, verified.output
    assert spec.read_bytes() == before
    current = verify_execution_receipt(Path(evidence["execution_receipt_path"]), project, FEATURE)
    assert not current.valid and current.certified_acs == []
