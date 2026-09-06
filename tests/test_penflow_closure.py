"""Lifecycle closure regressions; protocol doubles isolate external transport only."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.penflow_approval_fixtures import approved_feature
from tests.test_penflow_contract_verification import _response, _transport, _workspace
from tests.test_pipeline import PIPELINE_MD
from validator.cli import app
from validator.penflow_closure import PenflowClosureError, require_penflow_closure
from validator.visual_gate import detect_visual_feature

SLUG = "001-test"


def feature(root: Path, *, visual: bool = True, active: bool = True) -> Path:
    path = root / ".specs/features" / SLUG
    path.mkdir(parents=True)
    (path / "spec.md").write_text(f"---\nvisual: {str(visual).lower()}\nstatus: In Progress\n---\n")
    if active:
        (path / "design/flow-ui-contract").mkdir(parents=True)
    return path


@pytest.mark.parametrize("status", ["done", "skipped"])
def test_visual_test_completion_fails_before_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: str
) -> None:
    folder = feature(tmp_path)
    pipeline = folder / "pipeline.md"
    pipeline.write_text(PIPELINE_MD)
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        app, ["pipeline", "update", "--feature", SLUG, "--phase", "test", "--status", status]
    )
    assert result.exit_code == 1 and "not_certified" in result.output
    assert result.output.count("BLOCKED:") == 1
    assert pipeline.read_text() == PIPELINE_MD


def test_pipeline_lifecycle_preparation_coding_test_and_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = feature(tmp_path)
    pipeline = folder / "pipeline.md"
    pipeline.write_text(PIPELINE_MD)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    prefix = ["pipeline", "update", "--feature", SLUG]
    for phase in ("specify", "implement"):
        assert runner.invoke(app, [*prefix, "--phase", phase, "--status", "done"]).exit_code == 0
    assert runner.invoke(app, [*prefix, "--phase", "test", "--status", "done"]).exit_code == 1
    _workspace(tmp_path)
    approved_feature(tmp_path, SLUG)
    manifest = tmp_path / "runner-build.json"
    manifest.write_text("{}")
    calls = _transport(monkeypatch, _response(tmp_path, "implementation"))
    command = [*prefix, "--phase", "test", "--status", "done", "--build-manifest", str(manifest)]
    assert runner.invoke(app, command).exit_code == 0
    assert len(calls) == 1
    (tmp_path / "penflow/run-report.json").write_text("stale replacement")
    assert runner.invoke(app, command).exit_code == 1
    assert len(calls) == 2


@pytest.mark.parametrize("operation", ["update", "next"])
def test_terminal_pipeline_revalidates_even_outside_test_phase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    folder = feature(tmp_path)
    content = PIPELINE_MD.replace("Pending", "Done")
    (folder / "pipeline.md").write_text(content)
    monkeypatch.chdir(tmp_path)
    command = ["pipeline", operation, "--feature", SLUG]
    if operation == "update":
        command += ["--phase", "plan", "--status", "done"]
    result = CliRunner().invoke(app, command)
    assert result.exit_code == 1 and "not_certified" in result.output
    assert (folder / "pipeline.md").read_text() == content


def test_partial_visual_opt_out_exposes_active_contradiction(tmp_path: Path) -> None:
    feature(tmp_path, visual=False)
    classification = detect_visual_feature(project_root=tmp_path, feature_slug=SLUG)
    assert classification.classification == "NON_VISUAL"
    assert classification.signals.s4_flow_ui_contract
    with pytest.raises(PenflowClosureError, match="visual_authority_conflict"):
        require_penflow_closure(tmp_path, SLUG)


def test_removing_marker_does_not_hide_active_visual_contract(tmp_path: Path) -> None:
    folder = feature(tmp_path)
    (folder / "spec.md").write_text("# Feature\n")
    with pytest.raises(PenflowClosureError, match="not_certified"):
        require_penflow_closure(tmp_path, SLUG)


def test_nonvisual_conversion_ignores_historical_archives(tmp_path: Path) -> None:
    folder = feature(tmp_path, visual=False, active=False)
    historical = folder / "checks/old-run"
    historical.mkdir(parents=True)
    (historical / "screenshot.png").write_bytes(b"historical")
    require_penflow_closure(tmp_path, SLUG)


def test_visual_marker_without_artifacts_is_conflict(tmp_path: Path) -> None:
    feature(tmp_path, active=False)
    with pytest.raises(PenflowClosureError, match="visual_authority_conflict"):
        require_penflow_closure(tmp_path, SLUG)


@pytest.mark.parametrize("operation", ["update", "next"])
@pytest.mark.parametrize("mutation", ["deleted", "malformed", "empty"])
def test_terminal_pipeline_requires_current_readable_spec(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str, mutation: str
) -> None:
    folder = feature(tmp_path, visual=False, active=False)
    content = PIPELINE_MD.replace("Pending", "Done")
    pipeline = folder / "pipeline.md"
    pipeline.write_text(content)
    spec = folder / "spec.md"
    if mutation == "deleted":
        spec.unlink()
    else:
        spec.write_text("---\nvisual: [\n---\n" if mutation == "malformed" else "")
    monkeypatch.chdir(tmp_path)
    command = ["pipeline", operation, "--feature", SLUG]
    if operation == "update":
        command += ["--phase", "test", "--status", "done"]
    result = CliRunner().invoke(app, command, catch_exceptions=False)
    assert result.exit_code == 1
    assert "visual_closure_spec" in result.output
    assert "Traceback" not in result.output
    assert pipeline.read_text() == content


def test_unreadable_nonvisual_spec_is_not_an_opt_out(tmp_path: Path) -> None:
    folder = feature(tmp_path, visual=False, active=False)
    spec = folder / "spec.md"
    spec.chmod(0o000)
    try:
        with pytest.raises(PenflowClosureError, match="visual_closure_spec_unreadable"):
            require_penflow_closure(tmp_path, SLUG)
    finally:
        spec.chmod(0o644)
