"""Integration tests for command validation/naming migrations."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATE_SH = REPO_ROOT / "scripts" / "migrate.sh"


def _fake_project(root: Path, version: str) -> Path:
    (root / ".specs").mkdir(parents=True)
    (root / ".specs" / "livespec-version").write_text(f"{version}\n", encoding="utf-8")
    (root / ".claude" / "commands").mkdir(parents=True)
    (root / ".claude" / "agents").mkdir(parents=True)
    return root


def _run_migration(project_dir: Path, version: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "bash",
            str(MIGRATE_SH),
            str(REPO_ROOT / "migrations" / str(version) / "migrate.md"),
            str(project_dir),
            str(REPO_ROOT),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


@pytest.mark.level_3a
def test_migration_v14_refreshes_links_and_ignores_coverage(tmp_path: Path) -> None:
    project = _fake_project(tmp_path / "project", "13")

    result = _run_migration(project, 14)

    assert result.returncode == 0, result.stderr
    assert (project / ".claude" / "commands" / "spec-feature.md").is_symlink()
    assert "playground/coverage/" in (project / ".gitignore").read_text()
    assert (project / ".specs" / "livespec-version").read_text().strip() == "14"


@pytest.mark.level_3a
def test_migration_v15_creates_hyphenated_links_and_keeps_dotted_aliases(
    tmp_path: Path,
) -> None:
    project = _fake_project(tmp_path / "project", "14")

    result = _run_migration(project, 15)

    assert result.returncode == 0, result.stderr
    commands = project / ".claude" / "commands"
    assert (commands / "spec-feature.md").is_symlink()
    assert (commands / "spec.feature.md").is_symlink()
    assert (commands / "spec-check.md").is_symlink()
    assert (commands / "spec.check.md").is_symlink()
    assert (project / ".specs" / "livespec-version").read_text().strip() == "15"
