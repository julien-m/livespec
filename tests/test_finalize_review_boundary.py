"""A first real finalization keeps current review proof usable through CLI archival."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.review_support import review_existing_project
from tests.test_finalize import _make_specs_tree
from tests.test_goal_contracts import EXPECTATIONS
from validator.cli import app
from validator.goal_contracts import (
    GoalContract,
    compile_command_goal,
    render_goal_contract_file,
    render_goal_state_file,
)
from validator.progression_gate import require_progression


def _prepare_reviewed_goal(tmp_path: Path, feature: str) -> GoalContract:
    """Create current review inputs and a typed command before the first finalization."""
    specs = _make_specs_tree(tmp_path)
    spec = specs / "features" / feature / "spec.md"
    spec.write_text(
        spec.read_text()
        + "\n## FR-001\nDelete expired files.\n## AC-001\nExpired files are absent.\n"
    )
    review_existing_project(tmp_path, feature)
    skill = tmp_path / "producer/.agent-sync/skills/spec-demo"
    skill.mkdir(parents=True)
    (skill / "expectations.md").write_text(EXPECTATIONS)
    (skill / "SKILL.md").write_text(
        "# /spec-demo\n## Execution Tasks\n"
        "- [always] Review current requirements <!-- evidence:review review-kind:plan -->\n"
        "## Definition of Done (Command-Level)\n"
        "- [ ] Output prepared <!-- evidence:documentary -->\n"
    )
    goal = compile_command_goal(
        "spec-demo",
        project_root=tmp_path,
        livespec_root=tmp_path / "producer",
        feature=feature,
        flags="--model=reviewer/v1",
    )
    (tmp_path / "contract.json").write_text(render_goal_contract_file(goal))
    (tmp_path / "state.json").write_text(render_goal_state_file(goal))
    (tmp_path / "entry.md").write_text("Feature lifecycle synchronized")
    (tmp_path / "stdout.txt").write_text("done")
    return goal


def test_first_finalize_preserves_current_review_prove_and_archive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    feature = "004-notifications"
    goal = _prepare_reviewed_goal(tmp_path, feature)
    spec = tmp_path / ".specs/features" / feature / "spec.md"
    contract, state = tmp_path / "contract.json", tmp_path / "state.json"
    entry = tmp_path / "entry.md"
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    finalized = runner.invoke(
        app,
        [
            "finalize",
            "apply",
            "--feature",
            feature,
            "--command",
            "spec-demo",
            "--status",
            "Implemented",
            "--entry-file",
            str(entry),
            "--json",
        ],
    )
    assert finalized.exit_code == 0, finalized.output
    assert "<!-- finalize:" not in spec.read_text()
    require_progression(tmp_path, feature, "implement", model="reviewer/v1")
    common = ["--contract", str(contract), "--state", str(state)]
    for task in goal.payload["tasks"]:
        if task["id"] == "archive.run":
            continue
        evidence = {"output": "done", "success_criteria_met": True}
        if task["evidence_kind"] == "review":
            evidence = {"review_receipt_path": str(spec.parent / ".reviews/plan.json")}
        proven = runner.invoke(
            app,
            ["goal", "prove", *common, "--task", task["id"], "--evidence", json.dumps(evidence)],
        )
        assert proven.exit_code == 0, proven.output
    stdout = tmp_path / "stdout.txt"
    archived = runner.invoke(
        app,
        ["goal", "archive", *common, "--exit-code", "0", "--stdout-file", str(stdout), "--json"],
    )
    assert archived.exit_code == 0, archived.output
    receipt_path = json.loads(archived.output)["archived"]
    verified = runner.invoke(app, ["verify-output", "spec-demo", "--run", receipt_path])
    assert verified.exit_code == 0, verified.output
