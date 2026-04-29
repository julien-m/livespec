"""Unit tests for brainstorm flow grammar validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from validator.brainstorm.grammar import validate_all, validate_flow

_VALID_FLOW = """---
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

## User Scenarios & Testing

- AC-001: user logs in

## Acceptance Criteria

| ID | Criterion |
|---|---|
| AC-001 | login works |

## Functional Requirements

| ID | Requirement |
|---|---|
| FR-001 | login form |

## Key Entities

- User

## Edge Cases

- bad password

## Success Criteria

| ID | Criterion |
|---|---|
| SC-001 | 99% success |
"""


def _write(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


def test_valid_flow_passes(tmp_path: Path) -> None:
    p = _write(tmp_path, "login.md", _VALID_FLOW)
    result = validate_flow(p)
    assert result.ok, result.violations


def test_missing_section(tmp_path: Path) -> None:
    """Removing the AC section yields a SECTION_MISSING violation."""
    body = _VALID_FLOW.replace("## Acceptance Criteria", "## Renamed")
    p = _write(tmp_path, "broken.md", body)
    result = validate_flow(p)
    assert any(v.rule_id == "SECTION_MISSING" for v in result.violations)


def test_missing_frontmatter_field(tmp_path: Path) -> None:
    body = _VALID_FLOW.replace("priority: P1\n", "")
    p = _write(tmp_path, "incomplete.md", body)
    result = validate_flow(p)
    assert any(
        v.rule_id == "FRONTMATTER_MISSING_FIELD" and "priority" in v.message
        for v in result.violations
    )


def test_empty_surfaces_rejected(tmp_path: Path) -> None:
    """Finding #4: empty surfaces array is a hard violation."""
    body = _VALID_FLOW.replace(
        "surfaces:\n  - mobile\n",
        "surfaces: []\n",
    )
    p = _write(tmp_path, "no_surfaces.md", body)
    result = validate_flow(p)
    assert any(v.rule_id == "FRONTMATTER_EMPTY_SURFACES" for v in result.violations)


def test_missing_mockup_blocks(tmp_path: Path) -> None:
    """Mockup referenced but missing on disk is a BLOCKING violation."""
    flows = tmp_path / "specs" / "flows"
    flows.mkdir(parents=True)
    (flows / "login.md").write_text(_VALID_FLOW, encoding="utf-8")
    # No mockups dir, no mobile_login.png
    (tmp_path / "mockups").mkdir()
    report = validate_all(tmp_path)
    assert any(v.rule_id == "MOCKUP_MISSING" for v in report.all_violations)


def test_no_ids_violation(tmp_path: Path) -> None:
    body = _VALID_FLOW.replace("AC-001", "TBD").replace("FR-001", "TBD2").replace(
        "SC-001", "TBD3"
    )
    p = _write(tmp_path, "no_ids.md", body)
    result = validate_flow(p)
    assert any(v.rule_id == "IDS_MISSING" for v in result.violations)


def test_missing_file(tmp_path: Path) -> None:
    p = tmp_path / "ghost.md"
    result = validate_flow(p)
    assert any(v.rule_id == "FILE_MISSING" for v in result.violations)


@pytest.mark.chaos
def test_chaos_atomic_abort(tmp_path: Path) -> None:
    """Any violation aborts before any write — no .specs/ produced."""
    flows = tmp_path / "specs" / "flows"
    flows.mkdir(parents=True)
    (flows / "broken.md").write_text(
        _VALID_FLOW.replace("## Acceptance Criteria", "## Wrong"),
        encoding="utf-8",
    )
    report = validate_all(tmp_path)
    assert not report.ok
    assert not (tmp_path / ".specs").exists()
