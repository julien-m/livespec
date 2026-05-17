"""Corpus test: every builtin expectations file parses and is well-formed.

# @spec AC-002, AC-003 — .specs/features/039-command-expectations-and-verify-output/spec.md
"""

from __future__ import annotations

from pathlib import Path

import pytest

from validator.expectations import REQUIRED_SECTIONS, parse_expectations

COMMANDS_DIR = Path(__file__).resolve().parents[1] / "commands"
MIN_REVIEW_DATE = "2026-05-12"

# The 19-command invariant enumerated by AC-002, plus the 20th (verify-output)
# acknowledged in the feature changelog and spec-system.md `### Command discovery`.
EXPECTED_COMMANDS: tuple[str, ...] = (
    "init",
    "migrate",
    "propose",
    "specify",
    "plan",
    "implement",
    "test",
    "check",
    "fix",
    "explain",
    "stack",
    "feature",
    "ship",
    "preflight",
    "hooks",
    "play-coverage",
    "refine",
    "status",
    "refresh-conventions",
    "verify-output",
)


def test_20_builtin_files_exist():
    for cmd in EXPECTED_COMMANDS:
        assert (COMMANDS_DIR / f"{cmd}.expectations.md").exists(), cmd


def test_ac002_19_enumerated_commands_have_expectations():
    """AC-002 freezes the 19-command list (verify-output is the 20th)."""
    for cmd in EXPECTED_COMMANDS[:19]:
        assert (COMMANDS_DIR / f"{cmd}.expectations.md").exists()


@pytest.mark.parametrize("cmd", EXPECTED_COMMANDS)
def test_all_builtins_parse(cmd: str):
    path = COMMANDS_DIR / f"{cmd}.expectations.md"
    exp = parse_expectations(path)
    assert exp.command == cmd
    assert set(exp.prose_sections) == set(REQUIRED_SECTIONS)


@pytest.mark.parametrize("cmd", EXPECTED_COMMANDS)
def test_builtins_last_reviewed_is_not_stale(cmd: str):
    path = COMMANDS_DIR / f"{cmd}.expectations.md"
    exp = parse_expectations(path)
    assert exp.last_reviewed >= MIN_REVIEW_DATE


@pytest.mark.parametrize("cmd", EXPECTED_COMMANDS)
def test_builtins_have_must_and_must_not_rules(cmd: str):
    path = COMMANDS_DIR / f"{cmd}.expectations.md"
    exp = parse_expectations(path)
    # Every contract should at least forbid a Traceback.
    must_not_payloads = [str(r.payload) for r in exp.verify.must_not]
    assert any("Traceback" in p for p in must_not_payloads), cmd
