"""Unit tests for flow → spec conversion."""

from __future__ import annotations

from pathlib import Path

from validator.brainstorm.convert import (
    build_changelog,
    convert_flow_to_spec,
    inject_screens_section,
)

_FLOW = """---
flow: login
title: Login Flow
status: ready
priority: P1
mockups:
  - mobile_login
surfaces:
  - mobile
source:
  - figma
generated_at: 2026-04-29
---

# Flow Spec: Login

## Input

User wants to authenticate.

## Acceptance Criteria

| ID | Criterion |
|---|---|
| AC-001 | login works |
| AC-002 | password reset |

## Functional Requirements

| ID | Requirement |
|---|---|
| FR-001 | login form |

## Success Criteria

| ID | Criterion |
|---|---|
| SC-001 | 99% success |
"""


def test_h1_rewritten(tmp_path: Path) -> None:
    p = tmp_path / "login.md"
    p.write_text(_FLOW, encoding="utf-8")
    out = convert_flow_to_spec(p, "001", "login", "2026-04-29")
    assert out.startswith("# Feature Spec: Login")
    assert "# Flow Spec:" not in out


def test_id_preservation(tmp_path: Path) -> None:
    """AC/FR/SC IDs are preserved byte-for-byte."""
    p = tmp_path / "login.md"
    p.write_text(_FLOW, encoding="utf-8")
    out = convert_flow_to_spec(p, "001", "login", "2026-04-29")
    for ident in ("AC-001", "AC-002", "FR-001", "SC-001"):
        assert ident in out


def test_header_injected(tmp_path: Path) -> None:
    p = tmp_path / "login.md"
    p.write_text(_FLOW, encoding="utf-8")
    out = convert_flow_to_spec(p, "001", "login", "2026-04-29")
    assert "**Branch:** `feature/001-login`" in out
    assert "**Status:** Draft" in out
    assert "**Feature Number:** 001" in out


def test_input_extracted(tmp_path: Path) -> None:
    p = tmp_path / "login.md"
    p.write_text(_FLOW, encoding="utf-8")
    out = convert_flow_to_spec(p, "001", "login", "2026-04-29")
    assert "User wants to authenticate" in out


def test_frontmatter_stripped(tmp_path: Path) -> None:
    p = tmp_path / "login.md"
    p.write_text(_FLOW, encoding="utf-8")
    out = convert_flow_to_spec(p, "001", "login", "2026-04-29")
    assert "generated_at:" not in out
    assert not out.startswith("---")


def test_screens_with_mockups() -> None:
    spec = "# Feature Spec: X\n\n- **Branch:** x\n"
    out = inject_screens_section(spec, ["mobile_login", "web_dashboard"], "001", "x")
    assert "## Screens" in out
    assert "design/screens/001-x/mobile_login.png" in out
    assert "design/screens/001-x/web_dashboard.png" in out


def test_empty_mockups_placeholder() -> None:
    """Empty mockup list → 'À designer' placeholder."""
    spec = "# Feature Spec: X\n\n"
    out = inject_screens_section(spec, [], "001", "x")
    assert "À designer" in out


def test_changelog_initial_entry() -> None:
    cl = build_changelog("login", "2026-04-29")
    assert "Feature created from brainstorm flow `login`" in cl
    assert "## 2026-04-29" in cl
