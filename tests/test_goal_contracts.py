"""Tests for deterministic command goal contracts.

# @spec FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-013, FR-014, FR-015, FR-019
#   — .specs/features/052-deterministic-command-goal-contracts/spec.md
"""

from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.cli import app
from validator.exceptions import ExpectationsInvalid
from validator.goal_contracts import (
    compile_command_goal,
    normalize_goal_flags,
    prove_goal_task,
    render_goal_contract_file,
    render_goal_objective,
    render_goal_state_file,
)

EXPECTATIONS = """\
---
command: spec-demo
contract_version: "1.0"
last_reviewed: 2026-05-21
---

# Expectations — /spec-demo

## 1. Purpose

Demo command.

## 2. Preconditions

- `.specs/project.md` exists.

## 3. Observable Signals

- "done"

## 4. Filesystem Effects

- creates demo.txt.

## 5. Git Effects

- none.

## 6. Produced Artifacts

- demo.txt.

## 7. Exit Codes

| Code | Meaning |
|------|---------|
| 0 | success |

## 8. Outcome Matrix

- success.

## 9. Runtime Profile

- <1s.

## 10. Post-run Checks

- [ ] output checked.

## 11. Troubleshooting

- rerun.

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "done"
  must_not:
    - contains: "Traceback"
  when:
    - flag: "--strict"
      must:
        - exists: "demo.txt"
```

## 13. Demo Session

### Live Console Output

```
$ /spec-demo
> done
```
- line a
- line b
- line c

### Files Produced

- demo.txt
- report.md
- summary.md

### Aligned / Drift / Missing

- aligned: done.
- drift: marker missing.
- missing: no artifact.

### Runtime Profile

- cold: <1s.
- warm: <1s.
- worst: 2s.

### Edge Cases

- missing file: blocked.
- bad output: drift.
- crash: error.

### Post-run Actions

- success: continue.
- drift: inspect output.
- blocked: restore artifact.
"""


def _write_png(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width = 4
    height = 4
    row = bytes((*color, 255)) * width
    raw = b"".join(b"\x00" + row for _ in range(height))
    payload = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(raw))
        + _png_chunk(b"IEND", b"")
    )
    path.write_bytes(payload)


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )


SKILL = """\
---
name: spec-demo
description: Demo command
---

# /spec-demo

## Definition of Done (Command-Level)

`/spec-demo` is complete only if all are true:

- [ ] `demo.txt` exists
- [ ] Output contains `done`
- [ ] No traceback was emitted

If any item fails, fix before returning final output.
"""

EXECUTION_TASK_SKILL = """\
---
name: spec-demo
description: Demo command
---

# /spec-demo

## Execution Tasks

- [always] Always task
- [visual] Visual task
- [penflow] Penflow task
- [generate] Generate task
- [visual-generate] Visual generate task
- [execute] Execute task
- [surfaces] Surfaces task
- [quality-only] Quality task
- [tree-only] Tree task
- [visual-status] Visual status task
- [multi] Multi task
- [fix] Fix task

## Definition of Done (Command-Level)

- [ ] Done
"""

INLINE_INTERNAL_COMMAND_SKILL = """\
---
name: spec-demo
description: Demo command
---

# /spec-demo

## Internal Command Invocations

- [inline] `/spec-fix <feature>` — forbidden nested execution.

## Definition of Done (Command-Level)

- [ ] Done
"""

SUBAGENT_INTERNAL_COMMAND_SKILL = """\
---
name: spec-demo
description: Demo command
---

# /spec-demo

## Internal Command Invocations

- [subagent] `/spec-fix <feature>` — guard: project_root cwd .specs/spec-system.md; child goal.
- [suggestion] `/spec-plan <feature>` — text-only next action.

## Definition of Done (Command-Level)

- [ ] Done
"""


def _fixture_roots(tmp_path: Path) -> tuple[Path, Path]:
    project_root = tmp_path / "project"
    livespec_root = tmp_path / "livespec"
    (project_root / ".specs").mkdir(parents=True)
    skill_dir = livespec_root / ".agent-sync" / "skills" / "spec-demo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "expectations.md").write_text(EXPECTATIONS, encoding="utf-8")
    (skill_dir / "SKILL.md").write_text(SKILL, encoding="utf-8")
    return project_root, livespec_root


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _write_execution_task_skill(livespec_root: Path) -> None:
    skill_path = livespec_root / ".agent-sync" / "skills" / "spec-demo" / "SKILL.md"
    skill_path.write_text(EXECUTION_TASK_SKILL, encoding="utf-8")


