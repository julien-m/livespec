"""Integration tests for User Journeys v2 migration refreshes."""

from __future__ import annotations

import json
import os
import subprocess
from hashlib import sha256
from pathlib import Path

import pytest

from tests.test_journey_v2_validation import _write_feature, _write_v2_journey
from validator.journeys.manifest import COMPILER_VERSION

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


def _run_migration(
    tmp_path: Path,
    *,
    from_version: str,
    to_version: str,
    with_journey: bool = False,
) -> tuple[Path, str, subprocess.CompletedProcess[str]]:
    project = tmp_path / "project"
    (project / ".specs").mkdir(parents=True)
    (project / ".specs" / "livespec-version").write_text(f"{from_version}\n", encoding="utf-8")
    if with_journey:
        _write_feature(project / ".specs", "001-onboarding")
        _write_feature(project / ".specs", "012-projects")
        source = _write_v2_journey(project / ".specs")
        source_hash = sha256(source.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
        compiled_dir = source.parent / "compiled"
        compiled_dir.mkdir()
        (compiled_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "compiler_version": "journeys-v2-1",
                    "journey_id": "onboarding-first-project",
                    "native_output_paths": [],
                    "runner": "playwright",
                    "schema_version": 1,
                    "source_hash": source_hash,
                    "source_path": ".specs/journeys/onboarding-first-project/journey.yaml",
                    "visual_contract_paths": [],
                }
            ),
            encoding="utf-8",
        )
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
            str(REPO_ROOT / "migrations" / to_version / "migrate.md"),
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
def test_migration_v19_refreshes_agent_assets_for_spec_journey(tmp_path: Path) -> None:
    project, log, result = _run_migration(tmp_path, from_version="18", to_version="19")

    assert result.returncode == 0, result.stderr
    assert (project / ".specs" / "livespec-version").read_text().strip() == "19"
    assert (project / ".agent-sync.local" / "skills" / "spec-journey").is_symlink()
    assert "skill link" in log
    assert "spec-journey" in log
    assert "agent build" in log
    assert "rule build" in log
    assert "--agent-sync-root .agent-sync.local" in log


@pytest.mark.level_3a
def test_migration_v20_refreshes_assets_after_native_runner_fix(tmp_path: Path) -> None:
    project, log, result = _run_migration(
        tmp_path,
        from_version="19",
        to_version="20",
        with_journey=True,
    )

    assert result.returncode == 0, result.stderr
    assert (project / ".specs" / "livespec-version").read_text().strip() == "20"
    assert (project / ".agent-sync.local" / "skills" / "spec-journey").is_symlink()
    manifest = json.loads(
        (
            project
            / ".specs"
            / "journeys"
            / "onboarding-first-project"
            / "compiled"
            / "manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["compiler_version"] == COMPILER_VERSION
    assert manifest["native_output_paths"] == [
        "tests/e2e/journeys/onboarding_first_project.spec.ts"
    ]
    assert (project / "tests" / "e2e" / "journeys" / "onboarding_first_project.spec.ts").exists()
    assert "RUN migrate-journeys-compile.sh" in result.stdout
    assert "journey compile · OK · compiled=1 · errors=0" in result.stdout
    assert "spec-journey" in log
    assert "--agent-sync-root .agent-sync.local" in log
