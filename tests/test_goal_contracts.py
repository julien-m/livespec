# LiveSpec traceability anchors
# @spec(AC-001)
# @spec(AC-002)
# @spec(AC-003)
# @spec(AC-004)
# @spec(AC-005)
# @spec(AC-006)
# @spec(AC-007)
# @spec(AC-008)
# @spec(AC-009)
# @spec(AC-011)
# @spec(AC-012)
# @spec(AC-013)
# @spec(AC-014)
# @spec(AC-017)

"""Tests for deterministic command goal contracts.

# @spec FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-013, FR-014, FR-015, FR-019
#   — .specs/features/052-deterministic-command-goal-contracts/spec.md
"""

from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from validator.cli import app
from validator.conventions_gate import GateResult, GateVerdict, GateViolation
from validator.conventions_gates import gates_path
from validator.conventions_receipt import write_conventions_receipt
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


def _write_conventions_gates(project_root: Path) -> Path:
    path = gates_path(project_root)
    constitution = project_root / ".specs" / "constitution.md"
    constitution.parent.mkdir(parents=True, exist_ok=True)
    constitution.write_text("# Constitution\n", encoding="utf-8")
    path.write_text(
        """\
schema_version: 1
generated_from:
  constitution: .specs/constitution.md
  constitution_sha256: 1e573f647f46d0e508830de88db17ac2b096487ad15f73dbd608d5d35640ed94
  stack: .specs/stacks/_default.md
commands: {}
builtin: {}
coverage: {}
exclusions: []
scope: repo
""",
        encoding="utf-8",
    )
    return path


def _write_fail_conventions_receipt(project_root: Path) -> Path:
    gates = _write_conventions_gates(project_root)
    return write_conventions_receipt(
        project_root=project_root,
        feature_slug="001-demo",
        run_id="r-fail",
        result=GateResult(
            verdict=GateVerdict.FAIL,
            violations=[
                GateViolation(
                    rule_id="max_file_lines",
                    path="src/too_long.py",
                    line=501,
                    severity="error",
                    message="file too long",
                    source="builtin",
                )
            ],
            blockers=[],
        ),
        gates_path=gates,
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


def test_compile_command_goal_embeds_non_empty_before_hook_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    integrations_dir = tmp_path / "integrations"
    integrations_dir.mkdir()
    (integrations_dir / "qe-analysis.md").write_text(
        """\
---
integration: qe-analysis
commands: [plan]
phase: before
mode: extend
order: 60
---
# QE Analysis

Apply the QE analysis protocol before planning tests.
""",
        encoding="utf-8",
    )
    monkeypatch.setattr("validator.integrations.INTEGRATIONS_DIR", integrations_dir)

    goal = compile_command_goal(
        "spec-plan",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))

    before_hook = contract["hooks"]["before"]
    assert before_hook["non_empty"] is True
    assert "qe-analysis" in goal.canonical_json
    assert "# QE Analysis" in before_hook["context"]
    assert contract["tasks"][0]["id"] == "hooks.before"
    assert "resolved_hook_context_sha256" in contract["tasks"][0]["required_evidence"]
    assert "Hook context to apply:" in goal.objective


def test_goal_prove_requires_resolved_before_hook_context(tmp_path: Path) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    goal = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
    )
    hook_task = {
        "id": "hooks.before",
        "ordinal": 1,
        "category": "injected",
        "description": "Resolve hooks",
        "required_evidence": [
            "hook_resolution_command",
            "resolved_hook_context_sha256",
            "hook_context_applied",
        ],
        "invalid_substitutes": [
            "manual_integration_summary",
            "config_file_exists_without_resolved_context",
        ],
        "repair_if_missing": ["run hooks resolve"],
        "completion_actor": "goal",
        "expected_evidence": {
            "hook_resolution_command": "livespec hooks resolve --event before --command demo",
            "resolved_hook_context_sha256": "abc123",
        },
    }
    contract = json.loads(render_goal_contract_file(goal))
    contract["tasks"].insert(0, hook_task)
    state = json.loads(render_goal_state_file(goal))
    state["tasks"]["hooks.before"] = {
        "ordinal": 1,
        "description": "Resolve hooks",
        "status": "pending",
        "attempts": [],
        "accepted_evidence": None,
        "last_rejection": None,
    }

    rejected = prove_goal_task(
        contract,
        state,
        "hooks.before",
        evidence={
            "config_file_exists": True,
            "summary": "qe-analysis configured",
        },
        project_root=project_root,
    )

    assert rejected["status"] == "REJECTED_NEEDS_ACTION"
    assert "hook_resolution_command" in rejected["missing_evidence"]
    assert "resolved_hook_context_sha256" in rejected["missing_evidence"]
    assert "hook_context_applied" in rejected["missing_evidence"]
    assert "config_file_exists_without_resolved_context" in rejected["invalid_substitutes"]

    accepted = prove_goal_task(
        contract,
        state,
        "hooks.before",
        evidence={
            "hook_resolution_command": "livespec hooks resolve --event before --command demo",
            "resolved_hook_context_sha256": "abc123",
            "hook_context_applied": True,
        },
        project_root=project_root,
    )

    assert accepted["status"] == "ACCEPTED"


