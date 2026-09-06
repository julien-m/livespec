"""Approval publication, interrupted pipeline writes and governed visual retirement."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import validator.pipeline as pipeline_module
from tests.test_penflow_review_approval import FEATURE, ReviewProject
from tests.test_penflow_review_approval import project as project
from validator.cli import app
from validator.locks import acquire_lock
from validator.penflow_approval_files import PenflowApprovalError
from validator.penflow_closure import PenflowClosureError, require_penflow_closure
from validator.penflow_review_approval import require_approved_requirements


def _prepare_pipeline(project: ReviewProject) -> Path:
    pipeline = project.spec.parent / "pipeline.md"
    pipeline.write_text("| Phase | Status | Completed At |\n| Plan Review | Pending | — |\n")
    return pipeline


def _command(result: Path) -> list[str]:
    return [
        "pipeline",
        "update",
        "--feature",
        FEATURE,
        "--phase",
        "plan-review",
        "--status",
        "done",
        "--review-result",
        str(result),
    ]


def test_cli_snapshot_then_review_transition_publishes_bound_authority(
    project: ReviewProject, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(project.root)
    pipeline = _prepare_pipeline(project)
    runner = CliRunner()
    result = runner.invoke(
        app, ["penflow-contract", "review-snapshot", "--feature", FEATURE, "--json"]
    )
    assert result.exit_code == 0, result.output
    snapshot = json.loads(result.stdout)
    review = project.result(snapshot)
    assert runner.invoke(app, _command(review)).exit_code == 0
    assert "| Plan Review | Done |" in pipeline.read_text()
    require_approved_requirements(project.root, FEATURE)
    assert runner.invoke(app, _command(review)).exit_code == 0


def test_interrupted_phase_write_keeps_valid_baseline_nonfinal_and_retries(
    project: ReviewProject, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(project.root)
    pipeline = _prepare_pipeline(project)
    before = pipeline.read_text()
    result = project.result(project.snapshot())
    actual_write = pipeline_module.write_with_hash_check

    def interrupted(path: Path, content: str) -> str:
        raise OSError("interrupted phase write")

    monkeypatch.setattr(pipeline_module, "write_with_hash_check", interrupted)
    response = CliRunner().invoke(app, _command(result))
    assert response.exit_code == 1 and "interrupted phase write" in response.output
    assert project.baseline.is_file() and pipeline.read_text() == before
    with pytest.raises(PenflowApprovalError, match="plan_review_not_completed"):
        require_approved_requirements(project.root, FEATURE)
    monkeypatch.setattr(pipeline_module, "write_with_hash_check", actual_write)
    assert CliRunner().invoke(app, _command(result)).exit_code == 0
    require_approved_requirements(project.root, FEATURE)


def test_project_lock_contention_writes_no_approval_then_retry_succeeds(
    project: ReviewProject, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(project.root)
    pipeline = _prepare_pipeline(project)
    before = pipeline.read_text()
    result = project.result(project.snapshot())
    monkeypatch.setattr(
        pipeline_module, "acquire_lock", lambda root: acquire_lock(root, timeout=0.01)
    )
    with acquire_lock(project.root / ".specs"):
        response = CliRunner().invoke(app, _command(result))
    assert response.exit_code == 1
    assert not project.baseline.exists() and pipeline.read_text() == before
    assert CliRunner().invoke(app, _command(result)).exit_code == 0


def test_unapproved_visual_removal_blocks_but_bound_retirement_can_close(
    project: ReviewProject,
) -> None:
    project.approve(project.result(project.snapshot()))
    project.complete_review()
    project.spec.write_text(project.spec.read_text().replace("visual: true", "visual: false"))
    project.contract.unlink()
    with pytest.raises(PenflowClosureError, match="approved_visual_disposition_mismatch"):
        require_penflow_closure(project.root, FEATURE)
    snapshot = project.snapshot()
    baseline = project.approve(project.result(snapshot))
    assert baseline["disposition"] == "retired"
    assert baseline["previous"] is not None
    assert baseline["contract"]["path"].startswith(".specs/penflow-approvals/contract-")
    require_penflow_closure(project.root, FEATURE)
    with pytest.raises(PenflowApprovalError, match="approved_visual_disposition_mismatch"):
        require_approved_requirements(project.root, FEATURE)


def test_retirement_review_can_precede_cleanup_but_closure_cannot(project: ReviewProject) -> None:
    project.approve(project.result(project.snapshot()))
    project.complete_review()
    screenshot = project.spec.parent / "design/current.png"
    screenshot.parent.mkdir()
    screenshot.write_bytes(b"active-render")
    project.spec.write_text(project.spec.read_text().replace("visual: true", "visual: false"))
    project.approve(project.result(project.snapshot()))
    with pytest.raises(PenflowClosureError, match="visual_authority_conflict"):
        require_penflow_closure(project.root, FEATURE)
    screenshot.unlink()
    require_penflow_closure(project.root, FEATURE)
