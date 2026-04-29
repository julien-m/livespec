"""Integration tests for the two-phase apply pipeline."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from validator.brainstorm.apply import apply_plan, build_plan
from validator.brainstorm.grammar import validate_all

_VALID_FLOW = """---
flow: {flow}
title: {title}
status: ready
priority: {priority}
mockups:
{mockups}
surfaces:
  - mobile
source:
  - figma
generated_at: 2026-04-29
---

# Flow Spec: {title}

## Input

Test input.

## User Scenarios & Testing

- AC-001: works

## Acceptance Criteria

| ID | Criterion |
|---|---|
| AC-001 | works |

## Functional Requirements

| ID | Requirement |
|---|---|
| FR-001 | does the thing |

## Key Entities

- Thing

## Edge Cases

- none

## Success Criteria

| ID | Criterion |
|---|---|
| SC-001 | 100% |
"""


def _make_flow(
    flow: str, title: str, priority: str = "P1", mockups: list[str] | None = None
) -> str:
    refs = mockups or []
    mockup_yaml = (
        "  - " + "\n  - ".join(refs) if refs else "  []"
    )
    if not refs:
        # `mockups: []` inline form
        return _VALID_FLOW.format(
            flow=flow, title=title, priority=priority, mockups="  []"
        ).replace("mockups:\n  []", "mockups: []")
    return _VALID_FLOW.format(
        flow=flow, title=title, priority=priority, mockups=mockup_yaml
    )


def _setup_fixture(tmp_path: Path, with_profile: bool = True) -> Path:
    flows = tmp_path / "specs" / "flows"
    flows.mkdir(parents=True)
    (flows / "login.md").write_text(
        _make_flow("login", "Login", "P1", ["mobile_login"]), encoding="utf-8"
    )
    (flows / "checkout.md").write_text(
        _make_flow("checkout", "Checkout", "P2", ["web_checkout"]), encoding="utf-8"
    )
    mockups = tmp_path / "mockups"
    mockups.mkdir()
    (mockups / "mobile_login.png").write_bytes(b"\x89PNG\r\n\x1a\nfake1")
    (mockups / "web_checkout.png").write_bytes(b"\x89PNG\r\n\x1a\nfake2")
    (mockups / "manifest.json").write_text(
        json.dumps({"schemaVersion": 2, "exports": []}),
        encoding="utf-8",
    )
    if with_profile:
        (tmp_path / "project-profile.md").write_text(
            "# Project Profile\n\n## Name\n\nTest App\n\n"
            "## Vision\n\nA test\n\n## Audience\n\nDevs\n\n"
            "## Constraints\n\nNone\n\n## Stack\n\nPython\n",
            encoding="utf-8",
        )
    return tmp_path


def _sha256_dir(d: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in sorted(d.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(d))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def test_init_full_ingest(tmp_path: Path) -> None:
    _setup_fixture(tmp_path)
    report = validate_all(tmp_path)
    assert report.ok, report.all_violations
    plan = build_plan(tmp_path, "init", report)
    apply_plan(plan)

    specs = tmp_path / ".specs"
    assert specs.exists()
    assert (specs / "features" / "001-checkout" / "spec.md").exists() or (
        specs / "features" / "001-login" / "spec.md"
    ).exists()
    assert (specs / "roadmap.md").exists()
    assert (specs / "project.md").exists()
    assert (specs / "stacks" / "_default.md").exists()
    assert (specs / "design" / "screens" / "mobile_login.png").exists()
    assert not (specs / "manifest.json").exists()


def test_manifest_skipped(tmp_path: Path) -> None:
    """`mockups/manifest.json` is never copied (FR-008 / AC-008)."""
    _setup_fixture(tmp_path)
    report = validate_all(tmp_path)
    plan = build_plan(tmp_path, "init", report)
    apply_plan(plan)
    assert not (tmp_path / ".specs" / "manifest.json").exists()
    assert not list((tmp_path / ".specs").rglob("manifest.json"))


def test_source_mockups_unchanged(tmp_path: Path) -> None:
    """Source `mockups/` directory is byte-identical after apply (SC-005)."""
    _setup_fixture(tmp_path)
    before = _sha256_dir(tmp_path / "mockups")
    report = validate_all(tmp_path)
    plan = build_plan(tmp_path, "init", report)
    apply_plan(plan)
    after = _sha256_dir(tmp_path / "mockups")
    assert before == after


@pytest.mark.chaos
def test_atomic_abort_on_apply_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mid-apply IOError → staging destroyed, .specs/ untouched."""
    _setup_fixture(tmp_path)
    report = validate_all(tmp_path)
    plan = build_plan(tmp_path, "init", report)

    import shutil as shutil_mod

    real_copy = shutil_mod.copy2
    call_count = {"n": 0}

    def boom(*a: object, **kw: object) -> object:
        call_count["n"] += 1
        if call_count["n"] >= 2:
            raise OSError("simulated failure mid-apply")
        return real_copy(*a, **kw)  # type: ignore[arg-type]

    monkeypatch.setattr("validator.brainstorm.apply.shutil.copy2", boom)
    with pytest.raises(OSError):
        apply_plan(plan)
    assert not (tmp_path / ".specs").exists()
    # staging dir cleaned up
    leftovers = list(tmp_path.glob(".livespec-staging-*"))
    assert not leftovers


def test_refine_skips_existing_slugs(tmp_path: Path) -> None:
    """Refine mode preserves existing features."""
    _setup_fixture(tmp_path)
    report = validate_all(tmp_path)
    plan_init = build_plan(tmp_path, "init", report)
    apply_plan(plan_init)

    # Add a new flow and re-import in refine mode.
    new_flow = tmp_path / "specs" / "flows" / "billing.md"
    new_flow.write_text(_make_flow("billing", "Billing", "P2", []), encoding="utf-8")

    report2 = validate_all(tmp_path)
    plan_refine = build_plan(tmp_path, "refine", report2)
    # login + checkout already exist, billing is new
    new_slugs = {op.slug for op in plan_refine.flow_ops}
    assert "billing" in new_slugs
    assert "login" not in new_slugs
    assert "checkout" not in new_slugs

    apply_plan(plan_refine)
    assert any(
        d.name.endswith("-billing") for d in (tmp_path / ".specs" / "features").iterdir()
    )


def test_empty_mockups_flow_still_ingests(tmp_path: Path) -> None:
    """Flow with empty mockups still produces a feature with 'À designer'."""
    flows = tmp_path / "specs" / "flows"
    flows.mkdir(parents=True)
    (flows / "settings.md").write_text(
        _make_flow("settings", "Settings", "P2", []), encoding="utf-8"
    )
    (tmp_path / "mockups").mkdir()
    report = validate_all(tmp_path)
    assert report.ok, report.all_violations
    plan = build_plan(tmp_path, "init", report)
    apply_plan(plan)
    spec = (tmp_path / ".specs" / "features" / "001-settings" / "spec.md").read_text()
    assert "À designer" in spec
