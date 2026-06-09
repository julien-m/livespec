# LiveSpec traceability anchors
# @spec(AC-002)
# @spec(AC-004)
# @spec(AC-005)
# @spec(AC-006)
# @spec(FR-010)

"""Tests for hyphenated command skill aliases."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _fake_cc_hub(bin_dir: Path, log_path: Path) -> None:
    bin_dir.mkdir(parents=True)
    script = bin_dir / "cc-hub"
    script.write_text(
        '#!/usr/bin/env bash\nprintf \'%s\\n\' "$*" >> "${CC_HUB_LOG}"\n',
        encoding="utf-8",
    )
    script.chmod(0o755)


def _env_with_fake_cc_hub(tmp_path: Path) -> tuple[dict[str, str], Path]:
    log_path = tmp_path / "cc-hub.log"
    _fake_cc_hub(tmp_path / "bin", log_path)
    env = os.environ.copy()
    env["PATH"] = f"{tmp_path / 'bin'}:{env['PATH']}"
    env["CC_HUB_LOG"] = str(log_path)
    return env, log_path


def test_link_local_creates_hyphenated_and_dotted_command_links(tmp_path: Path) -> None:
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
    assert "spec-feature" in log


def test_installer_dry_run_mentions_hyphenated_bootstrap_aliases() -> None:
    result = subprocess.run(
        ["bash", "scripts/install.sh", "--dry-run"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "cc-hub skill link" in result.stdout
    assert ".agent-sync/skills/spec-init" in result.stdout
    assert ".agent-sync/skills/spec-migrate" in result.stdout
    assert "cc-hub rule" not in result.stdout
