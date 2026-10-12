# LiveSpec traceability anchors
# @spec(AC-001)
# @spec(AC-002)
# @spec(AC-003)
# @spec(AC-004)
# @spec(AC-005)
# @spec(AC-011)

"""Corpus test: every builtin expectations file parses and is well-formed.

# @spec AC-002, AC-003 — .specs/features/039-command-expectations-and-verify-output/spec.md
"""

from __future__ import annotations

from pathlib import Path

import pytest

from validator.command_registry import discover_commands
from validator.expectations import REQUIRED_SECTIONS, parse_expectations

SKILLS_DIR = Path(__file__).resolve().parents[1] / ".agent-sync" / "skills"
MIN_REVIEW_DATE = "2026-05-12"

# Every builtin discovered by the registry must ship a well-formed contract; the
# frozen inventory itself (AC-002) is pinned by tests/test_agent_sync_layout.py.
BUILTIN_COMMANDS: tuple[str, ...] = tuple(command.name for command in discover_commands(SKILLS_DIR))


@pytest.mark.parametrize("cmd", BUILTIN_COMMANDS)
def test_all_builtins_parse(cmd: str):
    path = SKILLS_DIR / cmd / "expectations.md"
    exp = parse_expectations(path)
    assert exp.command == cmd
    assert set(exp.prose_sections) == set(REQUIRED_SECTIONS)


@pytest.mark.parametrize("cmd", BUILTIN_COMMANDS)
def test_builtins_last_reviewed_is_not_stale(cmd: str):
    path = SKILLS_DIR / cmd / "expectations.md"
    exp = parse_expectations(path)
    assert exp.last_reviewed >= MIN_REVIEW_DATE


@pytest.mark.parametrize("cmd", BUILTIN_COMMANDS)
def test_builtins_have_must_and_must_not_rules(cmd: str):
    path = SKILLS_DIR / cmd / "expectations.md"
    exp = parse_expectations(path)
    # Every contract should at least forbid a Traceback.
    must_not_payloads = [str(r.payload) for r in exp.verify.must_not]
    assert any("Traceback" in p for p in must_not_payloads), cmd
