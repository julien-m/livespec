"""Validation policy is reachable from the actual planning and execution workflows."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _links(path: Path) -> set[Path]:
    """Resolve local Markdown contract references exactly as the skill reader does."""
    return {
        (path.parent / target.split("#", 1)[0]).resolve()
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text())
        if not target.startswith(("http:", "https:"))
    }


# @spec AC-005: Reachable proportional validation and recovery policy
# — .specs/features/095-test-time-budgets/spec.md#ac-005
def test_plan_and_execution_workflows_reach_the_same_budget_contract() -> None:
    policy = ROOT / "system/testing/execution-rules.md"
    scope = ROOT / "system/minimal-spec-scope.md"
    workflows = [
        ROOT / f".agent-sync/skills/{name}/SKILL.md"
        for name in ("spec-plan", "spec-test", "spec-implement")
    ]
    assert all({policy, scope} <= _links(path) for path in workflows)
    assert policy in _links(scope)
    assert policy in _links(ROOT / "system/anti-drift-block.md")
    assert scope in _links(ROOT / "system/review-protocol.md")
