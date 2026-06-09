"""Level 3A — Integration tests for migration v13 (command expectations wiring).

Migration v13 backfills feature 039 (`/spec-verify-output` + last_reviewed
pre-commit hook) and feature 040 (expectations gitignore entries) on
pre-v13 projects:

  - Refreshes `.claude/commands/` symlinks via the patched
    `scripts/link-local.sh` (drops orphan `spec.*.expectations.md`
    entries, adds `/spec-verify-output`).
  - Installs the pre-commit hook via `scripts/install-hooks.sh`.
  - Appends `.specs/.runs/` and `.specs/.previews/` to `.gitignore`.

These tests invoke the migration end-to-end against an isolated fake
project tree to validate idempotency, orphan cleanup, and missing-
optional-component handling (no `.claude/` directory, no `.git/`).
"""

# @spec Migration v13: command expectations wiring backfill
# — migrations/13/migrate.md

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATE_SH = REPO_ROOT / "scripts" / "migrate.sh"
MIGRATION_FILE = REPO_ROOT / "migrations" / "13" / "migrate.md"
LINK_LOCAL_SH = REPO_ROOT / "scripts" / "link-local.sh"


def _fake_project(root: Path, *, with_claude: bool, with_git: bool) -> Path:
    """Build a minimal pre-v13 project tree."""
    (root / ".specs").mkdir(parents=True)
    (root / ".specs" / "livespec-version").write_text("12\n", encoding="utf-8")
    if with_claude:
        (root / ".claude" / "commands").mkdir(parents=True)
        (root / ".claude" / "agents").mkdir(parents=True)
    if with_git:
        (root / ".git" / "hooks").mkdir(parents=True)
    return root


def _fake_cc_hub(bin_dir: Path, log_path: Path) -> dict[str, str]:
    bin_dir.mkdir(parents=True)
    script = bin_dir / "cc-hub"
    script.write_text(
        '#!/usr/bin/env bash\nprintf \'%s\\n\' "$*" >> "${CC_HUB_LOG}"\n',
        encoding="utf-8",
    )
    script.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["CC_HUB_LOG"] = str(log_path)
    return env


def _run_migration(
    project_dir: Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(MIGRATE_SH), str(MIGRATION_FILE), str(project_dir), str(REPO_ROOT)],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )


@pytest.mark.level_3a
class TestMigrationV13:
    """End-to-end migration v13 against synthetic project fixtures."""

    def test_full_project_with_claude_and_git(self, tmp_path: Path) -> None:
        """Project with `.claude/` and `.git/` — every action lands."""
        project = _fake_project(tmp_path / "proj", with_claude=True, with_git=True)
        log_path = tmp_path / "cc-hub.log"
        env = _fake_cc_hub(tmp_path / "bin", log_path)

        result = _run_migration(project, env)
        assert result.returncode == 0, result.stderr

        assert "skill link" in log_path.read_text(encoding="utf-8")
        # Pre-commit hook installed.
        hook = project / ".git" / "hooks" / "pre-commit"
        assert hook.exists()
        assert "# livespec-expectations" in hook.read_text()
        assert os.access(hook, os.X_OK)
        # Gitignore entries appended.
        gitignore = (project / ".gitignore").read_text()
        assert ".specs/.runs/" in gitignore
        assert ".specs/.previews/" in gitignore
        # Version bumped.
        assert (project / ".specs" / "livespec-version").read_text().strip() == "13"

    def test_idempotent_rerun(self, tmp_path: Path) -> None:
        """Running v13 twice is a no-op on the second pass."""
        project = _fake_project(tmp_path / "proj", with_claude=True, with_git=True)
        env = _fake_cc_hub(tmp_path / "bin", tmp_path / "cc-hub.log")
        first = _run_migration(project, env)
        assert first.returncode == 0, first.stderr
        gitignore_after_first = (project / ".gitignore").read_text()

        second = _run_migration(project, env)
        assert second.returncode == 0, second.stderr
        gitignore_after_second = (project / ".gitignore").read_text()

        # Idempotent: gitignore byte-identical, no duplicate entries.
        assert gitignore_after_first == gitignore_after_second
        assert gitignore_after_second.count(".specs/.runs/") == 1
        assert gitignore_after_second.count(".specs/.previews/") == 1

    def test_no_claude_dir_skipped_silently(self, tmp_path: Path) -> None:
        """Projects without `.claude/commands/` skip the link refresh."""
        project = _fake_project(tmp_path / "proj", with_claude=False, with_git=True)
        env = _fake_cc_hub(tmp_path / "bin", tmp_path / "cc-hub.log")
        result = _run_migration(project, env)
        assert result.returncode == 0, result.stderr
        # Hook still installed.
        assert (project / ".git" / "hooks" / "pre-commit").exists()
        # Gitignore still updated.
        gitignore = (project / ".gitignore").read_text()
        assert ".specs/.runs/" in gitignore

    def test_no_git_dir_skipped_silently(self, tmp_path: Path) -> None:
        """Projects without `.git/` skip the pre-commit hook install."""
        project = _fake_project(tmp_path / "proj", with_claude=True, with_git=False)
        env = _fake_cc_hub(tmp_path / "bin", tmp_path / "cc-hub.log")
        result = _run_migration(project, env)
        assert result.returncode == 0, result.stderr
        # No hook attempted.
        assert not (project / ".git").exists()
        # Gitignore + version still updated.
        gitignore = (project / ".gitignore").read_text()
        assert ".specs/.previews/" in gitignore
        assert (project / ".specs" / "livespec-version").read_text().strip() == "13"


@pytest.mark.level_3a
class TestLinkLocalFilter:
    """`link-local.sh` must skip `*.expectations.md` and clean orphans."""

    def test_expectations_files_are_not_linked(self, tmp_path: Path) -> None:
        project = _fake_project(tmp_path / "proj", with_claude=True, with_git=False)
        env = _fake_cc_hub(tmp_path / "bin", tmp_path / "cc-hub.log")
        result = subprocess.run(
            ["bash", str(LINK_LOCAL_SH), str(project), str(REPO_ROOT)],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        assert result.returncode == 0, result.stderr
        assert not (project / ".claude" / "commands" / "spec.verify-output.md").exists()

    def test_legacy_orphan_symlinks_are_not_recreated_by_agent_sync(self, tmp_path: Path) -> None:
        project = _fake_project(tmp_path / "proj", with_claude=True, with_git=False)
        orphan = project / ".claude" / "commands" / "spec.feature.expectations.md"
        orphan.symlink_to(REPO_ROOT / ".agent-sync" / "skills" / "spec-feature" / "expectations.md")
        assert orphan.is_symlink()
        env = _fake_cc_hub(tmp_path / "bin", tmp_path / "cc-hub.log")

        result = subprocess.run(
            ["bash", str(LINK_LOCAL_SH), str(project), str(REPO_ROOT)],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        assert result.returncode == 0, result.stderr
        assert orphan.is_symlink()