# @spec FR-002: Native QE render, FR-006: No user config/global skill dependency
#   — .specs/features/071-qe-analysis-native-module/spec.md#fr-002
def test_spec_plan_goal_embeds_native_qe_without_user_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    monkeypatch.setattr("validator.integrations.INTEGRATIONS_DIR", tmp_path / "missing-l0")
    monkeypatch.setattr("validator.hook_resolver.GLOBAL_HOOKS_DIR", tmp_path / "missing-global")

    goal = compile_command_goal(
        "spec-plan",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature="001-demo",
        flags="",
    )
    contract = json.loads(render_goal_contract_file(goal))

    qe_context = contract["qe_analysis"]
    assert qe_context["native"] is True
    assert qe_context["source_path"] == "system/qe-analysis.md"
    assert qe_context["user_hooks_role"] == "extension_only"
    assert "Quality Engineering" in qe_context["content"]
    assert "~/.config/livespec/qe-analysis.md" not in qe_context["content"]
    assert "$qe-analysis" not in qe_context["content"]

    qe_task = next(task for task in contract["tasks"] if task["id"] == "qe.analysis")
    assert qe_task["required_evidence"] == [
        "qe_dimensions_considered",
        "qe_gates_required",
        "qe_expected_evidence",
        "qe_gaps_or_missing_evidence",
        "qe_boundary_note",
    ]
    assert "Native QE Analysis:" in goal.objective


# @spec FR-003: Affected commands receive qe.analysis
#   — .specs/features/071-qe-analysis-native-module/spec.md#fr-003
@pytest.mark.parametrize("command", ["spec-specify", "spec-plan", "spec-test"])
def test_native_qe_analysis_task_is_injected_for_quality_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command: str,
) -> None:
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    monkeypatch.setattr("validator.integrations.INTEGRATIONS_DIR", tmp_path / "missing-l0")
    monkeypatch.setattr("validator.hook_resolver.GLOBAL_HOOKS_DIR", tmp_path / "missing-global")

    goal = compile_command_goal(
        command,
        project_root=project_root,
        livespec_root=_repo_root(),
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))

    task_ids = [task["id"] for task in contract["tasks"]]
    assert "qe.analysis" in task_ids
    assert task_ids.index("qe.analysis") < task_ids.index("archive.run")


# @spec FR-003: Unaffected commands do not receive qe.analysis
#   — .specs/features/071-qe-analysis-native-module/spec.md#fr-003
def test_native_qe_analysis_task_is_not_injected_for_unaffected_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    monkeypatch.setattr("validator.integrations.INTEGRATIONS_DIR", tmp_path / "missing-l0")
    monkeypatch.setattr("validator.hook_resolver.GLOBAL_HOOKS_DIR", tmp_path / "missing-global")

    goal = compile_command_goal(
        "spec-check",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))

    assert "qe_analysis" not in contract
    assert "qe.analysis" not in [task["id"] for task in contract["tasks"]]


