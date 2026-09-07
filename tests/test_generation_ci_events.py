"""CI event selection runs the shipped selector; routine checks stay independent of paid runs."""

# @spec AC-013: CI event and routine selection
# ../.specs/features/078-requirement-evidence-integrity/spec.md#ac-013

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]


def _workflow() -> dict[str, Any]:
    """Load current workflow declarations without interpreting YAML's on key as a boolean."""
    return yaml.load((REPO / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)


def _select(
    tmp_path: Path, event: str, *, mode: str = "", runtimes: str = ""
) -> tuple[int, dict[str, str]]:
    """Execute the shipped shell body; only Git's changed-path response is controlled."""
    step = next(row for row in _workflow()["jobs"]["generation-selection"]["steps"] if "id" in row)
    git = tmp_path / "git"
    git.write_text(f"#!{sys.executable}\nprint('README.md')\n")
    git.chmod(0o755)
    output = tmp_path / "output"
    environment = dict(
        os.environ,
        PATH=f"{tmp_path}:{Path(sys.executable).parent}:{os.environ['PATH']}",
        EVENT=event,
        BASE_SHA="controlled-base",
        HEAD_SHA="controlled-head",
        REQUEST_MODE=mode,
        REQUEST_RUNTIMES=runtimes,
        GITHUB_OUTPUT=str(output),
        PYTHONDONTWRITEBYTECODE="1",
    )
    # No model or CI runner is invoked: execute the existing selector with local event fixtures.
    result = subprocess.run(
        ["bash", "-c", step["run"]],
        cwd=REPO,
        env=environment,
        text=True,
        capture_output=True,
        timeout=20,
    )
    values = dict(line.split("=", 1) for line in output.read_text().splitlines())
    return result.returncode, values


@pytest.mark.parametrize(
    ("event", "mode", "runtimes", "expected_mode", "expected_runtimes"),
    [
        pytest.param("release", "", "", "full", "claude codex", id="release"),
        pytest.param("workflow_dispatch", "", "", "full", "claude codex", id="manual-default"),
        pytest.param("workflow_dispatch", "sample", "codex", "sample", "codex", id="manual-sample"),
    ],
)
def test_registered_events_select_real_full_or_requested_corpus(
    tmp_path: Path,
    event: str,
    mode: str,
    runtimes: str,
    expected_mode: str,
    expected_runtimes: str,
) -> None:
    workflow = _workflow()
    assert event in workflow["on"]
    if event == "release":
        assert workflow["on"]["release"]["types"] == ["published"]
    result = _select(tmp_path, event, mode=mode, runtimes=runtimes)
    assert result == (
        0,
        {
            "selected": "true",
            "mode": expected_mode,
            "runtimes": expected_runtimes,
        },
    )


@pytest.mark.parametrize("job_name", ["unit-tests", "integration-3a"])
def test_docs_only_pull_request_keeps_deterministic_jobs_without_model_selection(
    tmp_path: Path,
    job_name: str,
) -> None:
    workflow = _workflow()
    assert workflow["on"]["pull_request"]["branches"] == ["main"]
    assert _select(tmp_path, "pull_request") == (
        0,
        {
            "selected": "false",
            "mode": "none",
            "runtimes": "claude codex",
        },
    )
    job = workflow["jobs"][job_name]
    assert "if" not in job and not job.get("needs")
    commands = [shlex.split(step["run"]) for step in job["steps"] if "run" in step]
    if job_name == "unit-tests":
        assert any(
            command[:2] == ["pytest", "tests/"] and "--ignore=tests/integration" in command
            for command in commands
        )
    else:
        assert any(
            command[:4] == ["pytest", "tests/integration/", "-m", "level_3a"]
            for command in commands
        )
