"""Specify review flags govern obligations without granting semantic readiness (081)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.lightweight_goals_support import isolate_saved_goals
from validator.cli import app
from validator.finalize import ApplyRequest, apply_finalization, verify_finalization
from validator.goal_contracts import (
    compile_command_goal,
    prove_goal_task,
    render_goal_contract_file,
)

ROOT = Path(__file__).resolve().parents[1]
FEATURE = "001-demo"
QE = {
    "qe_dimensions_considered": ["correctness"],
    "qe_gates_required": ["regression"],
    "qe_expected_evidence": ["pytest"],
    "qe_gaps_or_missing_evidence": ["semantic review explicitly skipped"],
    "qe_boundary_note": "Review/audit owns defect hunting; tests own evidence sufficiency.",
}


@pytest.mark.parametrize(
    ("flags", "review_required"),
    [
        ("--auto --no-review --no-visual --model=gpt-6.1-sol", False),
        ("--auto -N --no-visual", False),
        ("--no-review", False),
        (["--auto", "-N", "--all-reviewers", "--model", "reviewer/v1"], False),
        ("--auto --no-review --no-review --review-max-chars=30000", False),
        ("--auto --no-visual --model=gpt-6.1-sol", True),
        (None, True),
        ("--auto --all-reviewers", True),
        ("--auto --model=no-review", True),
        ("--auto --no-review-extra", True),
    ],
)
def test_specify_review_obligation_matches_flags(
    tmp_path: Path, flags: str | list[str] | None, review_required: bool
) -> None:
    goal = compile_command_goal(
        "spec-specify", project_root=tmp_path, livespec_root=ROOT, flags=flags
    )
    contract = json.loads(render_goal_contract_file(goal))
    reviews = [task for task in contract["tasks"] if task["evidence_kind"] == "review"]
    assert bool(reviews) is review_required
    assert any("Run LLM spec review" in row for row in contract["checklist"]) is review_required
    if review_required:
        assert len(reviews) == 1
        assert reviews[0]["required_evidence"] == ["review_receipt_path"]
        assert reviews[0]["expected_evidence"]["review_kind"] == "spec"
    assert [task["ordinal"] for task in contract["tasks"]] == list(
        range(1, len(contract["tasks"]) + 1)
    )
    assert [task["id"] for task in contract["tasks"]][-2:] == ["outcome.verified", "archive.run"]


def _project(root: Path) -> Path:
    directory = root / ".specs/features" / FEATURE
    directory.mkdir(parents=True)
    spec = (ROOT / "tests/fixtures/valid_spec.md").read_text()
    spec = spec.replace("## User Scenarios", "# Demo\n\n- **Status:** Draft\n\n## User Scenarios")
    spec = spec.replace("AC content here.", "- **AC-001:** Export writes one local JSON file.")
    spec = spec.replace("FR content here.", "- **FR-001:** Export writes one local JSON file.")
    (directory / "spec.md").write_text(spec)
    (root / ".specs/semantic").mkdir()
    (root / ".specs/semantic/config.yaml").write_text("review_model: reviewer/v1\n")
    for name, text in (
        ("project.md", "Local CLI exports."),
        ("constitution.md", "Local execution."),
        ("stacks/_default.md", "Python."),
        ("roadmap.md", "# Roadmap\n\n- [x] [Demo](features/001-demo/spec.md)\n"),
    ):
        path = root / ".specs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return directory


def _finalize(project: Path) -> Path:
    apply_finalization(
        project,
        ApplyRequest(
            feature_slug=FEATURE,
            command="spec-specify",
            status="Draft",
            entry_body="Spec: Draft prepared; semantic review skipped.",
            global_summary="[Feature 001] Spec: Draft prepared",
            run_id="no-review",
        ),
    )
    result = verify_finalization(
        project, FEATURE, expected_command="spec-specify", run_id="no-review"
    )
    assert result.verdict == "PASS"
    return result.receipt_path


def _render(runner: CliRunner, flag: str) -> tuple[Path, Path]:
    result = runner.invoke(
        app,
        [
            "goal",
            "render",
            "spec-specify",
            "--feature",
            FEATURE,
            "--flags",
            f"--auto {flag}",
            "--save",
        ],
    )
    assert result.exit_code == 0, result.output
    match = re.search(r"contract-file:(\S+) \| state-file:(\S+)", result.output)
    assert match is not None
    return Path(match[1]), Path(match[2])


@pytest.mark.real_stop_condition
@pytest.mark.parametrize("flag", ["--no-review", "-N"])
def test_no_review_goal_closes_without_creating_semantic_receipts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, flag: str
) -> None:
    project = tmp_path / "project"
    directory = _project(project)
    config = project / ".specs/semantic/config.yaml"
    config.unlink()
    runner = isolate_saved_goals(project, tmp_path, monkeypatch)
    finalize_receipt = _finalize(project)
    contract, state = _render(runner, flag)
    common = ["--contract", str(contract), "--state", str(state)]
    original = contract.read_bytes()
    evidence = {
        "qe.analysis": QE,
        "finalize.registry": {"finalize_receipt_path": str(finalize_receipt)},
        "outcome.verified": {},
    }
    for task, proof in evidence.items():
        result = runner.invoke(
            app, ["goal", "prove", *common, "--task", task, "--evidence", json.dumps(proof)]
        )
        assert result.exit_code == 0, result.output
    _close_archive(runner, common)
    assert contract.read_bytes() == original
    assert json.loads(state.read_text())["status"] == "complete"
    assert not list(directory.glob(".reviews/*.json"))
    assert "status: Draft" in (directory / "spec.md").read_text()
    config.write_text("review_model: reviewer/v1\n")
    for destination in ("plan", "implement"):
        progression = runner.invoke(app, ["validate", str(directory), "--progression", destination])
        assert progression.exit_code == 1, progression.output
        assert "clarify_not_ready" in progression.output
        bypass = runner.invoke(
            app, ["validate", str(directory), "--progression", destination, "--no-review"]
        )
        assert bypass.exit_code == 1, bypass.output
        assert "semantic operations do not support --no-review" in bypass.output


def test_specify_opt_out_does_not_remove_plan_review(tmp_path: Path) -> None:
    goal = compile_command_goal(
        "spec-plan", project_root=tmp_path, livespec_root=ROOT, flags="--auto --no-review -N"
    )
    assert any(task["evidence_kind"] == "review" for task in goal.payload["tasks"])


def _close_archive(runner: CliRunner, common: list[str]) -> None:
    archive = runner.invoke(app, ["goal", "archive", *common, "--exit-code", "0", "--json"])
    assert archive.exit_code == 0, archive.output
    artifact = json.loads(archive.output)["archived"]
    proof = runner.invoke(
        app,
        [
            "goal",
            "prove",
            *common,
            "--task",
            "archive.run",
            "--evidence",
            json.dumps({"run_artifact_path": artifact}),
        ],
    )
    assert proof.exit_code == 0, proof.output
    verified = runner.invoke(app, ["verify-output", "spec-specify", "--run", artifact])
    assert verified.exit_code == 0, verified.output
    status = runner.invoke(app, ["goal", "status", "--state", common[3]])
    assert status.exit_code == 0, status.output
    assert "complete" in status.output


def test_default_review_rejects_a_skip_claim(tmp_path: Path) -> None:
    from tests.review_support import grounded_response
    from validator.goal_contracts import render_goal_state_file
    from validator.semantic.review_api import ingest_feature_review, prepare_feature_review

    _project(tmp_path)
    goal = compile_command_goal(
        "spec-specify",
        project_root=tmp_path,
        livespec_root=ROOT,
        feature=FEATURE,
        flags="--auto --model=reviewer/v1",
    )
    contract = json.loads(render_goal_contract_file(goal))
    review = next(task for task in contract["tasks"] if task["evidence_kind"] == "review")
    result = prove_goal_task(
        contract,
        json.loads(render_goal_state_file(goal)),
        review["id"],
        {"output": "Review skipped", "success_criteria_met": True},
        project_root=tmp_path,
    )
    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "review_receipt_path" in result["missing_evidence"]
    prepared = prepare_feature_review(tmp_path, FEATURE, "spec", "reviewer/v1")
    ingest_feature_review(
        tmp_path, FEATURE, "spec", [grounded_response(prepared)], model="reviewer/v1"
    )
    accepted = prove_goal_task(
        contract,
        result["state"],
        review["id"],
        {"review_receipt_path": f".specs/features/{FEATURE}/.reviews/spec.json"},
        project_root=tmp_path,
    )
    assert accepted["status"] == "ACCEPTED", accepted