# @spec FR-005: Generic QE proof is rejected
#   — .specs/features/071-qe-analysis-native-module/spec.md#fr-005
def test_goal_prove_rejects_generic_qe_analysis_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    monkeypatch.setattr("validator.integrations.INTEGRATIONS_DIR", tmp_path / "missing-l0")
    monkeypatch.setattr("validator.hook_resolver.GLOBAL_HOOKS_DIR", tmp_path / "missing-global")
    goal = compile_command_goal(
        "spec-plan",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))

    result = prove_goal_task(
        contract,
        state,
        "qe.analysis",
        evidence={
            "output": "quality checked",
            "success_criteria_met": True,
            "summary": "QE looks good",
        },
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert result["missing_evidence"] == [
        "qe_dimensions_considered",
        "qe_gates_required",
        "qe_expected_evidence",
        "qe_gaps_or_missing_evidence",
        "qe_boundary_note",
    ]
    assert "generic_quality_claim" in result["invalid_substitutes"]


# @spec FR-006: Skill/config substitutes are rejected
#   — .specs/features/071-qe-analysis-native-module/spec.md#fr-006
@pytest.mark.parametrize(
    ("extra_evidence", "invalid_substitute"),
    [
        ({"skill": "qe-analysis"}, "skill_global_qe_analysis_invocation"),
        ({"qe_analysis_skill_invoked": True}, "skill_global_qe_analysis_invocation"),
        ({"config_path": "~/.config/livespec/qe-analysis.md"}, "user_config_qe_analysis_only"),
        ({"user_config_qe_analysis": True}, "user_config_qe_analysis_only"),
    ],
)
def test_goal_prove_rejects_qe_analysis_substitutes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    extra_evidence: dict[str, object],
    invalid_substitute: str,
) -> None:
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    monkeypatch.setattr("validator.integrations.INTEGRATIONS_DIR", tmp_path / "missing-l0")
    monkeypatch.setattr("validator.hook_resolver.GLOBAL_HOOKS_DIR", tmp_path / "missing-global")
    goal = compile_command_goal(
        "spec-plan",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))

    evidence: dict[str, object] = {
        "qe_dimensions_considered": ["functional_correctness"],
        "qe_gates_required": ["AC coverage matrix maps every AC to test evidence"],
        "qe_expected_evidence": ["test command transcript with pass/fail counts"],
        "qe_gaps_or_missing_evidence": ["no visual proof required for CLI-only change"],
        "qe_boundary_note": "Review/audit owns defect hunting; tests own evidence sufficiency.",
        **extra_evidence,
    }
    result = prove_goal_task(
        contract,
        state,
        "qe.analysis",
        evidence=evidence,
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert result["missing_evidence"] == []
    assert invalid_substitute in result["invalid_substitutes"]


# @spec FR-004: Structured QE proof is accepted
#   — .specs/features/071-qe-analysis-native-module/spec.md#fr-004
def test_goal_prove_accepts_structured_qe_analysis_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    monkeypatch.setattr("validator.integrations.INTEGRATIONS_DIR", tmp_path / "missing-l0")
    monkeypatch.setattr("validator.hook_resolver.GLOBAL_HOOKS_DIR", tmp_path / "missing-global")
    goal = compile_command_goal(
        "spec-test",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))

    result = prove_goal_task(
        contract,
        state,
        "qe.analysis",
        evidence={
            "qe_dimensions_considered": [
                "functional_correctness",
                "regression_risk",
                "api_contract_compatibility",
            ],
            "qe_gates_required": [
                "AC coverage matrix maps every AC to test evidence",
                "resolved test commands exit 0",
            ],
            "qe_expected_evidence": [
                "checks/YYYY-MM-DD-test.md coverage report",
                "test command transcript with pass/fail counts",
            ],
            "qe_gaps_or_missing_evidence": [
                "visual proof not applicable for non-UI feature",
            ],
            "qe_boundary_note": (
                "Defect hunting remains in review/audit; spec-test owns test evidence."
            ),
        },
        project_root=project_root,
    )

    assert result["status"] == "ACCEPTED"
    assert result["state"]["tasks"]["qe.analysis"]["status"] == "complete"


# @spec FR-007: User hooks remain extension-only
#   — .specs/features/071-qe-analysis-native-module/spec.md#fr-007
def test_native_qe_is_primary_and_user_hooks_are_additive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    integrations_dir = tmp_path / "integrations"
    integrations_dir.mkdir()
    (integrations_dir / "qe-analysis.md").write_text(
        """\
---
integration: personal-qe
commands: [plan]
phase: before
mode: extend
order: 60
---
Personal QE addendum only.
""",
        encoding="utf-8",
    )
    monkeypatch.setattr("validator.integrations.INTEGRATIONS_DIR", integrations_dir)
    monkeypatch.setattr("validator.hook_resolver.GLOBAL_HOOKS_DIR", tmp_path / "missing-global")

    goal = compile_command_goal(
        "spec-plan",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))

    assert contract["qe_analysis"]["native"] is True
    assert contract["qe_analysis"]["source_path"] == "system/qe-analysis.md"
    assert contract["hooks"]["before"]["non_empty"] is True
    assert "Personal QE addendum only." in contract["hooks"]["before"]["context"]
    assert "qe.analysis" in [task["id"] for task in contract["tasks"]]


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


def test_conventions_gate_not_required_for_unlisted_command(tmp_path: Path) -> None:
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_conventions(project_root, tmp_path / "ai")
    _write_conventions_gates(project_root)
    _write_execution_task_skill(livespec_root)

    goal = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))
    final_tasks = [task for task in contract["tasks"] if task["id"] != "archive.run"]

    assert final_tasks
    assert all("conventions_receipt_path" not in task["required_evidence"] for task in final_tasks)


def test_conventions_gate_not_required_for_spec_plan(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions_gates(project_root)

    goal = compile_command_goal(
        "spec-plan",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))
    final_tasks = [task for task in contract["tasks"] if task["id"] != "archive.run"]

    assert final_tasks
    assert all("conventions_receipt_path" not in task["required_evidence"] for task in final_tasks)


def test_conventions_gate_required_for_spec_implement(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions_gates(project_root)

    goal = compile_command_goal(
        "spec-implement",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))
    final_tasks = [
        task for task in contract["tasks"] if task["id"] not in {"archive.run", "hooks.before"}
    ]

    assert final_tasks
    assert all("conventions_receipt_path" in task["required_evidence"] for task in final_tasks)


