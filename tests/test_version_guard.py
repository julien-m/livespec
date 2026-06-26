# @spec(AC-005)
# @spec(AC-014)

"""Tests for the blocking LiveSpec migration guard."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.cli import app
from validator.version_guard import (
    ProjectMigrationRequiredError,
    enforce_project_migrated,
    find_project_for_guard,
)


def _write_project(root: Path, version: int | None, *, with_spec_system: bool = True) -> Path:
    specs = root / ".specs"
    specs.mkdir(parents=True, exist_ok=True)
    if version is not None:
        (specs / "livespec-version").write_text(f"{version}\n", encoding="utf-8")
    if with_spec_system:
        (specs / "spec-system.md").write_text("# LiveSpec System\n", encoding="utf-8")
    return root


def _write_livespec_repo(root: Path, version: int) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "VERSION").write_text(f"{version}\n", encoding="utf-8")
    return root


def test_guard_blocks_stale_project_with_actionable_message(tmp_path: Path) -> None:
    project = _write_project(tmp_path / "project", 10)
    livespec = _write_livespec_repo(tmp_path / "livespec", 21)

    try:
        enforce_project_migrated(["status", "--project", str(project)], livespec_root=livespec)
    except ProjectMigrationRequiredError as exc:
        message = str(exc)
    else:
        raise AssertionError("stale project was not blocked")

    assert "LiveSpec project is not migrated" in message
    assert "Project version: v10" in message
    assert "Required version: v21" in message
    assert "Run /spec-migrate or livespec migrate" in message


def test_guard_allows_up_to_date_project(tmp_path: Path) -> None:
    project = _write_project(tmp_path / "project", 21)
    livespec = _write_livespec_repo(tmp_path / "livespec", 21)

    enforce_project_migrated(["status", "--project", str(project)], livespec_root=livespec)


def test_guard_treats_missing_version_as_v1_for_initialized_project(tmp_path: Path) -> None:
    project = _write_project(tmp_path / "project", None)
    livespec = _write_livespec_repo(tmp_path / "livespec", 21)

    try:
        enforce_project_migrated(["doctor", "--project", str(project)], livespec_root=livespec)
    except ProjectMigrationRequiredError as exc:
        assert "Project version: v1" in str(exc)
    else:
        raise AssertionError("project without livespec-version was not blocked")


def test_guard_allows_internal_migration_runner(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project = _write_project(tmp_path / "project", 10)
    livespec = _write_livespec_repo(tmp_path / "livespec", 21)
    monkeypatch.setenv("LIVESPEC_MIGRATION_IN_PROGRESS", "1")
    monkeypatch.setenv("LIVESPEC_MIGRATION_PROJECT", str(project.resolve()))
    monkeypatch.setenv("LIVESPEC_MIGRATION_LIVESPEC", str(livespec.resolve()))

    enforce_project_migrated(["journey", "compile", "--force"], cwd=project, livespec_root=livespec)


def test_guard_rejects_unscoped_migration_bypass(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project = _write_project(tmp_path / "project", 10)
    livespec = _write_livespec_repo(tmp_path / "livespec", 21)
    monkeypatch.setenv("LIVESPEC_MIGRATION_IN_PROGRESS", "1")

    with pytest.raises(ProjectMigrationRequiredError):
        enforce_project_migrated(
            ["journey", "compile", "--force"],
            cwd=project,
            livespec_root=livespec,
        )


def test_guard_ignores_uninitialized_minimal_specs_fixture(tmp_path: Path) -> None:
    project = _write_project(tmp_path / "project", None, with_spec_system=False)
    livespec = _write_livespec_repo(tmp_path / "livespec", 21)

    enforce_project_migrated(["drivers", "--project", str(project)], livespec_root=livespec)


def test_guard_resolves_explicit_project_over_current_directory(tmp_path: Path) -> None:
    current = _write_project(tmp_path / "current", 21)
    target = _write_project(tmp_path / "target", 10)

    assert (
        find_project_for_guard(["visual-gate", "validate", "--project", str(target)], cwd=current)
        == target.resolve()
    )


def test_cli_blocks_stale_explicit_project_over_current_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    current = _write_project(tmp_path / "current", 21)
    target = _write_project(tmp_path / "target", 10)
    monkeypatch.chdir(current)
    monkeypatch.setattr(
        sys,
        "argv",
        ["livespec", "status", "--repo", str(target), "--json"],
    )

    result = CliRunner().invoke(app, ["status", "--repo", str(target), "--json"])

    assert result.exit_code == 1
    assert "Project version: v10" in result.output


def test_cli_blocks_stale_project_before_command_execution(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project = _write_project(tmp_path / "project", 10)
    runner = CliRunner()
    monkeypatch.chdir(project)

    result = runner.invoke(app, ["status", "--json"])

    assert result.exit_code == 1
    assert "LiveSpec project is not migrated" in result.output
    assert "Run /spec-migrate or livespec migrate" in result.output


def test_cli_allows_migrate_on_stale_project(tmp_path: Path) -> None:
    project = _write_project(tmp_path / "project", 10)
    repo = tmp_path / "repo"
    (repo / "migrations" / "11").mkdir(parents=True)
    (repo / "VERSION").write_text("11\n", encoding="utf-8")
    (repo / "migrations" / "11" / "migrate.md").write_text(
        "---\nversion: 11\n---\n\nSET_VERSION 11\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        ["migrate", "plan", "--project", str(project), "--livespec", str(repo), "--json"],
    )

    assert result.exit_code == 0, result.output


def test_cli_allows_goal_render_for_spec_migrate_on_stale_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project = _write_project(tmp_path / "project", 20)
    monkeypatch.chdir(project)
    monkeypatch.setattr(
        sys,
        "argv",
        ["livespec", "goal", "render", "spec-migrate", "--flags", "", "--save"],
    )

    result = CliRunner().invoke(
        app,
        ["goal", "render", "spec-migrate", "--flags", "", "--save"],
    )

    assert result.exit_code == 0, result.output
    assert "contract-file:" in result.output
    assert "state-file:" in result.output


def test_cli_blocks_other_goal_render_on_stale_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project = _write_project(tmp_path / "project", 20)
    monkeypatch.chdir(project)
    monkeypatch.setattr(
        sys,
        "argv",
        ["livespec", "goal", "render", "status", "--save"],
    )

    result = CliRunner().invoke(app, ["goal", "render", "status", "--save"])

    assert result.exit_code == 1
    assert "LiveSpec project is not migrated" in result.output


def test_cli_help_is_not_blocked_for_stale_project(tmp_path: Path) -> None:
    project = _write_project(tmp_path / "project", 10)

    result = CliRunner().invoke(app, ["status", "--repo", str(project), "--help"])

    assert result.exit_code == 0
    assert "Usage" in result.output
