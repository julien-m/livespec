"""The compiled test inventory preserves global, project and overriding local hooks."""

from pathlib import Path

import pytest

from validator.goal_contracts import compile_command_goal


@pytest.mark.parametrize("local_mode", ["extend", "override"])
def test_test_contract_names_each_hook_level_and_resolves_the_actual_chain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, local_mode: str
) -> None:
    global_hooks = tmp_path / "global-hooks"
    project_hooks = tmp_path / ".specs/hooks"
    global_hooks.mkdir()
    project_hooks.mkdir(parents=True)
    (global_hooks / "before-test.md").write_text("Global test preparation\n")
    (project_hooks / "before-test.md").write_text("Project test preparation\n")
    (project_hooks / "before-test.local.md").write_text(
        f"---\nmode: {local_mode}\n---\nLocal test preparation\n"
    )
    feature = tmp_path / ".specs/features/001-hooks"
    feature.mkdir(parents=True)
    (feature / "spec.md").write_text("# Hooks\n## Acceptance Criteria\n### AC-001\nRun hooks.\n")
    monkeypatch.setattr("validator.hook_resolver.GLOBAL_HOOKS_DIR", global_hooks)
    monkeypatch.setattr("validator.integrations.INTEGRATIONS_DIR", tmp_path / "no-integrations")
    goal = compile_command_goal(
        "spec-test",
        project_root=tmp_path,
        livespec_root=Path(__file__).resolve().parents[1],
        feature=feature.name,
        flags="--audit-only --model=reviewer/v1",
    )
    row = next(
        task["description"]
        for task in goal.payload["tasks"]
        if "Read before-test hooks" in task["description"]
    )
    assert "~/.claude/livespec/hooks/before-test.md" in row
    assert row.count("](../../../.specs/hooks/before-test.md)") == 1
    assert "](../../../.specs/hooks/before-test.local.md)" in row
    context = goal.payload["hooks"]["before"]["context"]
    assert "Local test preparation" in context
    assert ("Global test preparation" in context) is (local_mode == "extend")
    assert ("Project test preparation" in context) is (local_mode == "extend")
