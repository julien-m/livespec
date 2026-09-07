"""Rendered test goals require visual closure only when visual tests execute."""

import json
from pathlib import Path
from typing import Any

import pytest

from validator.goal_contracts import compile_command_goal
from validator.goal_render import render_goal_contract_file

REPO = Path(__file__).resolve().parents[1]
VISUAL_DOD = (
    "Visual baselines captured",
    "`baselines/baseline.manifest.yml` written",
    "For VISUAL features: every validation PNG",
    "For VISUAL features: `livespec visual-gate certify",
)
PREVIEW_MODES = (
    "--dry-run",
    "--audit-only",
    "--regenerate-missing",
    "--regenerate-missing --confirm",
    "--regenerate-missing --confirm --dry-run",
)


def _render(tmp_path: Path, flags: str, *, visual: bool = True) -> dict[str, Any]:
    feature = tmp_path / ".specs/features/001-example"
    feature.mkdir(parents=True, exist_ok=True)
    spec = (
        "# Example\n## Header\n- Status: Implemented\n## Acceptance Criteria\n### AC-001\nWorks.\n"
    )
    if visual:
        spec += (
            "## Screens\n| Screen | Route | Mockup |\n"
            "| --- | --- | --- |\n| home | / | home.png |\n"
        )
    (feature / "spec.md").write_text(spec)
    (tmp_path / "penflow").mkdir(exist_ok=True)
    goal = compile_command_goal(
        "spec-test",
        project_root=tmp_path,
        livespec_root=REPO,
        feature=feature.name,
        flags=f"{flags} --model=reviewer/v1",
    )
    return json.loads(render_goal_contract_file(goal))


@pytest.mark.parametrize("flags", (*PREVIEW_MODES, "--no-visual"))
@pytest.mark.parametrize("description", VISUAL_DOD)
def test_preview_does_not_require_visual_completion(
    tmp_path: Path, flags: str, description: str
) -> None:
    contract = _render(tmp_path, flags)
    assert not any(task["description"].startswith(description) for task in contract["tasks"])


@pytest.mark.parametrize("flags", ("", "--no-generate", "--all"))
def test_each_selected_visual_feature_keeps_actual_visual_closure(
    tmp_path: Path, flags: str
) -> None:
    contract = _render(tmp_path, flags)
    tasks = contract["tasks"]
    for description in VISUAL_DOD:
        assert any(task["description"].startswith(description) for task in tasks)
    assert any(task["description"].startswith("4.5.2 Baseline capture") for task in tasks)
    assert any(task["description"].startswith("4.5.P Web runtime") for task in tasks)


@pytest.mark.parametrize("flags", ("", "--no-generate", "--all", *PREVIEW_MODES))
def test_non_visual_feature_has_no_visual_closure(tmp_path: Path, flags: str) -> None:
    contract = _render(tmp_path, flags, visual=False)
    assert not any(task["id"].startswith("visual.") for task in contract["tasks"])
    for description in VISUAL_DOD:
        assert not any(task["description"].startswith(description) for task in contract["tasks"])


@pytest.mark.parametrize("flags", PREVIEW_MODES)
def test_preview_already_excludes_visual_execution_tasks(tmp_path: Path, flags: str) -> None:
    contract = _render(tmp_path, flags)
    tasks = contract["tasks"]
    assert not any(task["description"].startswith("4.5.") for task in tasks)
    generates = flags == "--regenerate-missing --confirm"
    assert any(task["description"].startswith("Write tests:") for task in tasks) is generates
