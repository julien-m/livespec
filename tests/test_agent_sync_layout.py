"""Tests for LiveSpec's canonical agent-sync source layout."""

from __future__ import annotations

from pathlib import Path

import yaml

from validator.command_registry import discover_commands

AGENT_SYNC = Path(".agent-sync")
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


def test_agent_sync_contains_all_command_skills() -> None:
    skills = sorted((AGENT_SYNC / "skills").glob("spec-*"))

    assert {skill.name for skill in skills} == EXPECTED_SPEC_COMMANDS
    for skill in skills:
        assert (skill / "SKILL.md").is_file(), skill
        assert (skill / "expectations.md").is_file(), skill


def test_agent_sync_expectations_match_skill_names() -> None:
    for skill in sorted((AGENT_SYNC / "skills").glob("spec-*")):
        text = (skill / "expectations.md").read_text(encoding="utf-8")
        assert f"command: {skill.name}" in text


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


def test_command_registry_reads_agent_sync_skills() -> None:
    commands = discover_commands(AGENT_SYNC / "skills")
    feature = next(command for command in commands if command.name == "spec-feature")

    assert {command.name for command in commands} == EXPECTED_SPEC_COMMANDS
    assert feature.command_path == AGENT_SYNC / "skills" / "spec-feature" / "SKILL.md"
    assert feature.expectations_path == AGENT_SYNC / "skills" / "spec-feature" / "expectations.md"


def test_spec_migrate_documents_provider_skill_resolution() -> None:
    text = (AGENT_SYNC / "skills" / "spec-migrate" / "SKILL.md").read_text(encoding="utf-8")

    assert "~/.claude/skills/spec-migrate" in text
    assert "~/.agents/skills/spec-migrate" in text
    assert "~/.agent-sync/skills/spec-migrate" in text
    assert "~/.claude/.agent-sync" not in text
    assert "spec" + ".migrate" not in text