def _write_internal_command_skill(livespec_root: Path, rows: list[str]) -> None:
    skill_path = livespec_root / ".agent-sync" / "skills" / "spec-demo" / "SKILL.md"
    skill_path.write_text(
        f"""\
---
name: spec-demo
description: Demo command
---

# /spec-demo

## Internal Command Invocations

{chr(10).join(rows)}

## Definition of Done (Command-Level)

- [ ] Done
""",
        encoding="utf-8",
    )


def _write_visual_feature(project_root: Path, feature: str = "001-visual") -> None:
    feature_dir = project_root / ".specs" / "features" / feature
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text(
        "# Visual Feature\n\n## Screens\n\n- Home screen",
        encoding="utf-8",
    )


def _write_complete_check_fix_scenario(project_root: Path) -> str:
    feature = "001-visual-check-fix"
    feature_dir = project_root / ".specs" / "features" / feature
    feature_dir.mkdir(parents=True)
    for path in (
        project_root / ".specs" / "stacks",
        project_root / ".specs" / "testing",
        project_root / ".specs" / "design" / "screens" / feature,
        project_root / ".specs" / "design" / "baselines" / feature,
        project_root / "penflow",
        project_root / "src",
        project_root / "tests",
        feature_dir / "checks",
        feature_dir / "baselines",
    ):
        path.mkdir(parents=True, exist_ok=True)
    (project_root / ".specs" / "spec-system.md").write_text("# System\n", encoding="utf-8")
    (project_root / ".specs" / "constitution.md").write_text("# Constitution\n", encoding="utf-8")
    (project_root / ".specs" / "project.md").write_text("# Project\n", encoding="utf-8")
    (project_root / ".specs" / "README.md").write_text("# Registry\n", encoding="utf-8")
    (project_root / ".specs" / "changelog.md").write_text("# Changelog\n", encoding="utf-8")
    (project_root / ".specs" / "stacks" / "_default.md").write_text("# Stack\n", encoding="utf-8")
    (project_root / ".specs" / "testing" / "strategy.md").write_text(
        "# Testing\n",
        encoding="utf-8",
    )
    (feature_dir / "spec.md").write_text(
        """\
# Visual Check Fix

Status: Implemented

## Screens

- Dashboard: `.specs/design/screens/001-visual-check-fix/dashboard.png`

## Penflow Contract

- Target: web-desktop

## Acceptance Criteria

- AC-001: Dashboard renders current count.
- AC-002: Dashboard has matching visual baseline.

## Functional Requirements

- FR-001: Render count mapped to AC-001.
- FR-002: Preserve design fidelity mapped to AC-002.
""",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        """\
# Plan

## Testing Strategy

- Run `pytest tests/test_dashboard.py`.
""",
        encoding="utf-8",
    )
    (feature_dir / "implementation.md").write_text(
        """\
# Implementation

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | src/dashboard.py | @spec FR-001 | ✅ Implemented | 2026-05-22 |
| FR-002 | missing | missing | ❌ Missing | 2026-05-22 |

| AC | Test File | Status |
|---|---|---|
| AC-001 | tests/test_dashboard.py | ✅ Implemented |
| AC-002 | missing | ❌ Missing |
""",
        encoding="utf-8",
    )
    (feature_dir / "progress.md").write_text(
        "# Progress\n- [x] Implemented initial count\n",
        encoding="utf-8",
    )
    (feature_dir / "changelog.md").write_text("# Changelog\n", encoding="utf-8")
    (feature_dir / "checks" / "2026-05-22.md").write_text(
        """\
# Gap Report

## Findings

- tree/spec quality: README status stale.
- FR/AC mapping: FR-002 missing anchor.
- tests: AC-002 missing visual assertion.
- visual fidelity: dashboard drift 8.2%.
- baseline manifest: stale browser version.
- Penflow: compare-report status FAIL.
- changelog/report: feature changelog missing fix entry.
""",
        encoding="utf-8",
    )
    (project_root / "src" / "dashboard.py").write_text(
        """\
def render_count(count: int) -> str:
    # @spec FR-001: Render count — .specs/features/001-visual-check-fix/spec.md#fr-001
    return f"Count: {count}"
""",
        encoding="utf-8",
    )
    (project_root / "tests" / "test_dashboard.py").write_text(
        """\
from src.dashboard import render_count


def test_render_count() -> None:
    assert render_count(2) == "Count: 2"
""",
        encoding="utf-8",
    )
    for image_path in (
        project_root / ".specs" / "design" / "screens" / feature / "dashboard.png",
        project_root / ".specs" / "design" / "baselines" / feature / "dashboard.png",
        feature_dir / "baselines" / "dashboard.png",
    ):
        image_path.write_bytes(b"\x89PNG\r\n\x1a\n")
    (project_root / ".specs" / "design" / "ui.pen").write_text("penflow ui", encoding="utf-8")
    (project_root / ".specs" / "design" / "screens" / "index.md").write_text(
        "# Screens\n- 001-visual-check-fix/dashboard.png\n",
        encoding="utf-8",
    )
    (project_root / ".specs" / "design" / "changelog.md").write_text(
        "# Design Changelog\n",
        encoding="utf-8",
    )
    (feature_dir / "baselines" / "baseline.manifest.yml").write_text(
        """\
browser: chromium-120
mockups:
  dashboard.png: stale-sha
""",
        encoding="utf-8",
    )
    (project_root / "penflow" / "expected-ui-tree.json").write_text(
        '{"screen":"dashboard"}',
        encoding="utf-8",
    )
    (project_root / "penflow" / "actual-ui-tree.json").write_text(
        '{"screen":"dashboard","drift":true}',
        encoding="utf-8",
    )
    (project_root / "penflow" / "compare-report.json").write_text(
        '{"status":"FAIL","issues":[{"id":"layout"}]}',
        encoding="utf-8",
    )
    (project_root / "penflow" / "review-report.md").write_text(
        "# Review\n- drift\n",
        encoding="utf-8",
    )
    (project_root / "penflow" / "fix-report.md").write_text(
        "# Fix\n- adjust layout\n",
        encoding="utf-8",
    )
    return feature


