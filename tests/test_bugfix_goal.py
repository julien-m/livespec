"""spec-fix goal inventory with and without --bugfix, and outcome:passed proof (084 AC-013)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.bugfix_support import FEATURE, FIXED, TEST, make_project
from validator.cli import app
from validator.evidence_policy import (
    _execution_missing,  # pyright: ignore[reportPrivateUsage]
)

ROOT = Path(__file__).resolve().parents[1]


def _canonical(flags: str) -> dict[str, list[object]]:
    result = CliRunner().invoke(
        app,
        ["goal", "render", "spec-fix", "--feature", "084-bugfix-lane", "--flags", flags, "--json"],
    )
    assert result.exit_code == 0, result.output
    return json.loads(result.output)["canonical"]


def _tasks(flags: str) -> list[dict[str, object]]:
    return [task for task in _canonical(flags)["tasks"] if isinstance(task, dict)]


def _descriptions(flags: str) -> list[str]:
    """Return every active inventory row: proof tasks, checklist and definition of done."""
    canonical = _canonical(flags)
    rows = [str(task.get("description", "")) for task in _tasks(flags)]
    return rows + [
        str(row) for row in (*canonical["execution_tasks"], *canonical["definition_of_done"])
    ]


def test_bugfix_goal_replaces_readiness_gap_report_and_feature_acceptance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(ROOT)
    bugfix = _descriptions("--auto --bugfix")
    normal = _descriptions("--auto")

    def has(rows: list[str], text: str) -> bool:
        return any(text in row for row in rows)

    for text in ("livespec bugfix capture", "livespec bugfix gate", "livespec bugfix record"):
        assert has(bugfix, text) and not has(normal, text)
    for text in (
        "--progression implement --model",
        "Overwrite today's gap report",
        "Complete feature acceptance verified",
        "save gap report if missing or stale",
    ):
        assert has(normal, text) and not has(bugfix, text)


def test_visual_fix_never_uses_the_lane(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)
    rows = _descriptions("--auto --bugfix --visual")
    assert any("--progression implement --model" in row for row in rows)
    assert not any("livespec bugfix gate" in row for row in rows)


def test_green_capture_is_the_only_bugfix_execution_proof(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)
    execution = [t for t in _tasks("--auto --bugfix") if t.get("evidence_kind") == "execution"]
    assert [t.get("evidence_expected_outcome") for t in execution] == ["passed"]


def test_outcome_passed_accepts_current_green_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = make_project(tmp_path)
    project.write("tests/test_calc.py", TEST)
    monkeypatch.chdir(project.root)
    _, red = project.capture("red")
    project.write("calc.py", FIXED)
    _, green = project.capture("green")
    task: dict[str, object] = {"evidence_expected_outcome": "passed"}

    assert _execution_missing(task, Path(green), project.root, FEATURE, policy="2") == []
    assert _execution_missing(task, Path(red), project.root, FEATURE, policy="2") != []
