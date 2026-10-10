"""Actual CLI approval writes restore current authority when phase publication fails."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

import validator.pipeline as pipeline_module
from tests.test_penflow_approval_pipeline import _command, _prepare_pipeline
from tests.test_penflow_review_approval import FEATURE, ReviewProject
from tests.test_penflow_review_approval import project as project
from validator.cli import app
from validator.penflow_review_approval import require_approved_requirements


def _baseline_bytes(project: ReviewProject) -> bytes | None:
    return project.baseline.read_bytes() if project.baseline.exists() else None


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("after_rename", [False, True])
def test_failed_phase_write_restores_previous_authority_and_allows_bound_retry(
    project: ReviewProject, monkeypatch: pytest.MonkeyPatch, existing: bool, after_rename: bool
) -> None:
    monkeypatch.chdir(project.root)
    if existing:
        project.approve(project.result(project.snapshot()))
        project.complete_review()
    pipeline = _prepare_pipeline(project)
    before_phase = pipeline.read_bytes()
    before_authority = _baseline_bytes(project)
    result = project.result(project.snapshot())
    actual_write = pipeline_module.write_with_hash_check

    def fail_write(path: Path, content: str) -> str:
        if after_rename:
            actual_write(path, content)
        raise OSError("injected phase publication failure")

    monkeypatch.setattr(pipeline_module, "write_with_hash_check", fail_write)
    response = CliRunner().invoke(app, _command(result), catch_exceptions=False)
    assert response.exit_code == 1 and "injected phase publication failure" in response.output
    assert pipeline.read_bytes() == before_phase
    assert _baseline_bytes(project) == before_authority
    archives = project.root / ".specs/penflow-approvals"
    assert list(archives.glob("baseline-*.json"))
    archived_bytes = {path: path.read_bytes() for path in archives.iterdir() if path.is_file()}
    monkeypatch.setattr(pipeline_module, "write_with_hash_check", actual_write)
    retried = CliRunner().invoke(app, _command(result), catch_exceptions=False)
    assert retried.exit_code == 0, retried.output
    require_approved_requirements(project.root, FEATURE)
    assert "| Plan Review | Done |" in pipeline.read_text()
    assert all(path.read_bytes() == raw for path, raw in archived_bytes.items())


@pytest.mark.parametrize("foreign", ["phase", "authority"])
def test_failed_publication_does_not_overwrite_observed_foreign_bytes(
    project: ReviewProject, monkeypatch: pytest.MonkeyPatch, foreign: str
) -> None:
    monkeypatch.chdir(project.root)
    pipeline = _prepare_pipeline(project)
    before = pipeline.read_bytes()
    result = project.result(project.snapshot())
    target = pipeline if foreign == "phase" else project.baseline
    foreign_bytes = b"written by a noncooperating writer\n"

    def fail_write(path: Path, content: str) -> str:
        target.write_bytes(foreign_bytes)
        raise OSError("injected phase publication failure")

    monkeypatch.setattr(pipeline_module, "write_with_hash_check", fail_write)
    response = CliRunner().invoke(app, _command(result), catch_exceptions=False)
    assert response.exit_code == 1
    assert "pipeline_approval_rollback_failed" in response.output
    assert "pipeline_rollback_conflict" in response.output
    assert target.read_bytes() == foreign_bytes
    if foreign == "authority":
        assert pipeline.read_bytes() == before
    else:
        assert project.baseline.is_file()


def test_failed_approval_restoration_is_explicit_and_not_reported_as_success(
    project: ReviewProject, monkeypatch: pytest.MonkeyPatch
) -> None:
    from validator import pipeline_approval_write

    monkeypatch.chdir(project.root)
    project.approve(project.result(project.snapshot()))
    project.complete_review()
    pipeline = _prepare_pipeline(project)
    before = pipeline.read_bytes()
    result = project.result(project.snapshot())

    def fail_write(path: Path, content: str) -> str:
        raise OSError("injected phase publication failure")

    def fail_restore(path: Path, content: str) -> None:
        raise OSError("restoration storage unavailable")

    monkeypatch.setattr(pipeline_module, "write_with_hash_check", fail_write)
    monkeypatch.setattr(pipeline_approval_write, "atomic_write", fail_restore)
    response = CliRunner().invoke(app, _command(result), catch_exceptions=False)
    assert response.exit_code == 1
    assert "pipeline_approval_rollback_failed" in response.output
    assert "restoration storage unavailable" in response.output
    assert "injected phase publication failure" in response.output
    assert "Updated" not in response.output
    assert pipeline.read_bytes() == before
