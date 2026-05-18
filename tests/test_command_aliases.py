"""Tests for hyphenated slash command aliases."""

from __future__ import annotations

import subprocess
from pathlib import Path


def test_link_local_creates_hyphenated_and_dotted_command_links(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    result = subprocess.run(
        ["bash", "scripts/link-local.sh", str(project), str(Path.cwd())],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (project / ".claude" / "commands" / "spec-feature.md").is_symlink()
    assert (project / ".claude" / "commands" / "spec.feature.md").is_symlink()
    assert (project / ".claude" / "commands" / "spec-verify-output.md").is_symlink()
    assert (project / ".claude" / "commands" / "spec.verify-output.md").is_symlink()


def test_installer_dry_run_mentions_hyphenated_bootstrap_aliases() -> None:
    result = subprocess.run(
        ["bash", "scripts/install.sh", "--dry-run"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "commands/spec-init.md" in result.stdout
    assert "commands/spec.init.md" in result.stdout
    assert "commands/spec-migrate.md" in result.stdout
    assert "commands/spec.migrate.md" in result.stdout
