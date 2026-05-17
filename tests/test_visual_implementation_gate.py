"""Regression tests for mandatory visual certification during implementation.

# @spec FR-006: Regression tests
#   — .specs/features/046-visual-implementation-gate/spec.md#fr-006
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_implement_requires_visual_gate_before_final_status() -> None:
    """AC-001/AC-002: UI features run /spec.test --visual before finalization."""
    body = _read("commands/implement.md")

    assert "Phase 6.5 — Mandatory Visual Gate" in body
    assert "/spec.test <feature> --auto --visual" in body
    assert "before Phase 7" in body
    assert "before Phase 8.5" in body
    assert "Visual Gate Verdict: PASS" in body


def test_visual_tooling_failure_blocks_implementation() -> None:
    """AC-003: unavailable visual tooling cannot silently pass UI features."""
    body = _read("commands/implement.md")

    assert "Visual tooling unavailable on a UI feature is BLOCKED" in body
    assert "do not continue without blocking" in body
    assert "status remains `In Progress`" in body
    old_skip_message = (
        'Visual baselines skipped — Playwright not installed" and continue without blocking'
    )
    assert old_skip_message not in body


def test_no_visual_flag_caps_ui_feature_at_in_progress() -> None:
    """AC-004: --no-visual is allowed for partial work only."""
    body = _read("commands/implement.md")

    assert "`--no-visual` on a visual feature" in body
    assert "must set Status to `In Progress`" in body
    assert "never `Implemented`" in body


def test_spec_test_exposes_structured_visual_gate_verdict() -> None:
    """AC-005: /spec.test provides a verdict consumable by /spec.implement."""
    body = _read("commands/test.md")

    assert "### Visual Gate Verdict" in body
    assert "PASS | FAIL | BLOCKED" in body
    assert "Consumed by `/spec.implement` Phase 6.5" in body
    assert "exit code 0 only for PASS" in body


def test_expectations_contracts_describe_visual_gate() -> None:
    """AC-006: command expectation contracts stay aligned with visual gating."""
    implement = _read("commands/implement.expectations.md")
    test = _read("commands/test.expectations.md")

    assert "Visual Gate Verdict" in implement
    assert "/spec.test <feature> --auto --visual" in implement
    assert "visual gate passed before final status" in implement

    assert "Visual Gate Verdict" in test
    assert "PASS | FAIL | BLOCKED" in test
