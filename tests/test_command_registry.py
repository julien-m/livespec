"""Tests for the canonical LiveSpec command registry."""

from __future__ import annotations

from pathlib import Path

from validator.command_registry import (
    CommandNamingPolicy,
    discover_commands,
    normalize_command_name,
)


def test_discovers_all_builtin_commands() -> None:
    commands = discover_commands(Path(".agent-sync/skills"))

    assert len(commands) == 20
    assert {command.name for command in commands} >= {
        "spec-check",
        "spec-explain",
        "spec-feature",
    }
    assert all(command.command_path.is_file() for command in commands)
    assert all(command.expectations_path.is_file() for command in commands)
    assert all(command.command_path.name == "SKILL.md" for command in commands)
    assert all(
        command.expectations_path.name == "expectations.md"
        for command in commands
    )


def test_hyphenated_slash_names_are_canonical_with_dotted_aliases() -> None:
    command = next(
        c for c in discover_commands(Path(".agent-sync/skills")) if c.name == "spec-feature"
    )

    assert command.canonical_slash == "/spec-feature"
    assert command.command_path == Path(".agent-sync/skills/spec-feature/SKILL.md")
    assert command.expectations_path == Path(
        ".agent-sync/skills/spec-feature/expectations.md"
    )
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
    for command in discover_commands(Path(".agent-sync/skills")):
        assert normalize_command_name(command.name) == command.name
        assert normalize_command_name(f"/spec.{command.short_name}") == command.name
        assert normalize_command_name(f"/spec-{command.short_name}") == command.name
        assert command.legacy_slashes == (f"/spec.{command.short_name}",)


def test_naming_policy_rejects_dotted_canonical_names() -> None:
    assert CommandNamingPolicy.HYPHENATED.canonical_for("check") == "/spec-check"
    assert CommandNamingPolicy.HYPHENATED.is_canonical("/spec-check")
    assert not CommandNamingPolicy.HYPHENATED.is_canonical("/spec.check")
