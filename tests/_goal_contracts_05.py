"""Preserved test cases and fixtures for test_goal_contracts.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests._goal_contracts_01 import (
    INLINE_INTERNAL_COMMAND_SKILL,
    _fixture_roots,
    _write_execution_task_skill,
    _write_internal_command_skill,
)
from tests._goal_contracts_02 import _write_complete_check_fix_scenario, _write_conventions
from validator.cli import app
from validator.exceptions import ExpectationsInvalid
from validator.goal_contracts import (
    compile_command_goal,
    prove_goal_task,
    render_goal_contract_file,
    render_goal_state_file,
)


def test_compile_command_goal_extracts_definition_of_done(tmp_path: Path) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)

    goal = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
        feature="001-demo",
        flags=[],
    )

    assert goal.payload["definition_of_done"] == [
        "`demo.txt` exists",
        "Output contains `done`",
        "No traceback was emitted",
    ]
    assert goal.payload["expectations"]["source_path"].endswith(
        ".agent-sync/skills/spec-demo/expectations.md"
    )


def test_render_goal_contract_and_state_replace_markdown_task_file(
    tmp_path: Path,
) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_execution_task_skill(livespec_root)

    goal = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
        feature="001-demo",
        flags="--strict",
    )

    contract_text = render_goal_contract_file(goal)
    contract = json.loads(contract_text)
    state = json.loads(render_goal_state_file(goal))

    assert contract["schema_version"] == "2.0"
    assert contract["goal_hash"] == goal.goal_hash
    assert contract["mode"] == "enforced"
    assert contract["worker_may_mark_tasks_complete"] is False
    assert contract["rules"]["worker_may_mark_tasks_complete"] is False
    assert contract["rules"]["completion_actor"] == "goal"
    assert contract["rules"]["proof_required_for_each_task"] is True
    assert all(task["required_evidence"] for task in contract["tasks"])
    assert all(task["repair_if_missing"] for task in contract["tasks"])
    assert "task-file" not in contract_text
    assert "Check each task" not in contract_text

    assert state["schema_version"] == "2.0"
    assert state["goal_hash"] == goal.goal_hash
    assert state["status"] == "active"
    assert set(state["tasks"]) == {task["id"] for task in contract["tasks"]}
    assert all(task["status"] == "pending" for task in state["tasks"].values())


def test_goal_prove_rejects_generic_output_when_required_evidence_missing(
    tmp_path: Path,
) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_execution_task_skill(livespec_root)
    goal = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))
    task_id = contract["tasks"][0]["id"]

    result = prove_goal_task(
        contract,
        state,
        task_id,
        evidence={"output": "done"},
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "success_criteria_met" in result["missing_evidence"]


def test_goal_render_save_writes_contract_and_state_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    version = (Path(__file__).resolve().parents[1] / "VERSION").read_text(encoding="utf-8")
    (project_root / ".specs" / "livespec-version").write_text(version, encoding="utf-8")
    _write_conventions(project_root, tmp_path / "ai")
    _write_complete_check_fix_scenario(project_root)
    monkeypatch.chdir(project_root)

    result = CliRunner().invoke(
        app,
        ["goal", "render", "spec-check", "--flags=--all --fix", "--save"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "task-file:" not in result.output
    assert "contract-file:" in result.output
    assert "state-file:" in result.output

    parts = dict(
        item.strip().split(":", 1) for item in result.output.strip().split("|") if ":" in item
    )
    contract_path = Path(parts["contract-file"])
    state_path = Path(parts["state-file"])
    assert contract_path.suffix == ".json"
    assert state_path.suffix == ".json"
    assert contract_path.exists()
    assert state_path.exists()
    assert json.loads(contract_path.read_text(encoding="utf-8"))["mode"] == "enforced"
    assert json.loads(state_path.read_text(encoding="utf-8"))["status"] == "active"


def test_compile_command_goal_accepts_documented_execution_task_branches(
    tmp_path: Path,
) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_execution_task_skill(livespec_root)

    goal = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
        flags="--visual-status",
    )

    assert "Visual status task" in goal.payload["execution_tasks"]


def test_compile_command_goal_ignores_markdown_checkboxes_inside_execution_tasks(
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

## Execution Tasks

- [always] Machine task

### Exit Criteria

- [ ] Human checklist item
- [x] Completed documentary checklist item

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

    assert goal.payload["execution_tasks"] == ["Machine task"]


def test_compile_command_goal_activates_spec_check_flag_branches(
    tmp_path: Path,
) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_execution_task_skill(livespec_root)

    expected_by_flags = {
        "--all": "Multi task",
        "--surfaces": "Surfaces task",
        "--quality": "Quality task",
        "--tree-only": "Tree task",
        "--visual-status": "Visual status task",
    }

    for flags, expected_task in expected_by_flags.items():
        goal = compile_command_goal(
            "spec-demo",
            project_root=project_root,
            livespec_root=livespec_root,
            flags=flags,
        )
        assert expected_task in goal.payload["execution_tasks"]


def test_compile_command_goal_rejects_inline_internal_spec_invocation(
    tmp_path: Path,
) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    skill_path = livespec_root / ".agent-sync" / "skills" / "spec-demo" / "SKILL.md"
    skill_path.write_text(INLINE_INTERNAL_COMMAND_SKILL, encoding="utf-8")

    with pytest.raises(ExpectationsInvalid, match="must use mode subagent"):
        compile_command_goal(
            "spec-demo",
            project_root=project_root,
            livespec_root=livespec_root,
            flags=[],
        )


@pytest.mark.parametrize(
    "mode",
    ["direct", "cli", "api", "unknown", "Subagent"],
)
def test_compile_command_goal_rejects_any_unknown_internal_invocation_mode(
    tmp_path: Path,
    mode: str,
) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_internal_command_skill(
        livespec_root,
        [f"- [{mode}] `/spec-fix <feature>` — forbidden nested execution."],
    )

    with pytest.raises(ExpectationsInvalid, match="must use mode subagent"):
        compile_command_goal(
            "spec-demo",
            project_root=project_root,
            livespec_root=livespec_root,
            flags=[],
        )


@pytest.mark.parametrize("mode", ["cli", "api"])
def test_compile_command_goal_rejects_cli_api_fallback_for_non_spec_command(
    tmp_path: Path,
    mode: str,
) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_internal_command_skill(
        livespec_root,
        [f"- [{mode}] `livespec internal fix <feature>` — forbidden fallback."],
    )

    with pytest.raises(ExpectationsInvalid, match="must use mode subagent"):
        compile_command_goal(
            "spec-demo",
            project_root=project_root,
            livespec_root=livespec_root,
            flags=[],
        )


def test_compile_command_goal_rejects_subagent_non_spec_fallback(
    tmp_path: Path,
) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_internal_command_skill(
        livespec_root,
        ["- [subagent] `livespec internal fix <feature>` — forbidden fallback."],
    )

    with pytest.raises(ExpectationsInvalid, match="subagent rows must execute /spec"):
        compile_command_goal(
            "spec-demo",
            project_root=project_root,
            livespec_root=livespec_root,
            flags=[],
        )


def test_compile_command_goal_rejects_subagent_without_project_root_cwd_guard(
    tmp_path: Path,
) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_internal_command_skill(
        livespec_root,
        [
            "- [subagent] `/spec-fix <feature>` — executable nested command with child goal.",
        ],
    )

    with pytest.raises(ExpectationsInvalid, match=r"project_root.*cwd"):
        compile_command_goal(
            "spec-demo",
            project_root=project_root,
            livespec_root=livespec_root,
            flags=[],
        )


def test_compile_command_goal_rejects_executable_spec_invocation_without_section(
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

Run `/spec-fix <feature>` before returning.

## Definition of Done (Command-Level)

- [ ] Done
""",
        encoding="utf-8",
    )

    with pytest.raises(ExpectationsInvalid, match="requires ## Internal Command"):
        compile_command_goal(
            "spec-demo",
            project_root=project_root,
            livespec_root=livespec_root,
            flags=[],
        )


def test_compile_command_goal_ignores_documentary_and_self_spec_invocations(
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

## Overview

```
/spec-demo --all          -> run all demo phases
```

- If `.specs/` does not exist, show: "Run `/spec-init` first."
- Next useful action: suggest `/spec-plan <feature>`.
**Lifecycle placement:** `/spec-demo` is typically run after `/spec-init`.
Users can re-run `/spec-preflight` later after fixing blockers.

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

    assert goal.payload["internal_command_invocations"] == []
