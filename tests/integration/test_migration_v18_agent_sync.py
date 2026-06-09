"""Integration tests for Migration 18 agent-sync refresh."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATE_SH = REPO_ROOT / "scripts" / "migrate.sh"


def _fake_cc_hub(bin_dir: Path, log_path: Path) -> None:
    bin_dir.mkdir(parents=True)
    script = bin_dir / "cc-hub"
    script.write_text(
        '#!/usr/bin/env bash\nprintf \'%s\\n\' "$*" >> "${CC_HUB_LOG}"\n',
        encoding="utf-8",
    )
    script.chmod(0o755)


def _run_migration_v18(
    tmp_path: Path,
) -> tuple[Path, str, subprocess.CompletedProcess[str]]:
    project = tmp_path / "project"
    (project / ".specs").mkdir(parents=True)
    (project / ".specs" / "livespec-version").write_text("17\n", encoding="utf-8")
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
            str(REPO_ROOT / "migrations" / "18" / "migrate.md"),
            str(project),
            str(REPO_ROOT),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=env,
    )
    return project, log_path.read_text(encoding="utf-8"), result


@pytest.mark.level_3a
def test_migration_v18_refreshes_agent_assets_for_spec_doctor(tmp_path: Path) -> None:
    project, log, result = _run_migration_v18(tmp_path)

    assert result.returncode == 0, result.stderr
    assert (project / ".specs" / "livespec-version").read_text().strip() == "18"
    assert (project / ".agent-sync.local" / "skills" / "spec-doctor").is_symlink()
    assert "skill link" in log
    assert "spec-doctor" in log
    assert "agent build" in log
    assert "rule build" in log
    assert "--agent-sync-root .agent-sync.local" in log
