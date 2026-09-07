"""Archive confinement tests for the ``spec-init`` goal bootstrap."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests._json_fixture import json_fixture
from tests.goal_bootstrap_support import archive_valid_pair as valid_pair
from tests.goal_bootstrap_support import write_pair
from validator import goal_archive_fd, goal_archive_paths
from validator.cli import app
from validator.run_artifacts import archive_goal_run

runner = CliRunner()


def test_archive_before_specs_blocks_without_creation(tmp_path: Path) -> None:
    contract, state = valid_pair(tmp_path)
    before = deepcopy(state)

    result = archive_goal_run(contract, state, project_root=Path.cwd(), exit_code=0)

    assert result.outcome == "blocked"
    assert result.path is None
    assert result.blocked_reason is not None and ".specs" in result.blocked_reason
    assert state == before
    assert not (tmp_path / ".specs").exists()


def test_archive_before_specs_json_blocks_with_matching_reason(tmp_path: Path) -> None:
    control = tmp_path / "control"
    project = tmp_path / "target"
    control.mkdir()
    project.mkdir()
    contract_file, state_file = write_pair(control, valid_pair(project))

    result = runner.invoke(
        app,
        [
            "goal",
            "archive",
            "--contract",
            str(contract_file),
            "--state",
            str(state_file),
            "--json",
        ],
    )

    assert result.exit_code == 2
    envelope = json.loads(result.stdout)
    assert envelope["outcome"] == "blocked"
    assert envelope["reason"] in result.stderr
    assert result.stderr.count("goal archive blocked:") == 1
    assert not (project / ".specs").exists()


@pytest.mark.parametrize("runs_mode", ["absent", "existing", "contained_symlink"])
def test_archive_creates_or_reuses_contained_runs(tmp_path: Path, runs_mode: str) -> None:
    specs = tmp_path / ".specs"
    specs.mkdir()
    if runs_mode == "existing":
        (specs / ".runs").mkdir()
    elif runs_mode == "contained_symlink":
        actual_runs = specs / "contained-runs"
        actual_runs.mkdir()
        (specs / ".runs").symlink_to(actual_runs, target_is_directory=True)
    contract, state = valid_pair(tmp_path)
    before = deepcopy(state)

    result = archive_goal_run(contract, state, project_root=Path.cwd(), exit_code=0)

    assert result.outcome == "success"
    assert result.path is not None and result.path.parent == (specs / ".runs").resolve()
    assert result.path.name.startswith("spec-init-")
    assert not list((specs / ".runs").glob("*.tmp"))
    assert state == before


@pytest.mark.parametrize("target_kind", ["broken", "outside"])
def test_archive_rejects_unsafe_runs_symlink(tmp_path: Path, target_kind: str) -> None:
    project = tmp_path / "project"
    specs = project / ".specs"
    specs.mkdir(parents=True)
    outside = tmp_path / "outside"
    if target_kind == "outside":
        outside.mkdir()
        target = outside
    else:
        target = tmp_path / "missing"
    (specs / ".runs").symlink_to(target, target_is_directory=True)
    contract, state = valid_pair(project)
    before = deepcopy(state)

    result = archive_goal_run(contract, state, project_root=Path.cwd(), exit_code=0)

    assert result.outcome == "blocked"
    assert result.path is None
    assert result.blocked_reason is not None and ".runs" in result.blocked_reason
    assert state == before
    if outside.exists():
        assert not list(outside.glob("*.json"))


def test_specs_swap_before_runs_mkdir_keeps_external_trap_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    specs = project / ".specs"
    specs.mkdir(parents=True)
    outside = tmp_path / "outside"
    old_specs = outside / "old-specs"
    trap = outside / "trap"
    trap.mkdir(parents=True)
    contract, state = valid_pair(project)
    state_before = deepcopy(state)
    original_mkdir = os.mkdir
    swapped = False

    def swap_specs_then_mkdir(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal swapped
        if not swapped and Path(os.fsdecode(path)).name == ".runs":
            swapped = True
            specs.rename(old_specs)
            specs.symlink_to(trap, target_is_directory=True)
        original_mkdir(path, mode, dir_fd=dir_fd)

    monkeypatch.setattr(goal_archive_fd.os, "mkdir", swap_specs_then_mkdir)

    result = archive_goal_run(contract, state, project_root=project, exit_code=0)

    assert swapped
    assert result.outcome == "blocked"
    assert state == state_before
    assert list(trap.iterdir()) == []
    assert (old_specs / ".runs").is_dir()
    assert list((old_specs / ".runs").iterdir()) == []


def test_archive_uses_persisted_root_and_external_transcripts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "target"
    (project / ".specs").mkdir(parents=True)
    control = tmp_path / "control"
    control.mkdir()
    contract_file, state_file = write_pair(control, valid_pair(project))
    stdout_file = control / "stdout.txt"
    stderr_file = control / "stderr.txt"
    stdout_file.write_text("external stdout", encoding="utf-8")
    stderr_file.write_text("external stderr", encoding="utf-8")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    before = state_file.read_bytes()

    result = runner.invoke(
        app,
        [
            "goal",
            "archive",
            "--contract",
            str(contract_file),
            "--state",
            str(state_file),
            "--exit-code",
            "0",
            "--stdout-file",
            str(stdout_file),
            "--stderr-file",
            str(stderr_file),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    envelope = json.loads(result.stdout)
    artifact_path = Path(envelope["archived"])
    assert artifact_path.parent == (project / ".specs" / ".runs").resolve()
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["stdout"] == "external stdout"
    assert artifact["stderr"] == "external stderr"
    assert state_file.read_bytes() == before


@pytest.mark.parametrize("component", ["runs", "specs"])
def test_replaced_archive_component_cannot_redirect_write(tmp_path: Path, component: str) -> None:
    project = tmp_path / "project"
    runs = project / ".specs" / ".runs"
    runs.mkdir(parents=True)
    trusted = goal_archive_paths.resolve_goal_runs_directory(project)
    outside = tmp_path / "outside"
    outside.mkdir()
    if component == "runs":
        runs.rename(outside / "old-runs")
        trap = outside / "trap-runs"
        trap.mkdir()
        runs.symlink_to(trap, target_is_directory=True)
    else:
        specs = project / ".specs"
        specs.rename(outside / "old-specs")
        trap = outside / "trap-specs"
        (trap / ".runs").mkdir(parents=True)
        specs.symlink_to(trap, target_is_directory=True)
    with pytest.raises(goal_archive_paths.GoalArchivePathError):
        goal_archive_paths.write_goal_artifact(
            {}, "spec-init", "a" * 64, datetime.now(UTC), project, runs_dir=trusted
        )
    assert not list(outside.rglob("*.json"))
    assert not list(outside.rglob("*.tmp"))


def test_feature_mismatch_blocks_before_archive_write(tmp_path: Path) -> None:
    (tmp_path / ".specs").mkdir()
    contract, state = valid_pair(tmp_path, feature="076-x")

    result = archive_goal_run(
        contract,
        state,
        project_root=tmp_path,
        feature="other-feature",
        exit_code=0,
    )

    assert result.outcome == "blocked"
    assert result.path is None
    assert result.blocked_reason is not None and "feature" in result.blocked_reason
    assert not (tmp_path / ".specs" / ".runs").exists()


@pytest.mark.parametrize(
    ("exit_code", "pending", "outcome"),
    [(0, False, "success"), (0, True, "drift"), (1, False, "error")],
)
def test_archive_preserves_existing_outcomes(
    tmp_path: Path, exit_code: int, pending: bool, outcome: str
) -> None:
    (tmp_path / ".specs").mkdir()
    contract, state = valid_pair(tmp_path, pending=pending)

    result = archive_goal_run(contract, state, project_root=tmp_path, exit_code=exit_code)

    assert result.outcome == outcome
    assert result.path is not None and result.path.exists()
    assert result.artifact is not None
    assert json_fixture(result.artifact)["command"] == "spec-init"
    assert json_fixture(result.artifact)["goal_hash"] == contract["goal_hash"]
    assert json_fixture(result.artifact)["feature"] == contract["feature"]
    assert json_fixture(result.artifact)["verify_result"]["outcome"] == outcome
