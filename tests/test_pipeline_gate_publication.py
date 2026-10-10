"""Rejected pipeline transitions must not publish new review authority."""

import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.test_penflow_approval_pipeline import _command
from tests.test_penflow_review_approval import ReviewProject
from tests.test_penflow_review_approval import project as project
from validator.cli import app
from validator.pipeline import PHASE_MAP, PHASE_ORDER


def _approval_files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in (root / ".specs/penflow-approvals").rglob("*")
        if path.is_file()
    }


@pytest.mark.parametrize("failure", ["terminal", "malformed_row"])
def test_rejected_plan_review_does_not_publish_approval(
    project: ReviewProject, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    monkeypatch.chdir(project.root)
    pipeline = project.spec.parent / "pipeline.md"
    content = "not a phase table\n"
    if failure == "terminal":
        content = "| Phase | Status | Completed At |\n" + "".join(
            f"| {PHASE_MAP[phase]} | {'Pending' if phase == 'plan-review' else 'Done'} | — |\n"
            for phase in PHASE_ORDER
        )
    pipeline.write_text(content)
    result = project.result(project.snapshot())
    before = _approval_files(project.root)
    response = CliRunner().invoke(app, _command(result), catch_exceptions=False)
    assert response.exit_code == 1, response.output
    expected = "BLOCKED:" if failure == "terminal" else "not found"
    assert expected in response.output, response.output
    assert pipeline.read_text() == content
    assert not project.baseline.exists(), response.output
    assert _approval_files(project.root) == before


def _retired_terminal_review(project: ReviewProject) -> tuple[Path, Path, str]:
    project.approve(project.result(project.snapshot()))
    project.complete_review()
    project.spec.write_text(project.spec.read_text().replace("visual: true", "visual: false"))
    project.contract.unlink()
    result = project.result(project.snapshot())
    project.approve(result)
    pipeline = project.spec.parent / "pipeline.md"
    content = "| Phase | Status | Completed At |\n" + "".join(
        f"| {PHASE_MAP[phase]} | Done | — |\n" for phase in PHASE_ORDER
    )
    pipeline.write_text(content)
    return result, pipeline, content


def _change_review(project: ReviewProject, result: Path, change: str) -> Path:
    if change == "snapshot":
        return project.result(project.snapshot())
    if change in {"reviewer", "raw"}:
        wrapper = json.loads(result.read_text())
        output = project.root / wrapper["review"]["output"]["path"]
        if change == "reviewer":
            raw = json.loads(output.read_text())
            raw["producer_id"] = "another-reviewer"
            wrapper["review"]["producer_id"] = raw["producer_id"]
            output.write_text(json.dumps(raw))
        else:
            output.write_bytes(output.read_bytes() + b"\n")
        wrapper["review"]["output"]["sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
        result.write_text(json.dumps(wrapper))
    return result


@pytest.mark.parametrize("change", ["none", "snapshot", "reviewer", "raw"])
def test_terminal_review_replays_only_the_certified_approval(
    project: ReviewProject, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    monkeypatch.chdir(project.root)
    result, pipeline, content = _retired_terminal_review(project)
    result = _change_review(project, result, change)
    before = _approval_files(project.root)
    baseline = project.baseline.read_bytes()
    response = CliRunner().invoke(app, _command(result), catch_exceptions=False)
    assert response.exit_code == (0 if change == "none" else 1), response.output
    if change != "none":
        assert "terminal_review_requires_reopen" in response.output
    assert project.baseline.read_bytes() == baseline
    assert pipeline.read_text() == content
    assert _approval_files(project.root) == before


def test_terminal_replay_still_requires_current_closure(
    project: ReviewProject, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(project.root)
    result = project.result(project.snapshot())
    project.approve(result)
    pipeline = project.spec.parent / "pipeline.md"
    content = "| Phase | Status | Completed At |\n" + "".join(
        f"| {PHASE_MAP[phase]} | Done | — |\n" for phase in PHASE_ORDER
    )
    pipeline.write_text(content)
    before = _approval_files(project.root)
    baseline = project.baseline.read_bytes()
    response = CliRunner().invoke(app, _command(result), catch_exceptions=False)
    assert response.exit_code == 1 and "visual_authority_conflict" in response.output
    assert pipeline.read_text() == content
    assert project.baseline.read_bytes() == baseline
    assert _approval_files(project.root) == before


def test_new_review_can_resume_after_reopening_an_existing_phase(
    project: ReviewProject, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(project.root)
    _, pipeline, _ = _retired_terminal_review(project)
    result = project.result(project.snapshot())
    baseline = project.baseline.read_bytes()
    runner = CliRunner()
    reopened = runner.invoke(
        app,
        [
            "pipeline",
            "update",
            "--feature",
            project.spec.parent.name,
            "--phase",
            "analyze",
            "--status",
            "pending",
        ],
        catch_exceptions=False,
    )
    assert reopened.exit_code == 0, reopened.output
    response = runner.invoke(app, _command(result), catch_exceptions=False)
    assert response.exit_code == 0, response.output
    assert "| Analyze | Pending |" in pipeline.read_text()
    assert "| Plan Review | Done |" in pipeline.read_text()
    assert project.baseline.read_bytes() != baseline
