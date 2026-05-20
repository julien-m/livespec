"""Integration tests for Migration 16 agent-sync installation."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATE_SH = REPO_ROOT / "scripts" / "migrate.sh"


def _fake_project(root: Path) -> Path:
    (root / ".specs").mkdir(parents=True)
    (root / ".specs" / "livespec-version").write_text("15\n", encoding="utf-8")
    (root / ".claude" / "commands").mkdir(parents=True)
    (root / ".claude" / "agents").mkdir(parents=True)
    (root / ".claude" / "commands" / ("spec" + ".check.md")).symlink_to(
        "../../commands/check.md"
    )
    return root


def _fake_cc_hub(bin_dir: Path, log_path: Path) -> None:
    bin_dir.mkdir(parents=True)
    script = bin_dir / "cc-hub"
    script.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' \"$*\" >> \"${CC_HUB_LOG}\"\n",
        encoding="utf-8",
    )
    script.chmod(0o755)


@pytest.mark.level_3a
def test_migration_v16_syncs_agent_assets_with_cc_hub(tmp_path: Path) -> None:
    project = _fake_project(tmp_path / "project")
    log_path = tmp_path / "cc-hub.log"
    bin_dir = tmp_path / "bin"
    _fake_cc_hub(bin_dir, log_path)
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["CC_HUB_LOG"] = str(log_path)

    result = subprocess.run(
        [
            "bash",
            str(MIGRATE_SH),
            str(REPO_ROOT / "migrations" / "16" / "migrate.md"),
            str(project),
            str(REPO_ROOT),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert (project / ".specs" / "livespec-version").read_text().strip() == "16"
    gitignore = (project / ".gitignore").read_text(encoding="utf-8")
    assert ".agent-sync.local/" in gitignore
    assert ".agents/skills/spec-*" in gitignore
    assert ".claude/skills/spec-*" in gitignore
    assert ".claude/rules/*.md" in gitignore
    assert ".claude/rules/livespec/" in gitignore
    assert ".codex/agents/livespec-*.toml" in gitignore
    legacy = project / ".claude" / "commands" / ("spec" + ".check.md")
    assert not legacy.is_symlink()
    log = log_path.read_text(encoding="utf-8")
    assert "skill link" in log
    assert "agent build" in log
    assert "rule build" in log
