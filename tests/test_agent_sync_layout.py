# LiveSpec traceability anchors
# @spec(AC-001)
# @spec(AC-002)
# @spec(AC-003)
# @spec(AC-045)

"""Tests for LiveSpec's canonical agent-sync source layout.

This module owns the builtin command inventory. Expectations identity and
well-formedness per command are checked in ``test_builtin_expectations_corpus.py``.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from validator.command_registry import discover_commands

AGENT_SYNC = Path(__file__).resolve().parent.parent / ".agent-sync"
EXPECTED_SPEC_COMMANDS = {
    "spec-check",
    "spec-doctor",
    "spec-explain",
    "spec-feature",
    "spec-fix",
    "spec-hooks",
    "spec-implement",
    "spec-init",
    "spec-journey",
    "spec-migrate",
    "spec-plan",
    "spec-play-coverage",
    "spec-preflight",
    "spec-propose",
    "spec-refine",
    "spec-refresh-conventions",
    "spec-refresh-from-brainstorm",
    "spec-ship",
    "spec-specify",
    "spec-stack",
    "spec-status",
    "spec-test",
    "spec-verify-output",
}


def test_command_registry_discovers_every_builtin_skill() -> None:
    """The registry exposes exactly the builtin skills, each with SKILL.md + expectations."""
    commands = discover_commands(AGENT_SYNC / "skills")

    assert {command.name for command in commands} == EXPECTED_SPEC_COMMANDS
    for command in commands:
        assert command.command_path == AGENT_SYNC / "skills" / command.name / "SKILL.md"
        assert command.command_path.is_file(), command.name
        assert command.expectations_path.is_file(), command.name


def test_agent_sync_contains_portable_agents() -> None:
    agents = {path.name for path in sorted((AGENT_SYNC / "agents").glob("livespec-*"))}

    assert agents == {
        "livespec-documenter",
        "livespec-implementer",
        "livespec-supervisor",
        "livespec-verifier",
    }
    for name in agents:
        root = AGENT_SYNC / "agents" / name
        assert (root / "agent.yaml").is_file()
        assert (root / "prompt.md").is_file()
        payload = yaml.safe_load((root / "agent.yaml").read_text(encoding="utf-8"))
        assert payload["name"] == name


def test_agent_sync_contains_livespec_rules() -> None:
    rules = sorted((AGENT_SYNC / "rules" / "livespec").glob("*.md"))

    assert {rule.name for rule in rules} >= {"routing.md", "commands.md"}
