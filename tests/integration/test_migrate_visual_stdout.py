"""Exercise the migration sentinel through a real pipe with a stalled reader."""

from __future__ import annotations

import shutil
import subprocess
from contextlib import suppress
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "migrate-visual"
SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "migrate-visual-tests.js"


def _project_with_large_scan(tmp_path: Path, already_covered: bool) -> Path:
    project = tmp_path / "project"
    shutil.copytree(FIXTURE, project)
    # Exceed ordinary pipe buffers without introducing additional UI work.
    for index in range(2000):
        feature = project / ".specs" / "features" / f"{index + 100:04}-server"
        feature.mkdir()
        (feature / "spec.md").write_text("# Backend service\nServer storage.\n")
    if already_covered:
        for feature_slug in ("001-auth-ui", "003-dashboard"):
            (project / "tests" / "visual" / f"{feature_slug}.spec.ts").write_text(
                "// Existing test must remain intact.\n"
            )
    return project


def _run_with_stalled_reader(project: Path) -> subprocess.CompletedProcess[str]:
    # Hold the pipe unread while waiting for producer exit; a full pipe must
    # keep a successful producer alive until communicate starts draining it.
    process = subprocess.Popen(
        ["node", str(SCRIPT), "--generate"],
        cwd=project,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        # Backpressure is intentional, not a readiness delay or a failure.
        with suppress(subprocess.TimeoutExpired):
            process.wait(timeout=1)
        stdout, stderr = process.communicate(timeout=30)
        return subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=5)


@pytest.mark.level_3a
@pytest.mark.parametrize("already_covered", [False, True], ids=["generated", "covered"])
def test_generation_drains_pipe_before_success(tmp_path: Path, already_covered: bool) -> None:
    """Keep the complete machine-readable result even when its reader stalls."""
    # @spec FR-006: Structured result survives pipe backpressure — feature 011.
    project = _project_with_large_scan(tmp_path, already_covered)
    result = _run_with_stalled_reader(project)
    assert result.returncode == 0, result.stderr
    expected = "files=0 dirs=0" if already_covered else "files=2 dirs=12"
    assert result.stdout.splitlines()[-1] == f"VISUAL_SCAFFOLD_RESULT: {expected} routes=0"
    assert result.stdout.count("VISUAL_SCAFFOLD_RESULT:") == 1
    assert "2099-server" in result.stdout
