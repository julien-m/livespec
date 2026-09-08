"""Preserved test cases and fixtures for test_goal_contracts.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests._goal_contracts_01 import (
    EXECUTION_TASK_SKILL,
    EXPECTATIONS,
    SUBAGENT_INTERNAL_COMMAND_SKILL,
    _fixture_roots,
    _repo_root,
    _write_execution_task_skill,
    _write_internal_command_skill,
    _write_visual_feature,
)
from tests._goal_contracts_02 import _write_complete_check_fix_scenario, _write_conventions
from validator.exceptions import ExpectationsInvalid
from validator.goal_contracts import (
    compile_command_goal,
)


@pytest.mark.parametrize(
    "row",
    [
        "- [subagent] /spec-fix <feature> — missing command backticks.",
        "- subagent `/spec-fix <feature>` — missing mode brackets.",
        "- [subagent]",
    ],
)
def test_compile_command_goal_rejects_malformed_internal_invocation_bullets(
    tmp_path: Path,
    row: str,
) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_internal_command_skill(livespec_root, [row])

    with pytest.raises(ExpectationsInvalid, match="Malformed Internal Command"):
        compile_command_goal(
            "spec-demo",
            project_root=project_root,
            livespec_root=livespec_root,
            flags=[],
        )


def test_compile_command_goal_accepts_subagent_internal_spec_invocation(
    tmp_path: Path,
) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    skill_path = livespec_root / ".agent-sync" / "skills" / "spec-demo" / "SKILL.md"
    skill_path.write_text(SUBAGENT_INTERNAL_COMMAND_SKILL, encoding="utf-8")

    goal = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
        flags=[],
    )

    assert goal.payload["internal_command_invocations"] == [
        {
            "mode": "subagent",
            "command": "/spec-fix <feature>",
            "purpose": ("guard: project_root cwd .specs/spec-system.md; child goal."),
        },
        {
            "mode": "suggestion",
            "command": "/spec-plan <feature>",
            "purpose": "text-only next action.",
        },
    ]


def test_compile_command_goal_ignores_horizontal_rule_in_internal_invocations(
    tmp_path: Path,
) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    skill_path = livespec_root / ".agent-sync" / "skills" / "spec-demo" / "SKILL.md"
    skill_path.write_text(
        """\
---
name: spec-demo
description: Demo command
---

# /spec-demo

## Internal Command Invocations

- [subagent] `/spec-fix <feature>` — guard: project_root cwd .specs/spec-system.md; child goal.

---

## Definition of Done (Command-Level)

- [ ] Done
""",
        encoding="utf-8",
    )

    goal = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
        flags=[],
    )

    assert goal.payload["internal_command_invocations"] == [
        {
            "mode": "subagent",
            "command": "/spec-fix <feature>",
            "purpose": ("guard: project_root cwd .specs/spec-system.md; child goal."),
        }
    ]


@pytest.mark.parametrize(
    "command",
    [
        "spec-fix",
        "spec-implement",
        "spec-feature",
        "spec-ship",
        "spec-stack",
        "spec-refine",
        "spec-check",
        "spec-verify-output",
    ],
)
def test_compile_command_goal_accepts_updated_real_skills(
    tmp_path: Path,
    command: str,
) -> None:
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions(project_root, tmp_path / "ai")
    feature = _write_complete_check_fix_scenario(project_root)

    goal = compile_command_goal(
        command,
        project_root=project_root,
        livespec_root=_repo_root(),
        feature=feature,
        flags="--fix --all" if command == "spec-check" else "",
    )

    assert goal.command == command
    assert goal.goal_hash
    assert isinstance(goal.payload["internal_command_invocations"], list)


def test_spec_feature_execution_tasks_include_clarify_gate_before_plan(
    tmp_path: Path,
) -> None:
    """Feature A: the real /spec-feature skill renders a Clarify task before Plan.

    Invariant: the Clarify gate runs after spec review and before the Plan phase,
    so an ambiguous spec is forced to resolve questions before planning starts.
    """
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions(project_root, tmp_path / "ai")
    feature = _write_complete_check_fix_scenario(project_root)

    goal = compile_command_goal(
        "spec-feature",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature=feature,
        flags="",
    )

    assert any(
        "Run integrated Clarify gate after spec review and before plan" in task
        for task in goal.payload["execution_tasks"]
    )


def test_pre_impl_execution_task_branch_active_iff_flag_present(tmp_path: Path) -> None:
    """H1: the `pre-impl` branch is registered and activated only by --pre-impl.

    Invariant: an unregistered branch raises ValueError (command-audit failure);
    a flag-gated branch must be inert without its flag and active with it.
    """
    project_root, livespec_root = _fixture_roots(tmp_path)
    skill_path = livespec_root / ".agent-sync" / "skills" / "spec-demo" / "SKILL.md"
    skill_path.write_text(
        """\