def test_goal_prove_rejects_non_pass_conventions_receipt(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".specs").mkdir()
    _write_conventions(project_root, tmp_path / "ai")
    receipt = _write_fail_conventions_receipt(project_root)
    goal = compile_command_goal(
        "spec-implement",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))
    task_id = next(
        task["id"]
        for task in contract["tasks"]
        if "conventions_receipt_path" in task["required_evidence"]
    )

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
            "conventions_receipt_path": receipt.relative_to(project_root).as_posix(),
        },
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "conventions_receipt_verdict_pass" in result["missing_evidence"]


def test_goal_prove_rejects_conventions_receipt_outside_project(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".specs").mkdir()
    _write_conventions(project_root, tmp_path / "ai")
    _write_conventions_gates(project_root)
    outside = tmp_path / "outside-receipt.json"
    outside.write_text("{}", encoding="utf-8")
    goal = compile_command_goal(
        "spec-implement",
        project_root=project_root,
        livespec_root=_repo_root(),
        feature="001-demo",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))
    task_id = next(
        task["id"]
        for task in contract["tasks"]
        if "conventions_receipt_path" in task["required_evidence"]
    )

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
            "conventions_receipt_path": outside.as_posix(),
        },
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert any(
        item.startswith("conventions_receipt_valid:path_outside_project")
        for item in result["missing_evidence"]
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


# ─── finalize.registry evidence family (Feature 058, FR-005/FR-006) ──────────

FINALIZE_SKILL = """\
---
name: spec-demo
description: Demo command
---

# /spec-demo

## Execution Tasks

- [always] Finalize registry via `livespec finalize apply` + `livespec finalize verify` \
and prove finalize.registry with the receipt path

## Definition of Done (Command-Level)

- [ ] Done
"""


def _finalize_fixture(tmp_path: Path) -> tuple[Path, Path]:
    """Fixture roots with the finalize execution-task skill and a .specs tree."""
    from tests.test_finalize import _make_specs_tree

    project_root, livespec_root = _fixture_roots(tmp_path)
    skill_path = livespec_root / ".agent-sync" / "skills" / "spec-demo" / "SKILL.md"
    skill_path.write_text(FINALIZE_SKILL, encoding="utf-8")
    _make_specs_tree(project_root)
    return project_root, livespec_root


def _finalize_contract_and_state(project_root: Path, livespec_root: Path) -> tuple[dict, dict]:
    goal = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
        feature="004-notifications",
        flags="",
    )
    return (
        json.loads(render_goal_contract_file(goal)),
        json.loads(render_goal_state_file(goal)),
    )


def test_finalize_registry_task_requires_receipt_path(tmp_path: Path) -> None:
    """AC-007: the finalize execution-task line must compile to the
    finalize.registry task whose only accepted evidence is the receipt path."""
    project_root, livespec_root = _finalize_fixture(tmp_path)
    contract, _state = _finalize_contract_and_state(project_root, livespec_root)
    task = next(task for task in contract["tasks"] if task["id"] == "finalize.registry")
    assert "finalize_receipt_path" in task["required_evidence"]
    assert "prose_finalization_claim" in task["invalid_substitutes"]
    assert any("livespec finalize apply" in action for action in task["repair_if_missing"])


def test_goal_prove_rejects_prose_finalization_claim(tmp_path: Path) -> None:
    """AC-008: prose claims without a receipt are invalid substitutes."""
    project_root, livespec_root = _finalize_fixture(tmp_path)
    contract, state = _finalize_contract_and_state(project_root, livespec_root)
    result = prove_goal_task(
        contract,
        state,
        "finalize.registry",
        evidence={"output": "All registry files were updated", "success_criteria_met": True},
        project_root=project_root,
    )
    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "finalize_receipt_path" in result["missing_evidence"]
    assert "prose_finalization_claim" in result["invalid_substitutes"]
    assert result["state"]["tasks"]["finalize.registry"]["status"] == "pending"


def test_goal_prove_rejects_exit_code_and_file_list_substitutes(tmp_path: Path) -> None:
    """AC-008: exit codes and declared file lists are not finalization proof."""
    project_root, livespec_root = _finalize_fixture(tmp_path)
    contract, state = _finalize_contract_and_state(project_root, livespec_root)
    result = prove_goal_task(
        contract,
        state,
        "finalize.registry",
        evidence={"exit_code": 0, "files": [".specs/README.md", ".specs/changelog.md"]},
        project_root=project_root,
    )
    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "exit_code_without_receipt" in result["invalid_substitutes"]
    assert "declared_file_list_without_receipt" in result["invalid_substitutes"]


