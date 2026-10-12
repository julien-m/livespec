"""Migration v22 (conventions bootstrap) and its enforcement reference documentation."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATE_SH = REPO_ROOT / "scripts" / "migrate.sh"
MIGRATION_V22 = REPO_ROOT / "migrations" / "22" / "migrate.md"

_RECORDING_TOOL = '#!/usr/bin/env bash\nprintf \'%s\\n\' "$*" >> "{log}"\nexit {code}\n'


def _install_fake(bin_dir: Path, name: str, log: Path, exit_code: int) -> None:
    tool = bin_dir / name
    tool.write_text(_RECORDING_TOOL.format(log=log, code=exit_code), encoding="utf-8")
    tool.chmod(0o755)


def _project(root: Path, files: tuple[str, ...]) -> Path:
    (root / ".specs").mkdir(parents=True)
    (root / ".specs" / "livespec-version").write_text("21\n", encoding="utf-8")
    for relative in files:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# fixture\n", encoding="utf-8")
    return root


@pytest.mark.parametrize(
    ("files", "expected_calls"),
    [
        pytest.param((), [], id="nothing-to-bootstrap"),
        pytest.param(
            (".specs/constitution.md", ".specs/stacks/_default.md", ".conventions/manifest.yaml"),
            ["conventions gates init --force", "conventions compile --force"],
            id="fresh-project",
        ),
        pytest.param(
            (".specs/conventions-gates.yaml", ".conventions/manifest.yaml"),
            [
                "conventions compile --force",
                "conventions scaffold --apply",
                "conventions verify --report",
            ],
            id="gates-already-present",
        ),
    ],
)
def test_migration_v22_runs_advisory_conventions_steps_then_sets_version(
    tmp_path: Path, files: tuple[str, ...], expected_calls: list[str]
) -> None:
    """Each step runs only when its inputs exist; failing livespec calls never block."""
    # @spec AC-001..AC-006 — .specs/features/065-conventions-migration-docs/spec.md
    project = _project(tmp_path / "project", files)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    livespec_log = tmp_path / "livespec.log"
    livespec_log.touch()
    _install_fake(bin_dir, "livespec", livespec_log, exit_code=1)
    _install_fake(bin_dir, "cc-hub", tmp_path / "cc-hub.log", exit_code=0)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}

    result = subprocess.run(
        ["bash", str(MIGRATE_SH), str(MIGRATION_V22), str(project), str(REPO_ROOT)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert livespec_log.read_text(encoding="utf-8").splitlines() == expected_calls
    assert (project / ".specs" / "livespec-version").read_text().strip() == "22"
    assert "skill link" in (tmp_path / "cc-hub.log").read_text(encoding="utf-8")


def test_migration_v22_sets_version_only_after_every_run_step() -> None:
    """A failing RUN aborts migrate.sh before SET_VERSION, so it must come last."""
    # @spec AC-001
    instructions = [
        line.strip()
        for line in MIGRATION_V22.read_text(encoding="utf-8").splitlines()
        if line.startswith(("RUN ", "SET_VERSION "))
    ]

    assert instructions[-1] == "SET_VERSION 22"
    assert len(instructions) > 1
    assert all(instruction.startswith("RUN ") for instruction in instructions[:-1])


def test_conventions_enforcement_reference_has_required_sections() -> None:
    """AC-007..AC-011 require these sections in the enforcement reference."""
    text = (REPO_ROOT / "system" / "conventions-enforcement.md").read_text(encoding="utf-8")

    assert "## Architecture: Three Engines" in text
    assert "## Human Operations" in text
    assert "## Anti-Bypass Locks" in text
    assert "## CLI Reference" in text
    for engine in (
        "Engine A: Deterministic subprocess",
        "Engine B: Visual receipt",
        "Engine C: Layer 4 LLM review",
    ):
        assert engine in text