---
name: spec-demo
description: Demo command
---

# /spec-demo

## Execution Tasks

- [always] Always task
- [pre-impl] Pre-impl analyze task

## Definition of Done (Command-Level)

- [ ] Done
""",
        encoding="utf-8",
    )

    goal_on = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
        flags="--pre-impl",
    )
    goal_off = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
        flags="",
    )

    assert "Pre-impl analyze task" in goal_on.payload["execution_tasks"]
    assert "Pre-impl analyze task" not in goal_off.payload["execution_tasks"]


def test_compile_command_goal_preserves_existing_execution_task_branches(
    tmp_path: Path,
) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_execution_task_skill(livespec_root)
    _write_visual_feature(project_root)
    (project_root / "penflow").mkdir()

    goal = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
        feature="001-visual",
        flags=[],
    )

    assert goal.payload["execution_tasks"] == [
        "Always task",
        "Visual task",
        "Penflow task",
        "Generate task",
        "Visual generate task",
        "Execute task",
    ]


def test_compile_command_goal_respects_explicit_visual_false_marker(
    tmp_path: Path,
) -> None:
    """A spec with `visual: false` front-matter never activates visual tasks.

    Invariant: the goal renderer must agree with the visual-gate P0-A table —
    a CLI-only feature documenting a `## Penflow Contract` heading would
    otherwise receive receipt-bound visual tasks it can never prove.
    """
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_execution_task_skill(livespec_root)
    feature = "002-cli-only"
    feature_dir = project_root / ".specs" / "features" / feature
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text(
        """\
---
id: 002-cli-only
visual: false
---

# CLI Feature

## Penflow Contract

| ID | Artifact |
|----|----------|
| C99 | `report.json` |
""",
        encoding="utf-8",
    )
    (project_root / "penflow").mkdir()

    goal = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
        feature=feature,
        flags=[],
    )

    assert goal.payload["runtime_context"]["is_visual_feature"] is False
    assert goal.payload["runtime_context"]["visual_feature_slugs"] == []
    assert "Visual task" not in goal.payload["execution_tasks"]
    assert "Penflow task" not in goal.payload["execution_tasks"]


def test_compile_command_goal_activates_visual_tasks_for_spec_check_all(
    tmp_path: Path,
) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    skill_dir = livespec_root / ".agent-sync" / "skills" / "spec-check"
    skill_dir.mkdir(parents=True)
    (skill_dir / "expectations.md").write_text(
        EXPECTATIONS.replace("command: spec-demo", "command: spec-check"),
        encoding="utf-8",
    )
    (skill_dir / "SKILL.md").write_text(
        EXECUTION_TASK_SKILL.replace("name: spec-demo", "name: spec-check"),
        encoding="utf-8",
    )
    _write_visual_feature(project_root, "001-visual")
    nonvisual_dir = project_root / ".specs" / "features" / "002-nonvisual"
    nonvisual_dir.mkdir(parents=True)
    (nonvisual_dir / "spec.md").write_text(
        "# Nonvisual Feature\n\n## Functional Requirements\n\n- FR-001",
        encoding="utf-8",
    )
    (project_root / "penflow").mkdir()

    goal = compile_command_goal(
        "spec-check",
        project_root=project_root,
        livespec_root=livespec_root,
        feature=None,
        flags="--all",
    )

    assert "Visual task" in goal.payload["execution_tasks"]
    assert "Penflow task" in goal.payload["execution_tasks"]


def test_compile_command_goal_activates_spec_check_fix_branch(
    tmp_path: Path,
) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_execution_task_skill(livespec_root)

    goal = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
        flags="--fix",
    )

    assert "Fix task" in goal.payload["execution_tasks"]