def test_goal_prove_accepts_valid_finalize_receipt(tmp_path: Path) -> None:
    """AC-007: a real PASS receipt from finalize verify completes the task."""
    from validator.finalize import ApplyRequest, apply_finalization, verify_finalization

    project_root, livespec_root = _finalize_fixture(tmp_path)
    request = ApplyRequest(
        feature_slug="004-notifications",
        command="spec-demo",
        status="Implemented",
        entry_body="Feature: Implemented notifications",
        global_summary="[Feature 004] Implemented: Notifications",
        run_id="goal-run",
    )
    apply_finalization(project_root, request)
    verify_result = verify_finalization(
        project_root,
        "004-notifications",
        expected_command="spec-demo",
        run_id="goal-run",
    )
    assert verify_result.verdict == "PASS"
    contract, state = _finalize_contract_and_state(project_root, livespec_root)
    result = prove_goal_task(
        contract,
        state,
        "finalize.registry",
        evidence={"finalize_receipt_path": str(verify_result.receipt_path)},
        project_root=project_root,
    )
    assert result["status"] == "ACCEPTED"
    assert result["state"]["tasks"]["finalize.registry"]["status"] == "complete"


def test_goal_prove_rejects_tampered_finalize_receipt(tmp_path: Path) -> None:
    """AC-008 / SC-004: a registry file edited after verify makes the receipt
    stale; the proof must be rejected with the named evidence."""
    from validator.finalize import ApplyRequest, apply_finalization, verify_finalization

    project_root, livespec_root = _finalize_fixture(tmp_path)
    request = ApplyRequest(
        feature_slug="004-notifications",
        command="spec-demo",
        status="Implemented",
        entry_body="Feature: Implemented notifications",
        global_summary="[Feature 004] Implemented: Notifications",
        run_id="goal-run",
    )
    apply_finalization(project_root, request)
    verify_result = verify_finalization(
        project_root,
        "004-notifications",
        expected_command="spec-demo",
        run_id="goal-run",
    )
    readme = project_root / ".specs" / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8") + "\ntampered\n", encoding="utf-8")
    contract, state = _finalize_contract_and_state(project_root, livespec_root)
    result = prove_goal_task(
        contract,
        state,
        "finalize.registry",
        evidence={"finalize_receipt_path": str(verify_result.receipt_path)},
        project_root=project_root,
    )
    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert any(item.startswith("finalize_receipt_valid:") for item in result["missing_evidence"])


def test_goal_prove_rejects_fail_verdict_finalize_receipt(tmp_path: Path) -> None:
    """AC-008: a FAIL-verdict receipt names the PASS requirement."""
    from validator.finalize import ApplyRequest, apply_finalization, verify_finalization

    project_root, livespec_root = _finalize_fixture(tmp_path)
    request = ApplyRequest(
        feature_slug="004-notifications",
        command="spec-demo",
        status="Implemented",
        entry_body="Feature: Implemented notifications",
        global_summary="[Feature 004] Implemented: Notifications",
        run_id="goal-run",
    )
    apply_finalization(project_root, request)
    # Corrupt the registry BEFORE verify so verify emits a FAIL receipt whose
    # file hashes still match the (corrupted) on-disk state.
    readme = project_root / ".specs" / "README.md"
    readme.write_text(
        "\n".join(
            line
            for line in readme.read_text(encoding="utf-8").splitlines()
            if "004-notifications" not in line and not line.startswith("| 004 ")
        ),
        encoding="utf-8",
    )
    verify_result = verify_finalization(
        project_root,
        "004-notifications",
        expected_command="spec-demo",
        run_id="goal-run-fail",
    )
    assert verify_result.verdict == "FAIL"
    contract, state = _finalize_contract_and_state(project_root, livespec_root)
    result = prove_goal_task(
        contract,
        state,
        "finalize.registry",
        evidence={"finalize_receipt_path": str(verify_result.receipt_path)},
        project_root=project_root,
    )
    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "finalize_receipt_verdict_pass" in result["missing_evidence"]


@pytest.mark.parametrize(
    "command",
    ["spec-specify", "spec-plan", "spec-implement", "spec-fix", "spec-stack", "spec-feature"],
)
def test_six_registry_commands_carry_finalize_registry_task(
    tmp_path: Path,
    command: str,
) -> None:
    """FR-005 (AC-007): every registry-finalizing command's real contract must
    include the finalize.registry task so DONE structurally requires the receipt."""
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions(project_root, tmp_path / "ai")
    feature = _write_complete_check_fix_scenario(project_root)
    goal = compile_command_goal(
        command,
        project_root=project_root,
        livespec_root=_repo_root(),
        feature=feature,
        flags="",
    )
    contract = json.loads(render_goal_contract_file(goal))
    finalize_tasks = [task for task in contract["tasks"] if task["id"] == "finalize.registry"]
    assert finalize_tasks, f"{command} contract lacks the finalize.registry task"
    assert "finalize_receipt_path" in finalize_tasks[0]["required_evidence"]


# ─── archive.run injected task (Feature 059, FR-001/FR-002/FR-003) ───────────


