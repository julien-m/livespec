"""Corpus test: every builtin expectations file parses and is well-formed.

# @spec AC-002, AC-003 — .specs/features/039-command-expectations-and-verify-output/spec.md
"""

from __future__ import annotations

from pathlib import Path

import pytest

from validator.expectations import REQUIRED_SECTIONS, parse_expectations

SKILLS_DIR = Path(__file__).resolve().parents[1] / ".agent-sync" / "skills"
MIN_REVIEW_DATE = "2026-05-12"

# The command invariant enumerated by AC-002.
EXPECTED_COMMANDS: tuple[str, ...] = (
    "spec-init",
    "spec-migrate",
    "spec-propose",
    "spec-specify",
    "spec-plan",
    "spec-implement",
    "spec-test",
    "spec-check",
    "spec-fix",
    "spec-explain",
    "spec-stack",
    "spec-feature",
    "spec-ship",
    "spec-preflight",
    "spec-hooks",
    "spec-play-coverage",
    "spec-refine",
    "spec-status",
    "spec-refresh-conventions",
    "spec-refresh-from-brainstorm",
    "spec-verify-output",
)


def test_builtin_files_exist():
    for cmd in EXPECTED_COMMANDS:
        assert (SKILLS_DIR / cmd / "expectations.md").exists(), cmd


def test_ac002_enumerated_commands_have_expectations():
    """AC-002 freezes the builtin command expectations list."""
    for cmd in EXPECTED_COMMANDS:
        assert (SKILLS_DIR / cmd / "expectations.md").exists()


@pytest.mark.parametrize("cmd", EXPECTED_COMMANDS)
def test_all_builtins_parse(cmd: str):
    path = SKILLS_DIR / cmd / "expectations.md"
    exp = parse_expectations(path)
    assert exp.command == cmd
    assert set(exp.prose_sections) == set(REQUIRED_SECTIONS)


@pytest.mark.parametrize("cmd", EXPECTED_COMMANDS)
def test_builtins_last_reviewed_is_not_stale(cmd: str):
    path = SKILLS_DIR / cmd / "expectations.md"
    exp = parse_expectations(path)
    assert exp.last_reviewed >= MIN_REVIEW_DATE


@pytest.mark.parametrize("cmd", EXPECTED_COMMANDS)
def test_builtins_have_must_and_must_not_rules(cmd: str):
    path = SKILLS_DIR / cmd / "expectations.md"
    exp = parse_expectations(path)
    # Every contract should at least forbid a Traceback.
    must_not_payloads = [str(r.payload) for r in exp.verify.must_not]
    assert any("Traceback" in p for p in must_not_payloads), cmd
