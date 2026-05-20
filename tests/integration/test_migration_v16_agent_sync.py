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
    (root / ".claude" / "skills").mkdir(parents=True)
    (root / ".claude" / "rules").mkdir(parents=True)
    (root / ".agents" / "skills").mkdir(parents=True)
    (root / ".codex" / "agents").mkdir(parents=True)
    (root / ".agent-sync" / "skills").mkdir(parents=True)
    (root / ".agent-sync" / "agents").mkdir(parents=True)
    (root / ".agent-sync" / "rules").mkdir(parents=True)
    (root / ".claude" / "commands" / ("spec" + ".check.md")).symlink_to(
        "../../commands/check.md"
    )
    (root / ".agent-sync" / "skills" / "spec-init").symlink_to(
        REPO_ROOT / ".agent-sync" / "skills" / "spec-init"
    )
    (root / ".agent-sync" / "agents" / "livespec-verifier").symlink_to(
        REPO_ROOT / ".agent-sync" / "agents" / "livespec-verifier"
    )
    (root / ".agent-sync" / "rules" / "routing.md").symlink_to(
        REPO_ROOT / ".agent-sync" / "rules" / "livespec" / "routing.md"
    )
    (root / ".claude" / "skills" / "spec-init").symlink_to(
        "../../.agent-sync/skills/spec-init"
    )
    (root / ".agents" / "skills" / "spec-init").symlink_to(
        "../../.agent-sync/skills/spec-init"
    )
    (root / ".claude" / "agents" / "livespec-verifier.md").symlink_to(
        "../../.agent-sync/agents/livespec-verifier/dist/claude.md"
    )
    (root / ".codex" / "agents" / "livespec-verifier.toml").symlink_to(
        "../../.agent-sync/agents/livespec-verifier/dist/codex.toml"
    )
    (root / ".claude" / "rules" / "routing.md").symlink_to(
        "../../.agent-sync/rules/routing.md"
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
    assert ".agent-sync.local/" not in gitignore
    assert ".agents/skills/spec-*" in gitignore
    assert ".claude/skills/spec-*" in gitignore
    assert ".claude/rules/*.md" in gitignore
    assert ".claude/rules/livespec/" in gitignore
    assert ".codex/agents/livespec-*.toml" in gitignore
    legacy = project / ".claude" / "commands" / ("spec" + ".check.md")
    assert not legacy.is_symlink()
    assert not (project / ".agent-sync" / "skills" / "spec-init").exists()
    assert not (project / ".agent-sync" / "agents" / "livespec-verifier").exists()
    assert not (project / ".agent-sync" / "rules" / "routing.md").exists()
    assert not (project / ".claude" / "skills" / "spec-init").exists()
    assert not (project / ".agents" / "skills" / "spec-init").exists()
    assert not (project / ".claude" / "agents" / "livespec-verifier.md").exists()
    assert not (project / ".codex" / "agents" / "livespec-verifier.toml").exists()
    assert not (project / ".claude" / "rules" / "routing.md").exists()
    assert (project / ".agent-sync.local" / "skills" / "spec-init").is_symlink()
    assert (project / ".agent-sync.local" / "agents" / "livespec-verifier").is_symlink()
    assert (project / ".agent-sync.local" / "rules" / "routing.md").is_symlink()
    log = log_path.read_text(encoding="utf-8")
    assert "skill link" in log
    assert "agent build" in log
    assert "rule build" in log
    assert "--agent-sync-root .agent-sync.local" in log