def _demo_contract_and_state(
    project_root: Path,
    livespec_root: Path,
    *,
    feature: str | None = "001-demo",
    flags: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compile the spec-demo fixture goal and return contract+state dicts."""
    goal = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
        feature=feature,
        flags=flags,
    )
    return (
        json.loads(render_goal_contract_file(goal)),
        json.loads(render_goal_state_file(goal)),
    )


@pytest.mark.parametrize(
    ("with_execution_tasks", "feature", "flags"),
    [
        (False, None, ""),
        (False, "001-demo", "--strict"),
        (True, None, ""),
        (True, "001-demo", "--strict --auto"),
    ],
)
def test_every_contract_carries_exactly_one_archive_run_task(
    tmp_path: Path,
    with_execution_tasks: bool,
    feature: str | None,
    flags: str,
) -> None:
    """AC-001: archive.run is injected compiler-side for every command/feature/flags."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    if with_execution_tasks:
        _write_execution_task_skill(livespec_root)

    contract, state = _demo_contract_and_state(
        project_root, livespec_root, feature=feature, flags=flags
    )

    archive_tasks = [task for task in contract["tasks"] if task["id"] == "archive.run"]
    assert len(archive_tasks) == 1
    assert "archive.run" in state["tasks"]
    assert state["tasks"]["archive.run"]["status"] == "pending"


def test_archive_run_task_has_strictly_highest_ordinal(tmp_path: Path) -> None:
    """AC-002: archive.run snapshots all prior evidence — always the last ordinal."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_execution_task_skill(livespec_root)

    contract, _state = _demo_contract_and_state(project_root, livespec_root)

    archive_task = next(task for task in contract["tasks"] if task["id"] == "archive.run")
    other_ordinals = [task["ordinal"] for task in contract["tasks"] if task["id"] != "archive.run"]
    assert all(archive_task["ordinal"] > ordinal for ordinal in other_ordinals)
    assert archive_task["ordinal"] == max(task["ordinal"] for task in contract["tasks"])


def test_archive_run_task_evidence_family_matches_constants(tmp_path: Path) -> None:
    """AC-003: required evidence, named substitutes, and repair actions are fixed."""
    project_root, livespec_root = _fixture_roots(tmp_path)

    contract, _state = _demo_contract_and_state(project_root, livespec_root)

    task = next(task for task in contract["tasks"] if task["id"] == "archive.run")
    assert task["required_evidence"] == ["run_artifact_path"]
    assert task["invalid_substitutes"] == [
        "prose_archive_claim",
        "exit_code_without_artifact",
        "tmpdir_contract_state_paths_without_artifact",
    ]
    assert task["category"] == "injected"
    assert "livespec goal archive" in task["description"]
    assert any("livespec goal archive" in action for action in task["repair_if_missing"])
    assert any("artifact path" in action for action in task["repair_if_missing"])


def test_archive_run_task_skips_convention_evidence_layering(tmp_path: Path) -> None:
    """AC-003: the synthetic compiler task never carries convention proof fields."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_conventions(project_root, tmp_path / "ai")
    _write_execution_task_skill(livespec_root)

    contract, _state = _demo_contract_and_state(project_root, livespec_root)

    task = next(task for task in contract["tasks"] if task["id"] == "archive.run")
    assert task["required_evidence"] == ["run_artifact_path"]
    assert "required_conventions" not in task
    # Prose tasks keep convention layering — the injection must not strip them.
    prose_task = contract["tasks"][0]
    assert "convention_domains_recorded" in prose_task["required_evidence"]


def test_archive_run_injection_preserves_hash_determinism(tmp_path: Path) -> None:
    """AC-002: same inputs → same canonical JSON and hash with the injected task."""
    project_root, livespec_root = _fixture_roots(tmp_path)

    rendered = [
        compile_command_goal(
            "spec-demo",
            project_root=project_root,
            livespec_root=livespec_root,
            feature="001-demo",
            flags="--strict",
        )
        for _ in range(5)
    ]

    first = rendered[0]
    assert all(goal.goal_hash == first.goal_hash for goal in rendered)
    assert all(goal.canonical_json == first.canonical_json for goal in rendered)
    assert '"archive.run"' in first.canonical_json


# ─── archive.run prove validator (Feature 059, FR-003) ───────────────────────


def _archive_fixture_artifact(
    project_root: Path,
    contract: dict[str, Any],
    state: dict[str, Any],
) -> Path:
    """Archive the fixture goal and return the written artifact path."""
    from validator.run_artifacts import archive_goal_run

    result = archive_goal_run(contract, state, project_root=project_root, exit_code=0)
    assert result.path is not None
    return result.path


def test_archive_run_prove_rejects_prose_claim(tmp_path: Path) -> None:
    """AC-003: prose without an artifact path names prose_archive_claim."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    contract, state = _demo_contract_and_state(project_root, livespec_root)

    result = prove_goal_task(
        contract,
        state,
        "archive.run",
        evidence={"output": "I archived the run", "success_criteria_met": True},
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "prose_archive_claim" in result["invalid_substitutes"]
    assert "run_artifact_path" in result["missing_evidence"]
    assert any("livespec goal archive" in action for action in result["required_actions"])
    assert result["state"]["tasks"]["archive.run"]["status"] == "pending"


def test_archive_run_prove_rejects_exit_code_substitute(tmp_path: Path) -> None:
    """AC-003: an exit code is not an artifact."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    contract, state = _demo_contract_and_state(project_root, livespec_root)

    result = prove_goal_task(
        contract,
        state,
        "archive.run",
        evidence={"exit_code": 0},
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "exit_code_without_artifact" in result["invalid_substitutes"]


def test_archive_run_prove_rejects_tmpdir_contract_state_paths(tmp_path: Path) -> None:
    """AC-003: $TMPDIR contract/state paths are not the durable artifact."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    contract, state = _demo_contract_and_state(project_root, livespec_root)

    result = prove_goal_task(
        contract,
        state,
        "archive.run",
        evidence={
            "contract_file": "/tmp/livespec-goals/goal-spec-demo-abcd1234.contract.json",
            "state_file": "/tmp/livespec-goals/goal-spec-demo-abcd1234.state.json",
        },
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "tmpdir_contract_state_paths_without_artifact" in result["invalid_substitutes"]


def test_archive_run_prove_rejects_path_outside_specs_runs(tmp_path: Path) -> None:
    """AC-004: containment — the artifact must live under .specs/.runs/."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    contract, state = _demo_contract_and_state(project_root, livespec_root)
    outside = project_root / "artifact.json"
    outside.write_text("{}", encoding="utf-8")

    result = prove_goal_task(
        contract,
        state,
        "archive.run",
        evidence={"run_artifact_path": str(outside)},
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "run_artifact_under_specs_runs" in result["missing_evidence"]


def test_archive_run_prove_rejects_malformed_artifact_file(tmp_path: Path) -> None:
    """AC-004 (chaos-style fixture, unmarked so it runs at every level): a
    malformed v2 file is named in the rejection."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    contract, state = _demo_contract_and_state(project_root, livespec_root)
    runs_dir = project_root / ".specs" / ".runs"
    runs_dir.mkdir(parents=True)
    bad = runs_dir / "spec-demo-2026-06-11T10-00-00.000000-deadbeef.json"
    bad.write_text("{truncated", encoding="utf-8")

    result = prove_goal_task(
        contract,
        state,
        "archive.run",
        evidence={"run_artifact_path": str(bad)},
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert any(item.startswith("run_artifact_valid:") for item in result["missing_evidence"])


def test_archive_run_prove_rejects_foreign_goal_artifact(tmp_path: Path) -> None:
    """AC-004: an artifact archived under another goal hash is rejected."""
    from tests.test_run_artifact import make_contract, make_state

    project_root, livespec_root = _fixture_roots(tmp_path)
    contract, state = _demo_contract_and_state(project_root, livespec_root)
    foreign = _archive_fixture_artifact(
        project_root,
        make_contract(command="spec-demo", goal_hash="f" * 64),
        make_state(command="spec-demo", goal_hash="f" * 64),
    )

    result = prove_goal_task(
        contract,
        state,
        "archive.run",
        evidence={"run_artifact_path": str(foreign)},
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "run_artifact_goal_hash_match" in result["missing_evidence"]


def test_archive_run_prove_rejects_foreign_command_artifact(tmp_path: Path) -> None:
    """AC-004: an artifact archived for another command is rejected."""
    from tests.test_run_artifact import make_contract, make_state

    project_root, livespec_root = _fixture_roots(tmp_path)
    contract, state = _demo_contract_and_state(project_root, livespec_root)
    goal_hash = str(contract["goal_hash"])
    foreign = _archive_fixture_artifact(
        project_root,
        make_contract(command="spec-other", goal_hash=goal_hash),
        make_state(command="spec-other", goal_hash=goal_hash),
    )

    result = prove_goal_task(
        contract,
        state,
        "archive.run",
        evidence={"run_artifact_path": str(foreign)},
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "run_artifact_command_match" in result["missing_evidence"]


def test_archive_run_prove_accepts_matching_artifact_read_only(tmp_path: Path) -> None:
    """AC-004/AC-005: a matching .specs/.runs/ artifact is accepted without re-archiving."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    contract, state = _demo_contract_and_state(project_root, livespec_root)
    artifact_path = _archive_fixture_artifact(project_root, contract, state)
    runs_dir = project_root / ".specs" / ".runs"
    listing_before = sorted(path.name for path in runs_dir.iterdir())

    result = prove_goal_task(
        contract,
        state,
        "archive.run",
        evidence={"run_artifact_path": str(artifact_path)},
        project_root=project_root,
    )

    assert result["status"] == "ACCEPTED"
    assert result["state"]["tasks"]["archive.run"]["status"] == "complete"
    # Read-only bootstrap: the proof never writes anything under .specs/.runs/.
    assert sorted(path.name for path in runs_dir.iterdir()) == listing_before


def test_archive_run_prove_accepts_non_latest_matching_artifact(tmp_path: Path) -> None:
    """EC-002: any artifact with a matching goal hash is accepted, not only the latest."""
    from tests.test_run_artifact import make_contract, make_state

    project_root, livespec_root = _fixture_roots(tmp_path)
    contract, state = _demo_contract_and_state(project_root, livespec_root)
    matching = _archive_fixture_artifact(project_root, contract, state)
    # A later artifact for the same command but another goal makes `matching` non-latest.
    _archive_fixture_artifact(
        project_root,
        make_contract(command="spec-demo", goal_hash="9" * 64),
        make_state(command="spec-demo", goal_hash="9" * 64),
    )

    result = prove_goal_task(
        contract,
        state,
        "archive.run",
        evidence={"run_artifact_path": str(matching)},
        project_root=project_root,
    )

    assert result["status"] == "ACCEPTED"
    # Meaningful postcondition: the accepted evidence records the non-latest
    # matching artifact path, proving EC-002 (no latest-only restriction).
    accepted = result["state"]["tasks"]["archive.run"]["accepted_evidence"]
    assert accepted["run_artifact_path"] == str(matching)


def test_archive_run_prove_rejects_deleted_artifact_with_repair(tmp_path: Path) -> None:
    """EC-003: artifact deleted between archive and prove → repair instructs re-archive."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    contract, state = _demo_contract_and_state(project_root, livespec_root)
    artifact_path = _archive_fixture_artifact(project_root, contract, state)
    artifact_path.unlink()

    result = prove_goal_task(
        contract,
        state,
        "archive.run",
        evidence={"run_artifact_path": str(artifact_path)},
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert any(item.startswith("run_artifact_valid:") for item in result["missing_evidence"])
    assert any("livespec goal archive" in action for action in result["required_actions"])


# ─── Feature 059 Step 9 — registry sweep + end-to-end proof chain ─────────────


@pytest.mark.level_3a
def test_every_registry_command_contract_ends_with_archive_run(tmp_path: Path) -> None:
    """SC-001: sweep over the real command registry — every goal-locked
    contract's max-ordinal task id is archive.run."""
    from validator.command_registry import discover_commands

    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    commands = discover_commands(_repo_root() / ".agent-sync" / "skills")
    assert commands, "registry discovery returned no commands"

    for info in commands:
        goal = compile_command_goal(
            info.name,
            project_root=project_root,
            livespec_root=_repo_root(),
            feature=None,
            flags="",
        )
        contract = json.loads(render_goal_contract_file(goal))
        last_task = max(contract["tasks"], key=lambda task: int(task["ordinal"]))
        assert last_task["id"] == "archive.run", (
            f"{info.name} contract max-ordinal task is {last_task['id']!r}"
        )


def test_archive_run_end_to_end_drill(tmp_path: Path) -> None:
    """SC-002/SC-004 drill: prove prior tasks → archive → prove archive.run
    → ACCEPTED on first attempt; the artifact outcome is success while its
    snapshot still shows archive.run pending (self-reference exclusion)."""
    from validator.run_artifacts import archive_goal_run

    project_root, livespec_root = _fixture_roots(tmp_path)
    contract, state = _demo_contract_and_state(project_root, livespec_root, flags="")

    # Prove every prior (non-archive) task with generic evidence.
    for task in contract["tasks"]:
        if task["id"] == "archive.run":
            continue
        result = prove_goal_task(
            contract,
            state,
            str(task["id"]),
            evidence={"output": "done", "success_criteria_met": True},
            project_root=project_root,
        )
        assert result["status"] == "ACCEPTED", result
        state = result["state"]

    archive = archive_goal_run(contract, state, project_root=project_root, exit_code=0)
    assert archive.path is not None
    # SC-004: success despite archive.run pending in the embedded snapshot.
    assert archive.outcome == "success"
    assert archive.artifact is not None
    snapshot = {task["id"]: task["status"] for task in archive.artifact["goal"]["tasks"]}
    assert snapshot["archive.run"] == "pending"
    assert archive.artifact["verify_result"]["outcome"] == "success"

    # SC-002: the printed artifact path is accepted on the first attempt.
    proof = prove_goal_task(
        contract,
        state,
        "archive.run",
        evidence={"run_artifact_path": str(archive.path)},
        project_root=project_root,
    )
    assert proof["status"] == "ACCEPTED"
    final_state = proof["state"]
    assert all(task["status"] == "complete" for task in final_state["tasks"].values())
    assert final_state["status"] == "complete"
