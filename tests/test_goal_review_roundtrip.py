"""Current proof purposes cannot be replaced by documentary success assertions."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.review_support import grounded_response, reviewed_project
from tests.test_goal_contracts import EXPECTATIONS
from validator.cli import app
from validator.goal_contracts import (
    compile_command_goal,
    render_goal_contract_file,
    render_goal_state_file,
)
from validator.semantic.review_api import ingest_feature_review, prepare_feature_review


@pytest.fixture
def review_goal_files(tmp_path, monkeypatch):
    reviewed_project(tmp_path)
    skill = tmp_path / "producer/.agent-sync/skills/spec-demo"
    skill.mkdir(parents=True)
    (skill / "expectations.md").write_text(EXPECTATIONS)
    (skill / "SKILL.md").write_text(
        "# /spec-demo\n## Execution Tasks\n"
        "- [always] Review current requirements <!-- evidence:review review-kind:plan -->\n"
        "## Definition of Done (Command-Level)\n"
        "- [ ] Output prepared <!-- evidence:documentary -->\n"
    )
    from validator import goal_cli_actions

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(goal_cli_actions, "_detect_livespec_root", lambda: tmp_path / "producer")
    config = tmp_path / ".specs/semantic/config.yaml"
    config.unlink()
    for kind in ("spec", "plan"):
        prepared = prepare_feature_review(tmp_path, "001-test", kind, "reviewer/v1")
        ingest_feature_review(
            tmp_path, "001-test", kind, [grounded_response(prepared)], model="reviewer/v1"
        )
    goal = compile_command_goal(
        "spec-demo",
        project_root=tmp_path,
        livespec_root=tmp_path / "producer",
        feature="001-test",
        flags="--model=reviewer/v1",
    )
    contract = tmp_path / "contract.json"
    state = tmp_path / "state.json"
    contract.write_text(render_goal_contract_file(goal))
    state.write_text(render_goal_state_file(goal))
    common = ["--contract", str(contract), "--state", str(state)]
    return CliRunner(), goal, contract, state, common


def test_resolved_model_roundtrips_through_native_goal_render(review_goal_files):
    runner, _, _, _, _ = review_goal_files
    unresolved = runner.invoke(
        app, ["goal", "render", "spec-demo", "--feature", "001-test", "--save"]
    )
    assert unresolved.exit_code == 2
    assert "reviewer_model_unresolved" in unresolved.output
    assert "contract-file:" not in unresolved.output
    rendered = runner.invoke(
        app,
        [
            "goal",
            "render",
            "spec-demo",
            "--feature",
            "001-test",
            "--flags",
            "--model=reviewer/v1",
            "--json",
        ],
    )
    assert rendered.exit_code == 0, rendered.output
    assert "--model=reviewer/v1" in json.loads(rendered.output)["canonical"]["normalized_flags"]


def test_rendered_files_prove_and_archive_current_review_policy(tmp_path, review_goal_files):
    runner, goal, _, _, common = review_goal_files
    for task in goal.payload["tasks"]:
        if task["id"] == "archive.run":
            continue
        evidence = {"output": "done", "success_criteria_met": True}
        if task["evidence_kind"] == "review":
            rejected = runner.invoke(
                app,
                [
                    "goal",
                    "prove",
                    *common,
                    "--task",
                    task["id"],
                    "--evidence",
                    json.dumps(evidence),
                ],
            )
            assert rejected.exit_code == 1
            evidence = {
                "review_receipt_path": str(tmp_path / ".specs/features/001-test/.reviews/plan.json")
            }
        result = runner.invoke(
            app,
            ["goal", "prove", *common, "--task", task["id"], "--evidence", json.dumps(evidence)],
        )
        assert result.exit_code == 0, result.output
    stdout = tmp_path / "stdout.txt"
    stdout.write_text("done")
    archive = runner.invoke(
        app,
        ["goal", "archive", *common, "--exit-code", "0", "--stdout-file", str(stdout), "--json"],
    )
    assert archive.exit_code == 0, archive.output
    artifacts = list((tmp_path / ".specs/.runs").rglob("*.json"))
    assert any(
        json.loads(path.read_text()).get("evidence_policy_version") == "2" for path in artifacts
    )
    verified = runner.invoke(
        app, ["verify-output", "spec-demo", "--run", json.loads(archive.output)["archived"]]
    )
    assert verified.exit_code == 0, verified.output


@pytest.fixture
def completed_review_goal(tmp_path, review_goal_files):
    runner, goal, contract, state, common = review_goal_files
    for task in goal.payload["tasks"]:
        if task["id"] == "archive.run":
            continue
        evidence = {"output": "done", "success_criteria_met": True}
        if task["evidence_kind"] == "review":
            evidence = {
                "review_receipt_path": str(tmp_path / ".specs/features/001-test/.reviews/plan.json")
            }
        runner.invoke(
            app,
            ["goal", "prove", *common, "--task", task["id"], "--evidence", json.dumps(evidence)],
            catch_exceptions=False,
        )
    return runner, goal, contract, state, common


def test_archive_and_verify_output_reject_forged_review_evidence(completed_review_goal):
    runner, goal, contract, state, common = completed_review_goal
    forged_state = json.loads(state.read_text())
    review_task = next(task for task in goal.payload["tasks"] if task["evidence_kind"] == "review")
    forged_state["tasks"][review_task["id"]]["accepted_evidence"] = {"output": "review passed"}
    state.write_text(json.dumps(forged_state))
    forged_archive = runner.invoke(app, ["goal", "archive", *common, "--exit-code", "0", "--json"])
    assert forged_archive.exit_code == 1
    forged_artifact = json.loads(Path(json.loads(forged_archive.output)["archived"]).read_text())
    assert forged_artifact["evidence_errors"][review_task["id"]] == ["review_receipt_path"]
    reread = runner.invoke(
        app, ["verify-output", "spec-demo", "--run", json.loads(forged_archive.output)["archived"]]
    )
    assert reread.exit_code == 1, reread.output
    tampered = json.loads(contract.read_text())
    tampered["tasks"][0]["evidence_kind"] = "documentary"
    contract.write_text(json.dumps(tampered))
    rejected_archive = runner.invoke(
        app, ["goal", "archive", *common, "--exit-code", "0", "--json"]
    )
    assert rejected_archive.exit_code == 2
    assert "current_contract_mirror_mismatch:tasks" in rejected_archive.output


def test_verify_output_rejects_future_archive_policy(tmp_path, completed_review_goal):
    runner, _, _, _, common = completed_review_goal
    archive = runner.invoke(app, ["goal", "archive", *common, "--exit-code", "0", "--json"])
    assert archive.exit_code == 0, archive.output
    future = json.loads(Path(json.loads(archive.output)["archived"]).read_text())
    future["evidence_policy_version"] = "999"
    future_path = tmp_path / "future-run.json"
    future_path.write_text(json.dumps(future))
    future_read = runner.invoke(app, ["verify-output", "spec-demo", "--run", str(future_path)])
    assert future_read.exit_code == 2
    assert "unsupported evidence_policy_version" in future_read.output
