# LiveSpec traceability anchors
# @spec(AC-007)
# @spec(AC-012)

"""Integration tests for command validation/naming migrations."""

from __future__ import annotations

import os
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
    version: int,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
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
        env=env,
    )


@pytest.mark.level_3a
def test_migration_v14_refreshes_links_and_ignores_coverage(tmp_path: Path) -> None:
    project = _fake_project(tmp_path / "project", "13")
    log_path = tmp_path / "cc-hub.log"
    env = _fake_cc_hub(tmp_path / "bin", log_path)

    result = _run_migration(project, 14, env)

    assert result.returncode == 0, result.stderr
    assert "skill link" in log_path.read_text(encoding="utf-8")
    assert "playground/coverage/" in (project / ".gitignore").read_text()
    assert (project / ".specs" / "livespec-version").read_text().strip() == "14"


@pytest.mark.level_3a
def test_migration_v15_creates_hyphenated_links_and_keeps_dotted_aliases(
    tmp_path: Path,
) -> None:
    project = _fake_project(tmp_path / "project", "14")
    log_path = tmp_path / "cc-hub.log"
    env = _fake_cc_hub(tmp_path / "bin", log_path)

    result = _run_migration(project, 15, env)

    assert result.returncode == 0, result.stderr
    log = log_path.read_text(encoding="utf-8")
    assert "skill link" in log
    assert "agent build" in log
    assert (project / ".specs" / "livespec-version").read_text().strip() == "15"
