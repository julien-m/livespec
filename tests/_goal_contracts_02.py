"""Preserved test cases and fixtures for test_goal_contracts.py."""

from __future__ import annotations

from pathlib import Path

from tests._goal_contracts_01 import _fixture_roots
from validator.conventions_gate import GateResult, GateVerdict, GateViolation
from validator.conventions_gates import gates_path
from validator.conventions_receipt import write_conventions_receipt
from validator.goal_contracts import (
    compile_command_goal,
    normalize_goal_flags,
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
    _write_check_fix_files_01(project_root, feature_dir, feature)
    _write_check_fix_files_02(project_root, feature_dir, feature)
    _write_check_fix_files_03(project_root, feature_dir, feature)
    _write_check_fix_files_04(project_root, feature_dir, feature)
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


def _write_check_fix_files_01(project_root: Path, feature_dir: Path, feature: str) -> None:
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


def _write_check_fix_files_02(project_root: Path, feature_dir: Path, feature: str) -> None:
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


def _write_check_fix_files_03(project_root: Path, feature_dir: Path, feature: str) -> None:
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


def _write_check_fix_files_04(project_root: Path, feature_dir: Path, feature: str) -> None:
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
