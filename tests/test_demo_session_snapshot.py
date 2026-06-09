# LiveSpec traceability anchors
# @spec(AC-003)
# @spec(AC-005)
# @spec(AC-006)
# @spec(AC-007)
# @spec(AC-011)

"""Snapshot tests for AC-011 — init, test, feature have complete Section 13.

# @spec AC-011: 3 expectations files have complete Section 13
#   — .specs/features/040-expectations-rich-and-verify-preview/spec.md#ac-011
"""

from __future__ import annotations

from pathlib import Path

import pytest

from validator.expectations import (
    SECTION13_MIN_CONTENT_LINES,
    SECTION13_SUBSECTIONS,
    parse_expectations,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
PRIORITY_COMMANDS = ("spec-init", "spec-test", "spec-feature")


def _count_content_lines(body: str) -> int:
    count = 0
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("<!--") and stripped.endswith("-->"):
            continue
        count += 1
    return count


@pytest.mark.parametrize("command", PRIORITY_COMMANDS)
def test_priority_command_has_full_section_13(command: str) -> None:
    path = REPO_ROOT / ".agent-sync" / "skills" / command / "expectations.md"
    expectations = parse_expectations(path)
    assert expectations.demo_session is not None, f"{command}: no demo session"
    sub_map = expectations.demo_session.as_mapping()
    assert set(sub_map.keys()) == set(SECTION13_SUBSECTIONS), (
        f"{command}: missing sub-sections {set(SECTION13_SUBSECTIONS) - set(sub_map.keys())}"
    )
    for name, body in sub_map.items():
        lines = _count_content_lines(body)
        assert lines >= SECTION13_MIN_CONTENT_LINES, (
            f"{command}: sub-section {name!r} has only {lines} content lines"
        )
