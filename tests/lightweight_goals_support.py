"""Saved-goal helpers shared by the feature 081 recompilation tests."""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from validator.cli import app

_REPO_ROOT = Path(__file__).resolve().parents[1]


def render_saved(runner: CliRunner) -> tuple[Path, Path]:
    """Render and save the demo spec-test goal, returning its contract and state paths."""
    result = runner.invoke(
        app,
        ["goal", "render", "spec-test", "--feature", "demo", "--flags", "--auto", "--save"],
    )
    assert result.exit_code == 0, result.output
    match = re.search(r"contract-file:(\S+) \| state-file:(\S+)", result.output)
    assert match is not None
    return Path(match.group(1)), Path(match.group(2))


def isolate_saved_goals(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> CliRunner:
    """Pin the project version, redirect saved goals and global hooks, and enter the project."""
    (project / ".specs/livespec-version").write_text((_REPO_ROOT / "VERSION").read_text())
    controls = tmp_path / "controls"
    controls.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(controls))
    monkeypatch.setattr("validator.integrations.INTEGRATIONS_DIR", tmp_path / "none")
    monkeypatch.setattr("validator.hook_resolver.GLOBAL_HOOKS_DIR", tmp_path / "none")
    monkeypatch.chdir(project)
    return CliRunner()


def summarize_recompile(
    first: dict[str, Any],  # parsed JSON goal contract before drift
    output: dict[str, Any],  # parsed JSON report of the drifted proof
    paths: tuple[Path, Path, Path, Path],
) -> dict[str, object]:
    """Summarize an in-place recompilation and the adoption by a later re-render."""
    contract_path, state_path, new_contract_path, new_state_path = paths
    rewritten = json.loads(contract_path.read_text())
    state = json.loads(state_path.read_text())
    adopted = json.loads(new_state_path.read_text())
    return {
        "from_hash": output["recompiled"]["from_hash"] == first["goal_hash"],
        "carried": output["recompiled"]["carried"],
        "rewritten_in_place": rewritten["goal_hash"] == output["recompiled"]["to_hash"],
        "state_hash": state["goal_hash"] == rewritten["goal_hash"],
        "hook_task_added": rewritten["tasks"][0]["id"],
        "qe_status": state["tasks"]["qe.analysis"]["status"],
        "outcome_status": state["tasks"]["outcome.verified"]["status"],
        "recompiled_from": state["recompiled_from"] == first["goal_hash"],
        "rerender_new_paths": new_contract_path != contract_path,
        "rerender_adopts_qe": adopted["tasks"]["qe.analysis"]["status"],
    }
