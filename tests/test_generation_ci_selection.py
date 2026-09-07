"""Exercise the actual CI selector with a controlled git-diff transport."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


@pytest.mark.parametrize(
    ("changed_path", "mode", "runtimes", "selected"),
    [
        ("validator/llm_provider.py", "full", "claude codex", "true"),
        (".codex/config.toml", "full", "claude codex", "true"),
        ("tests/integration/helpers/sdk_runner.py", "full", "claude codex", "true"),
        ("validator/semantic/plan_review.py", "sample", "claude", "true"),
        ("README.md", "none", "claude codex", "false"),
    ],
)
def test_pull_request_selector_covers_full_runtimes_and_bounds_sample(
    tmp_path: Path, changed_path: str, mode: str, runtimes: str, selected: str
) -> None:
    output = _execute_selection(tmp_path, "pull_request", changed_path)
    assert output == {"selected": selected, "mode": mode, "runtimes": runtimes}


def test_manual_selector_preserves_explicit_runtime_request(tmp_path: Path) -> None:
    output = _execute_selection(tmp_path, "workflow_dispatch", "", "codex")
    assert output == {"selected": "true", "mode": "full", "runtimes": "codex"}


def _execute_selection(
    tmp_path: Path, event: str, changed_path: str, runtimes: str = ""
) -> dict[str, str]:
    repo = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((repo / ".github/workflows/ci.yml").read_text())
    step = next(row for row in workflow["jobs"]["generation-selection"]["steps"] if "id" in row)
    git = tmp_path / "git"
    git.write_text(f"#!{sys.executable}\nprint({changed_path!r})\n")
    git.chmod(0o755)
    output = tmp_path / "output"
    environment = dict(
        os.environ,
        PATH=f"{tmp_path}:{Path(sys.executable).parent}:{os.environ['PATH']}",
        EVENT=event,
        BASE_SHA="controlled-base",
        HEAD_SHA="controlled-head",
        REQUEST_MODE="",
        REQUEST_RUNTIMES=runtimes,
        GITHUB_OUTPUT=str(output),
    )
    # Execute the shipped shell/Python selector; only git's changed-path response is controlled.
    result = subprocess.run(
        ["bash", "-c", step["run"]],
        cwd=repo,
        env=environment,
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    return dict(line.split("=", 1) for line in output.read_text().splitlines())
