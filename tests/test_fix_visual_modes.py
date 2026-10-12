"""Rendered visual fix contracts keep inspection separate from authorized mutation."""

import json
import re
from pathlib import Path

import pytest

from tests.goal_checklist_support import checklist_tasks
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
    return checklist_tasks(json.loads(render_goal_contract_file(goal)))


# Non-visual features never get visual mutations, so preview flags are only exercised on
# visual features, where they are the sole reason mutations disappear.
@pytest.mark.parametrize(
    ("flags", "visual"),
    [
        ("", True),
        ("", False),
        ("--dry-run", True),
        ("-d", True),
        ("--audit-only", True),
        ("--conventions", True),
        ("--all", True),
    ],
)
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
    inventory = text.split("## Execution Tasks", 1)[1].split("\n## ", 1)[0]
    legend = inventory.split("### Phase 0", 1)[0]
    # Every branch tag used by an inventory row must be explained in the legend above it.
    used = set(re.findall(r"^- \[([a-z][a-z-]*)\] ", inventory, flags=re.MULTILINE))
    assert {"multi", "fix-conventions"} <= used
    assert {tag for tag in used if f"`{tag}`" not in legend} == set()
