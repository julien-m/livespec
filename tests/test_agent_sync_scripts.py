"""Tests for cc-hub based agent-sync scripts."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _fake_cc_hub(bin_dir: Path, log_path: Path) -> None:
    bin_dir.mkdir(parents=True)
    script = bin_dir / "cc-hub"
    script.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' \"$*\" >> \"${CC_HUB_LOG}\"\n",
        encoding="utf-8",
    )
    script.chmod(0o755)


def _env_with_fake_cc_hub(tmp_path: Path) -> tuple[dict[str, str], Path]:
    log_path = tmp_path / "cc-hub.log"
    bin_dir = tmp_path / "bin"
    _fake_cc_hub(bin_dir, log_path)
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["CC_HUB_LOG"] = str(log_path)
    return env, log_path


def test_link_local_delegates_to_cc_hub_without_manual_claude_symlinks(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env, log_path = _env_with_fake_cc_hub(tmp_path)

    result = subprocess.run(
        ["bash", "scripts/link-local.sh", str(project), str(Path.cwd())],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    log = log_path.read_text(encoding="utf-8")
    assert "skill link" in log
    assert "agent build" in log
    assert "agent link" in log
    assert "rule build" in log
    assert not (project / ".claude" / "commands").exists()
    assert not (project / ".claude" / "agents").exists()


def test_install_dry_run_reports_cc_hub_bootstrap_calls(tmp_path: Path) -> None:
    env, _log_path = _env_with_fake_cc_hub(tmp_path)

    result = subprocess.run(
        ["bash", "scripts/install.sh", "--dry-run"],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert "cc-hub skill link" in result.stdout
    assert ".agent-sync/skills/spec-init" in result.stdout
    assert ".agent-sync/skills/spec-migrate" in result.stdout
    assert "cc-hub rule" not in result.stdout


def test_migrate_agent_sync_removes_relative_legacy_command_symlinks(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    commands_dir = project / ".claude" / "commands"
    commands_dir.mkdir(parents=True)
    legacy = commands_dir / ("spec" + ".check.md")
    legacy.symlink_to("../../commands/check.md")
    env, log_path = _env_with_fake_cc_hub(tmp_path)

    result = subprocess.run(
        ["bash", "scripts/migrate-agent-sync.sh", str(project), str(Path.cwd())],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert not legacy.is_symlink()
    assert "skill link" in log_path.read_text(encoding="utf-8")
