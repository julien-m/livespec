"""Tests for metadata-aware LiveSpec migration planning."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.cli import app
from validator.migration_planner import MigrationPlannerError, build_migration_plan

RUNNER = CliRunner()


def _write_project(root: Path, version: int) -> Path:
    (root / ".specs").mkdir(parents=True)
    (root / ".specs" / "livespec-version").write_text(f"{version}\n", encoding="utf-8")
    return root


def _write_repo(root: Path, target: int, migrations: dict[int, str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "VERSION").write_text(f"{target}\n", encoding="utf-8")
    for version, frontmatter in migrations.items():
        migration_dir = root / "migrations" / str(version)
        migration_dir.mkdir(parents=True, exist_ok=True)
        migration_dir.joinpath("migrate.md").write_text(
            f"---\nversion: {version}\n{frontmatter}---\n\nSET_VERSION {version}\n",
            encoding="utf-8",
        )
    return root


def test_linear_plan_is_unchanged_without_metadata(tmp_path: Path) -> None:
    project = _write_project(tmp_path / "project", 10)
    repo = _write_repo(tmp_path / "repo", 12, {11: "", 12: ""})

    plan = build_migration_plan(project, repo)

    assert plan.project_version == 10
    assert plan.target_version == 12
    assert plan.apply == [11, 12]
    assert plan.skipped == []
    assert plan.invalid_restore_points == []


def test_replaces_when_unapplied_skips_pending_old_migration(tmp_path: Path) -> None:
    project = _write_project(tmp_path / "project", 2)
    repo = _write_repo(
        tmp_path / "repo",
        17,
        {
            3: "",
            4: "",
            17: "replaces_when_unapplied: [3]\n",
        },
    )

    plan = build_migration_plan(project, repo)

    assert 3 not in plan.apply
    assert plan.apply == [4, 17]
    assert plan.skipped == [{"version": 3, "reason": "superseded_by_17"}]


def test_already_applied_replaced_migration_is_not_removed(tmp_path: Path) -> None:
    project = _write_project(tmp_path / "project", 3)
    repo = _write_repo(
        tmp_path / "repo",
        17,
        {
            3: "",
            4: "",
            17: "replaces_when_unapplied: [3]\n",
        },
    )

    plan = build_migration_plan(project, repo)

    assert plan.apply == [4, 17]
    assert plan.skipped == []


def test_invalid_restore_points_are_reported(tmp_path: Path) -> None:
    project = _write_project(tmp_path / "project", 16)
    repo = _write_repo(
        tmp_path / "repo",
        17,
        {17: "invalidates_restore_points: [3]\n"},
    )

    plan = build_migration_plan(project, repo)

    assert plan.invalid_restore_points == [3]


def test_invalid_frontmatter_reference_fails_clearly(tmp_path: Path) -> None:
    project = _write_project(tmp_path / "project", 1)
    repo = _write_repo(
        tmp_path / "repo",
        2,
        {2: "replaces_when_unapplied: [old]\n"},
    )

    with pytest.raises(MigrationPlannerError, match="replaces_when_unapplied"):
        build_migration_plan(project, repo)


def test_migrate_plan_cli_outputs_json(tmp_path: Path) -> None:
    project = _write_project(tmp_path / "project", 10)
    repo = _write_repo(tmp_path / "repo", 12, {11: "", 12: ""})

    result = RUNNER.invoke(
        app,
        [
            "migrate",
            "plan",
            "--project",
            str(project),
            "--livespec",
            str(repo),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload == {
        "project_version": 10,
        "target_version": 12,
        "apply": [11, 12],
        "skipped": [],
        "invalid_restore_points": [],
    }
