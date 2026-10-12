# LiveSpec traceability anchors
# @spec(AC-001)
# @spec(AC-002)
# @spec(AC-003)
# @spec(AC-008)
# @spec(AC-009)
# @spec(AC-011)
# @spec(AC-045)
# @spec(FR-010)
# @spec(FR-011)

"""Tests for the canonical LiveSpec command registry."""

from __future__ import annotations

from pathlib import Path

from validator.command_registry import (
    CommandNamingPolicy,
    discover_commands,
    normalize_command_name,
)

# The builtin inventory itself is pinned by tests/test_agent_sync_layout.py.
SKILLS_DIR = Path(__file__).resolve().parent.parent / ".agent-sync" / "skills"


def test_hyphenated_slash_names_are_canonical_with_dotted_aliases() -> None:
    command = next(c for c in discover_commands(SKILLS_DIR) if c.name == "spec-feature")

    assert command.canonical_slash == "/spec-feature"
    assert command.command_path == SKILLS_DIR / "spec-feature" / "SKILL.md"
    assert command.expectations_path == SKILLS_DIR / "spec-feature" / "expectations.md"
    assert "/spec.feature" in command.legacy_slashes


def test_discovers_legacy_command_files_but_exposes_logical_name(tmp_path: Path) -> None:
    commands_dir = tmp_path / "commands"
    commands_dir.mkdir()
    (commands_dir / "demo.md").write_text("# Demo\n", encoding="utf-8")

    commands = discover_commands(commands_dir)

    assert len(commands) == 1
    assert commands[0].name == "spec-demo"
    assert commands[0].command_path == commands_dir / "demo.md"
    assert commands[0].expectations_path == commands_dir / "demo.expectations.md"


def test_normalize_command_name_accepts_ids_and_slash_aliases() -> None:
    assert normalize_command_name("feature") == "spec-feature"
    assert normalize_command_name("spec.feature") == "spec-feature"
    assert normalize_command_name("/spec-feature") == "spec-feature"
    assert normalize_command_name("spec-feature") == "spec-feature"
    assert normalize_command_name("/spec-feature") == "spec-feature"


def test_every_builtin_command_has_dotted_and_hyphenated_aliases() -> None:
    for command in discover_commands(SKILLS_DIR):
        assert normalize_command_name(command.name) == command.name
        assert normalize_command_name(f"/spec.{command.short_name}") == command.name
        assert normalize_command_name(f"/spec-{command.short_name}") == command.name
        assert command.legacy_slashes == (f"/spec.{command.short_name}",)


def test_naming_policy_rejects_dotted_canonical_names() -> None:
    assert CommandNamingPolicy.HYPHENATED.canonical_for("check") == "/spec-check"
    assert CommandNamingPolicy.HYPHENATED.is_canonical("/spec-check")
    assert not CommandNamingPolicy.HYPHENATED.is_canonical("/spec.check")