def _write_conventions(project_root: Path, ai_root: Path) -> None:
    conventions = project_root / ".conventions"
    conventions.mkdir()
    (conventions / "index.md").write_text(
        f"""\
# Conventions · fixture

> `$AIRESOURCES` = `{ai_root.as_posix()}`

## code [code, tests, logging, naming, imports, architecture]
→ $AIRESOURCES/code-conventions/general.md, python.md

## design-tokens [CSS, colors, spacing, typography, mockup, UI, visual]
→ $AIRESOURCES/design/tokens.md
""",
        encoding="utf-8",
    )
    (ai_root / "code-conventions").mkdir(parents=True)
    (ai_root / "design").mkdir(parents=True)
    (ai_root / "code-conventions" / "general.md").write_text(
        "# General\n- Prefer explicit typed APIs.\n",
        encoding="utf-8",
    )
    (ai_root / "code-conventions" / "python.md").write_text(
        "# Python\n- Use pytest for tests.\n",
        encoding="utf-8",
    )
    (ai_root / "design" / "tokens.md").write_text(
        "# Tokens\n- Use spacing tokens for mockups.\n",
        encoding="utf-8",
    )


def _command_definition_of_done(skill_path: Path) -> list[str]:
    text = skill_path.read_text(encoding="utf-8")
    section = text.split("## Definition of Done (Command-Level)", 1)[1]
    section = section.split("\n## ", 1)[0]
    return [
        line.removeprefix("- [ ]").strip()
        for line in section.splitlines()
        if line.strip().startswith("- [ ]")
    ]


def test_normalize_goal_flags_is_order_independent_and_preserves_values() -> None:
    assert normalize_goal_flags("--strict --priority P1 --auto") == [
        "--auto",
        "--priority=P1",
        "--strict",
    ]
    assert normalize_goal_flags(["--priority=P1", "--auto", "--strict"]) == [
        "--auto",
        "--priority=P1",
        "--strict",
    ]


def test_compile_command_goal_is_reproducible_for_same_inputs(tmp_path: Path) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)

    rendered = [
        compile_command_goal(
            "demo",
            project_root=project_root,
            livespec_root=livespec_root,
            feature="052-deterministic-command-goal-contracts",
            flags="--strict --priority P1 --auto",
        )
        for _ in range(10)
    ]

    first = rendered[0]
    assert all(goal.canonical_json == first.canonical_json for goal in rendered)
    assert all(goal.goal_hash == first.goal_hash for goal in rendered)
    assert first.payload["normalized_flags"] == [
        "--auto",
        "--priority=P1",
        "--strict",
    ]
    assert first.payload["expectation_sections"]["filesystem_effects"] == ["- creates demo.txt."]
    assert first.payload["expectation_sections"]["post_run_checks"] == ["- [ ] output checked."]
    assert "timestamp" not in first.canonical_json.lower()


