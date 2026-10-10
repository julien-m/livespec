"""Rendered visual fix contracts keep inspection separate from authorized mutation."""

import json
from pathlib import Path

import pytest

from validator.goal_contracts import compile_command_goal, render_goal_contract_file

ROOT = Path(__file__).parents[1]
FEATURE = "001-screen"
MUTATIONS = (
    "Apply CSS/layout",
    "Enforce theme token",
    "Re-capture",
    "visual-gate cleanup",
    "visual-gate promote",
    "Copy new Playwright",
    "Update Last Modified",
    "Baselines updated",
    "produced a PASS receipt",
)


def _rendered_tasks(root: Path, flags: str, visual: bool) -> list[dict[str, object]]:
    directory = root / ".specs/features" / FEATURE
    directory.mkdir(parents=True)
    text = "# Screen\n## Acceptance Criteria\n### AC-001\nThe screen is shown.\n"
    if visual:
        text += "## Screens\n| Screen | Route |\n|---|---|\n| Main | / |\n"
        (root / "penflow").mkdir()
    (directory / "spec.md").write_text(text)
    goal = compile_command_goal(
        "spec-fix", project_root=root, livespec_root=ROOT, feature=FEATURE, flags=flags
    )
    return json.loads(render_goal_contract_file(goal))["tasks"]


@pytest.mark.parametrize("visual", [True, False])
@pytest.mark.parametrize("flags", ["", "--dry-run", "-d", "--audit-only", "--conventions", "--all"])
def test_visual_mutation_obligations_only_apply_to_executable_repairs(
    tmp_path: Path, flags: str, visual: bool
) -> None:
    tasks = _rendered_tasks(tmp_path, flags, visual)
    descriptions = [str(task["description"]) for task in tasks]
    mutations = [text for text in descriptions if any(action in text for action in MUTATIONS)]
    assert bool(mutations) is (visual and not flags)
    if not flags and visual:
        assert any(text.startswith("Read mockup PNGs") for text in descriptions)
        assert any("Apply CSS/layout" in text for text in mutations)
        assert any("visual-gate cleanup" in text for text in mutations)
        assert any("Copy new Playwright" in text for text in mutations)


def test_visual_fix_branch_documentation_covers_all_used_tags() -> None:
    text = (ROOT / ".agent-sync/skills/spec-fix/SKILL.md").read_text()
    inventory = text.split("## Execution Tasks", 1)[1].split("### Phase 0", 1)[0]
    for branch in ("multi", "fix-conventions"):
        assert f"`{branch}`" in inventory