def test_compile_command_goal_embeds_code_convention_domains(tmp_path: Path) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_conventions(project_root, tmp_path / "ai")

    goal = compile_command_goal(
        "demo",
        project_root=project_root,
        livespec_root=livespec_root,
        feature="001-demo",
        flags="--strict",
    )

    conventions = goal.payload["conventions"]
    assert conventions["index_path"] == ".conventions/index.md"
    assert [domain["name"] for domain in conventions["selected_domains"]] == ["code"]
    assert conventions["selected_domains"][0]["source_files"] == [
        {
            "path": "$AIRESOURCES/code-conventions/general.md",
            "sha256": conventions["selected_domains"][0]["source_files"][0]["sha256"],
            "content": "# General\n- Prefer explicit typed APIs.",
        },
        {
            "path": "$AIRESOURCES/code-conventions/python.md",
            "sha256": conventions["selected_domains"][0]["source_files"][1]["sha256"],
            "content": "# Python\n- Use pytest for tests.",
        },
    ]


def test_compile_command_goal_adds_design_domain_for_ui_feature(tmp_path: Path) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_conventions(project_root, tmp_path / "ai")
    feature_dir = project_root / ".specs" / "features" / "002-ui"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text(
        "# UI Feature\n\nBuild a mockup-driven visual screen with spacing tokens.",
        encoding="utf-8",
    )

    goal = compile_command_goal(
        "demo",
        project_root=project_root,
        livespec_root=livespec_root,
        feature="002-ui",
        flags="--visual",
    )

    selected = goal.payload["conventions"]["selected_domains"]
    assert [domain["name"] for domain in selected] == ["code", "design-tokens"]
    assert "design-tokens" in goal.objective
    assert "$AIRESOURCES/design/tokens.md" in goal.objective


def test_rendered_goal_tasks_replay_required_conventions(tmp_path: Path) -> None:
    """AC-001/AC-002/AC-007/AC-008: tasks replay convention domains and sources."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_conventions(project_root, tmp_path / "ai")
    _write_execution_task_skill(livespec_root)

    goal = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
        feature="001-demo",
        flags=[],
    )
    contract = json.loads(render_goal_contract_file(goal))

    first_task = contract["tasks"][0]
    assert first_task["required_conventions"] == {
        "mode": "read_apply",
        "domains": ["code"],
        "source_paths": [
            "$AIRESOURCES/code-conventions/general.md",
            "$AIRESOURCES/code-conventions/python.md",
        ],
    }
    assert "convention_domains_recorded" in first_task["required_evidence"]
    assert "convention_sources_read" in first_task["required_evidence"]
    assert "conventions_applied_to_output" in first_task["required_evidence"]
    assert any("Read and apply conventions" in action for action in first_task["repair_if_missing"])
    assert "Task-level convention replay:" in goal.objective
    assert "task.001.always_task" in goal.objective


def test_goal_prove_rejects_missing_convention_evidence(tmp_path: Path) -> None:
    """AC-003/AC-004/AC-005: convention-scoped tasks require convention proof."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_conventions(project_root, tmp_path / "ai")
    _write_execution_task_skill(livespec_root)
    goal = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))
    task_id = contract["tasks"][0]["id"]

    result = prove_goal_task(
        contract,
        state,
        task_id,
        evidence={"output": "done", "success_criteria_met": True},
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert result["missing_evidence"] == [
        "convention_domains_recorded",
        "convention_sources_read",
        "conventions_applied_to_output",
    ]


def test_goal_prove_accepts_matching_convention_evidence(tmp_path: Path) -> None:
    """AC-006: matching convention evidence satisfies convention-scoped tasks."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_conventions(project_root, tmp_path / "ai")
    _write_execution_task_skill(livespec_root)
    goal = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))
    task_id = contract["tasks"][0]["id"]

    result = prove_goal_task(
        contract,
        state,
        task_id,
        evidence={
            "output": "done",
            "success_criteria_met": True,
            "convention_domains": ["code"],
            "convention_sources": [
                "$AIRESOURCES/code-conventions/general.md",
                "$AIRESOURCES/code-conventions/python.md",
            ],
            "conventions_applied_to_output": True,
        },
        project_root=project_root,
    )

    assert result["status"] == "ACCEPTED"
    assert result["state"]["tasks"][task_id]["status"] == "complete"


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


def test_spec_check_fix_all_complete_scenario_goal_requires_child_goals(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "complete-project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions(project_root, tmp_path / "ai")
    feature = _write_complete_check_fix_scenario(project_root)

    goal = compile_command_goal(
        "spec-check",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature=None,
        flags="--fix --all",
    )
    tasks = goal.payload["execution_tasks"]
    contract = json.loads(render_goal_contract_file(goal))
    task_descriptions = [task["description"] for task in contract["tasks"]]

    assert goal.payload["runtime_context"]["is_visual_feature"] is True
    assert goal.payload["runtime_context"]["has_penflow"] is True
    assert goal.payload["runtime_context"]["visual_feature_slugs"] == [feature]
    assert any("tree/spec quality" in task for task in tasks)
    assert any("FR/AC mapping" in task for task in tasks)
    assert any("missing or blocked tests" in task for task in tasks)
    assert any("visual fidelity" in task for task in tasks)
    assert any("absent or stale baseline manifests" in task for task in tasks)
    assert any("Penflow drift" in task for task in tasks)
    assert any("changelog/report drift" in task for task in tasks)
    assert any("README sync" in task for task in tasks)
    assert any("Create missing visual/Penflow prerequisites" in task for task in tasks)
    assert any("Spawn independent native sub-agent to execute `/spec-fix" in task for task in tasks)
    assert any(
        "Spawn independent native sub-agent to re-run `/spec-check" in task for task in tasks
    )
    assert any("Inspect child goal state files" in task for task in tasks)
    assert any("canonical BLOCKED" in task for task in tasks)
    assert any("/spec-fix <feature> --auto --update" in task for task in task_descriptions)
    assert any("/spec-check <feature>" in task for task in task_descriptions)
    assert any(task["id"] == "visual.design_fidelity" for task in contract["tasks"])
    assert feature in (project_root / ".specs" / "design" / "screens" / "index.md").read_text(
        encoding="utf-8"
    )
    assert (project_root / "penflow" / "compare-report.json").exists()
    assert (
        project_root / ".specs" / "features" / feature / "baselines" / "baseline.manifest.yml"
    ).exists()


def test_spec_fix_child_spec_check_goal_cannot_be_skipped_with_zero_gap_report(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "complete-project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions(project_root, tmp_path / "ai")
    feature = _write_complete_check_fix_scenario(project_root)
    report_path = project_root / ".specs" / "features" / feature / "checks" / "2026-06-03.md"
    report_path.write_text(
        "# Spec Fix Report\n\nNo Feature gaps remain after verification.\n",
        encoding="utf-8",
    )
    goal = compile_command_goal(
        "spec-fix",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature=feature,
        flags="--auto --update",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))
    child_tasks = [
        task
        for task in contract["tasks"]
        if str(task["id"]).startswith("fix.child_goal.spec_check")
    ]
    assert child_tasks

    evidence = {
        "child_goal_skipped": True,
        "skip_reason": "zero_gap_report",
        "report_path": report_path.relative_to(project_root).as_posix(),
        "convention_domains": ["code", "design-tokens"],
        "convention_sources": [
            "$AIRESOURCES/code-conventions/general.md",
            "$AIRESOURCES/code-conventions/python.md",
            "$AIRESOURCES/design/tokens.md",
        ],
        "conventions_applied_to_output": True,
    }
    result = prove_goal_task(
        contract,
        state,
        str(child_tasks[0]["id"]),
        evidence,
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "child_goal_hash_recorded" in result["missing_evidence"]
    assert "child_contract_file_exists" in result["missing_evidence"]
    assert "child_state_file_exists" in result["missing_evidence"]
    assert "child_final_status_recorded" in result["missing_evidence"]


def test_spec_fix_child_spec_check_skip_requires_zero_gap_report(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "complete-project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions(project_root, tmp_path / "ai")
    feature = _write_complete_check_fix_scenario(project_root)
    report_path = project_root / ".specs" / "features" / feature / "checks" / "2026-06-03.md"
    report_path.write_text(
        "# Spec Fix Report\n\n- FR/AC mapping: one gap remains.\n",
        encoding="utf-8",
    )
    goal = compile_command_goal(
        "spec-fix",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature=feature,
        flags="--auto --update",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))
    child_task = next(
        task
        for task in contract["tasks"]
        if str(task["id"]).startswith("fix.child_goal.spec_check")
    )

    result = prove_goal_task(
        contract,
        state,
        str(child_task["id"]),
        {
            "child_goal_skipped": True,
            "skip_reason": "zero_gap_report",
            "report_path": report_path.relative_to(project_root).as_posix(),
            "convention_domains": ["code", "design-tokens"],
            "convention_sources": [
                "$AIRESOURCES/code-conventions/general.md",
                "$AIRESOURCES/code-conventions/python.md",
                "$AIRESOURCES/design/tokens.md",
            ],
            "conventions_applied_to_output": True,
        },
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "child_goal_hash_recorded" in result["missing_evidence"]


def test_child_goal_contract_and_state_paths_may_use_goal_artifacts_outside_project(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions(project_root, tmp_path / "ai")
    feature = _write_complete_check_fix_scenario(project_root)
    child_hash = "abc12345"
    child_dir = tmp_path / "livespec-goals"
    child_dir.mkdir()
    child_contract = child_dir / "goal-spec-check-abc12345.contract.json"
    child_state = child_dir / "goal-spec-check-abc12345.state.json"
    child_contract.write_text(
        json.dumps({"goal_hash": child_hash, "tasks": []}),
        encoding="utf-8",
    )
    child_state.write_text(
        json.dumps({"goal_hash": child_hash, "status": "complete"}),
        encoding="utf-8",
    )
    goal = compile_command_goal(
        "spec-fix",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature=feature,
        flags="--auto --update",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))
    child_task = next(
        task
        for task in contract["tasks"]
        if str(task["id"]).startswith("fix.child_goal.spec_check")
    )

    result = prove_goal_task(
        contract,
        state,
        str(child_task["id"]),
        {
            "child_goal_hash": child_hash,
            "child_contract_file": child_contract.as_posix(),
            "child_state_file": child_state.as_posix(),
            "child_final_status": "complete",
            "convention_domains": ["code", "design-tokens"],
            "convention_sources": [
                "$AIRESOURCES/code-conventions/general.md",
                "$AIRESOURCES/code-conventions/python.md",
                "$AIRESOURCES/design/tokens.md",
            ],
            "conventions_applied_to_output": True,
        },
        project_root=project_root,
    )

    assert result["status"] == "ACCEPTED"


def test_child_goal_contract_rejects_nested_goal_artifact_path(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions(project_root, tmp_path / "ai")
    feature = _write_complete_check_fix_scenario(project_root)
    child_hash = "abc12345"
    child_dir = tmp_path / "livespec-goals" / "child"
    child_dir.mkdir(parents=True)
    child_contract = child_dir / "goal-spec-check-abc12345.contract.json"
    child_state = child_dir / "goal-spec-check-abc12345.state.json"
    child_contract.write_text(
        json.dumps({"goal_hash": child_hash, "tasks": []}),
        encoding="utf-8",
    )
    child_state.write_text(
        json.dumps({"goal_hash": child_hash, "status": "complete"}),
        encoding="utf-8",
    )
    goal = compile_command_goal(
        "spec-fix",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature=feature,
        flags="--auto --update",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))
    child_task = next(
        task
        for task in contract["tasks"]
        if str(task["id"]).startswith("fix.child_goal.spec_check")
    )

    result = prove_goal_task(
        contract,
        state,
        str(child_task["id"]),
        {
            "child_goal_hash": child_hash,
            "child_contract_file": child_contract.as_posix(),
            "child_state_file": child_state.as_posix(),
            "child_final_status": "complete",
            "convention_domains": ["code", "design-tokens"],
            "convention_sources": [
                "$AIRESOURCES/code-conventions/general.md",
                "$AIRESOURCES/code-conventions/python.md",
                "$AIRESOURCES/design/tokens.md",
            ],
            "conventions_applied_to_output": True,
        },
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "child_contract_file_exists" in result["missing_evidence"]
    assert "child_state_file_exists" in result["missing_evidence"]


def test_child_goal_contract_rejects_arbitrary_absolute_path(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions(project_root, tmp_path / "ai")
    feature = _write_complete_check_fix_scenario(project_root)
    child_contract = tmp_path / "child.contract.json"
    child_state = tmp_path / "child.state.json"
    child_contract.write_text(
        json.dumps({"goal_hash": "abc123", "tasks": []}),
        encoding="utf-8",
    )
    child_state.write_text(
        json.dumps({"goal_hash": "abc123", "status": "complete"}),
        encoding="utf-8",
    )
    goal = compile_command_goal(
        "spec-fix",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature=feature,
        flags="--auto --update",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))
    child_task = next(
        task
        for task in contract["tasks"]
        if str(task["id"]).startswith("fix.child_goal.spec_check")
    )

    result = prove_goal_task(
        contract,
        state,
        str(child_task["id"]),
        {
            "child_goal_hash": "abc123",
            "child_contract_file": child_contract.as_posix(),
            "child_state_file": child_state.as_posix(),
            "child_final_status": "complete",
            "convention_domains": ["code", "design-tokens"],
            "convention_sources": [
                "$AIRESOURCES/code-conventions/general.md",
                "$AIRESOURCES/code-conventions/python.md",
                "$AIRESOURCES/design/tokens.md",
            ],
            "conventions_applied_to_output": True,
        },
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "child_contract_file_exists" in result["missing_evidence"]
    assert "child_state_file_exists" in result["missing_evidence"]


def test_spec_check_design_fidelity_contract_rejects_normalized_json_substitute(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "complete-project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions(project_root, tmp_path / "ai")
    _write_complete_check_fix_scenario(project_root)

    goal = compile_command_goal(
        "spec-check",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature=None,
        flags="--fix --all",
    )
    contract = json.loads(render_goal_contract_file(goal))
    visual_task = next(task for task in contract["tasks"] if task["id"] == "visual.design_fidelity")

    assert "visual_evidence_receipt_path" in visual_task["required_evidence"]
    assert "normalized_json_alignment_only" in visual_task["invalid_substitutes"]
    assert "worker_declared_diff_without_receipt" in visual_task["invalid_substitutes"]
    assert any("export mockup PNG" in action for action in visual_task["repair_if_missing"])


def test_goal_prove_rejects_missing_visual_design_fidelity_evidence(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "complete-project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions(project_root, tmp_path / "ai")
    _write_complete_check_fix_scenario(project_root)
    goal = compile_command_goal(
        "spec-check",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature=None,
        flags="--fix --all",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))

    result = prove_goal_task(
        contract,
        state,
        "visual.design_fidelity",
        evidence={
            "normalized_design_path": "penflow/expected-ui-tree.json",
            "normalized_runtime_path": "penflow/actual-ui-tree.json",
        },
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert result["state"]["tasks"]["visual.design_fidelity"]["status"] == "pending"
    assert "normalized_json_alignment_only" in result["invalid_substitutes"]
    assert any("mockup PNG" in action for action in result["required_actions"])


def test_goal_prove_rejects_legacy_visual_design_fidelity_payload(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "complete-project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions(project_root, tmp_path / "ai")
    feature = _write_complete_check_fix_scenario(project_root)
    goal = compile_command_goal(
        "spec-check",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature=None,
        flags="--fix --all",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))

    result = prove_goal_task(
        contract,
        state,
        "visual.design_fidelity",
        evidence={
            "mockup_path": f".specs/design/screens/{feature}/dashboard.png",
            "baseline_path": f".specs/design/baselines/{feature}/dashboard.png",
            "comparison_report": "penflow/compare-report.json",
            "threshold_percent": 5,
            "actual_diff_percent": 3.2,
            "verdict": "PASS",
        },
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert result["state"]["tasks"]["visual.design_fidelity"]["status"] == "pending"
    assert "visual_evidence_receipt_path" in result["missing_evidence"]


def test_goal_prove_accepts_visual_design_fidelity_receipt(
    tmp_path: Path,
) -> None:
    from validator.visual_evidence import (
        compare_visual_images,
        write_visual_receipt,
    )

    project_root = tmp_path / "complete-project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions(project_root, tmp_path / "ai")
    feature = _write_complete_check_fix_scenario(project_root)
    mockup = project_root / ".specs" / "design" / "screens" / feature / "dashboard.png"
    runtime = (
        project_root / ".specs" / "features" / feature / "run" / "manual" / "web" / "dashboard.png"
    )
    _write_png(mockup, (10, 20, 30))
    _write_png(runtime, (10, 20, 30))
    comparison = compare_visual_images(
        project_root=project_root,
        feature_slug=feature,
        screen="dashboard",
        target="web",
        comparison_kind="mockup_runtime",
        reference_path=mockup,
        actual_path=runtime,
        threshold_percent=5.0,
        diff_path=(
            project_root
            / ".specs"
            / "features"
            / feature
            / "run"
            / "manual"
            / "visual-evidence"
            / "dashboard.diff.png"
        ),
    )
    receipt_path = write_visual_receipt(
        project_root=project_root,
        feature_slug=feature,
        command="spec-check",
        target="web",
        run_id="manual",
        comparisons=[comparison],
        output_dir=(
            project_root / ".specs" / "features" / feature / "run" / "manual" / "visual-evidence"
        ),
    )
    goal = compile_command_goal(
        "spec-check",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature=None,
        flags="--fix --all",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))

    result = prove_goal_task(
        contract,
        state,
        "visual.design_fidelity",
        evidence={"visual_evidence_receipt_path": str(receipt_path)},
        project_root=project_root,
    )

    assert result["status"] == "ACCEPTED"
    assert result["state"]["tasks"]["visual.design_fidelity"]["status"] == "complete"


def test_goal_prove_rejects_visual_receipt_from_wrong_feature(
    tmp_path: Path,
) -> None:
    from validator.visual_evidence import (
        compare_visual_images,
        write_visual_receipt,
    )

    project_root = tmp_path / "complete-project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions(project_root, tmp_path / "ai")
    _write_complete_check_fix_scenario(project_root)
    other_feature = "999-other"
    mockup = project_root / ".specs" / "design" / "screens" / other_feature / "dashboard.png"
    runtime = (
        project_root
        / ".specs"
        / "features"
        / other_feature
        / "run"
        / "manual"
        / "web"
        / "dashboard.png"
    )
    _write_png(mockup, (10, 20, 30))
    _write_png(runtime, (10, 20, 30))
    comparison = compare_visual_images(
        project_root=project_root,
        feature_slug=other_feature,
        screen="dashboard",
        target="web",
        comparison_kind="mockup_runtime",
        reference_path=mockup,
        actual_path=runtime,
        threshold_percent=5.0,
        diff_path=(
            project_root
            / ".specs"
            / "features"
            / other_feature
            / "run"
            / "manual"
            / "visual-evidence"
            / "dashboard.diff.png"
        ),
    )
    receipt_path = write_visual_receipt(
        project_root=project_root,
        feature_slug=other_feature,
        command="spec-check",
        target="web",
        run_id="manual",
        comparisons=[comparison],
        output_dir=(
            project_root
            / ".specs"
            / "features"
            / other_feature
            / "run"
            / "manual"
            / "visual-evidence"
        ),
    )
    goal = compile_command_goal(
        "spec-check",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature=None,
        flags="--fix --all",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))

    result = prove_goal_task(
        contract,
        state,
        "visual.design_fidelity",
        evidence={"visual_evidence_receipt_path": str(receipt_path)},
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert any("feature_slug_mismatch" in item for item in result["missing_evidence"])


def test_spec_check_dod_requires_tree_validation_report_not_pass() -> None:
    dod = _command_definition_of_done(_repo_root() / ".agent-sync/skills/spec-check/SKILL.md")

    assert dod[0] == "Tree validation executed and reported (or skipped by --skip-tree)"
    assert not any("tree validation" in item.lower() and "passed" in item.lower() for item in dod)
    assert "Gap report produced and displayed" in dod
    assert "Gap report saved to `checks/YYYY-MM-DD.md`" in dod
    assert "Feature `changelog.md` has a check entry" in dod
    assert "Global `.specs/changelog.md` has a summary entry" in dod
    assert "If multi-spec: consolidated report produced" in dod


def test_render_goal_objective_is_stable_text_from_payload(tmp_path: Path) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    goal = compile_command_goal(
        "demo",
        project_root=project_root,
        livespec_root=livespec_root,
        feature="001-demo",
        flags="--strict",
    )

    objective = render_goal_objective(goal)

    assert objective == render_goal_objective(goal)
    assert "Goal hash:" in objective
    assert "Command: spec-demo" in objective
    assert "- `demo.txt` exists" in objective
    assert "Filesystem effects:" in objective
    assert "- creates demo.txt." in objective
    assert "- must contains: done" in objective


def test_anti_drift_block_documents_shared_goal_protocol() -> None:
    """AC-007: all imported command protocols share the same goal lifecycle."""
    text = Path("system/anti-drift-block.md").read_text(encoding="utf-8")

    assert "livespec goal render <command-name>" in text
    assert "/goal hash:<" in text  # Exact /goal slash command form with hash+ref
    assert "/goal clear" in text  # Active goal precheck
    assert "already active" in text  # Precheck documentation
    assert "contract-file:" in text
    assert "state-file:" in text
    assert "livespec goal prove" in text
    assert "[ ]` → `[x]" not in text
