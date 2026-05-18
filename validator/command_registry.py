"""Canonical registry for LiveSpec slash command skills.

# @spec FR-001: canonical command registry
#   — .specs/features/048-command-validation-hardening/spec.md#fr-001
# @spec FR-002: command discovery
#   — .specs/features/048-command-validation-hardening/spec.md#fr-002
# @spec FR-001: hyphenated canonical names
#   — .specs/features/049-command-naming-normalization/spec.md#fr-001
# @spec FR-003: alias resolution
#   — .specs/features/049-command-naming-normalization/spec.md#fr-003
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


@dataclass(frozen=True)
class CommandInfo:
    """Resolved command metadata from the agent-sync skill source tree."""

    name: str
    command_path: Path
    expectations_path: Path
    canonical_slash: str
    legacy_slashes: tuple[str, ...]

    @property
    def dotted_slash(self) -> str:
        """Return the legacy dotted slash command."""
        return f"/spec.{short_command_name(self.name)}"

    @property
    def short_name(self) -> str:
        """Return the command name without the canonical ``spec-`` prefix."""
        return short_command_name(self.name)


class CommandNamingPolicy(StrEnum):
    """Supported command naming policies for audits and migrations."""

    DOTTED = "dotted"
    HYPHENATED = "hyphenated"

    def canonical_for(self, command_name: str) -> str:
        """Return the canonical slash spelling for a command name."""
        short_name = short_command_name(command_name)
        if self is CommandNamingPolicy.DOTTED:
            return f"/spec.{short_name}"
        return canonical_command_name(command_name, with_slash=True)

    def is_canonical(self, slash_name: str) -> bool:
        """Return True when ``slash_name`` follows this policy."""
        if self is CommandNamingPolicy.DOTTED:
            return slash_name.startswith("/spec.")
        return slash_name.startswith("/spec-")


def discover_commands(
    commands_dir: Path,
    *,
    naming_policy: CommandNamingPolicy = CommandNamingPolicy.HYPHENATED,
) -> list[CommandInfo]:
    """Discover command skills or legacy command files.

    Args:
        commands_dir: ``.agent-sync/skills`` or legacy ``commands`` source dir.
        naming_policy: Naming policy used for the canonical slash spelling.

    Returns:
        Sorted command metadata. Sidecars matching ``*.expectations.md`` are
        excluded from command discovery.
    """
    if not commands_dir.is_dir():
        return []
    if (commands_dir / "spec-check" / "SKILL.md").exists():
        return _discover_agent_sync_skills(commands_dir, naming_policy=naming_policy)
    return _discover_legacy_command_files(commands_dir, naming_policy=naming_policy)


def _discover_agent_sync_skills(
    skills_dir: Path,
    *,
    naming_policy: CommandNamingPolicy,
) -> list[CommandInfo]:
    """Discover canonical command skills from ``.agent-sync/skills``."""
    commands: list[CommandInfo] = []
    for skill_dir in sorted(skills_dir.glob("spec-*")):
        if not skill_dir.is_dir():
            continue
        name = canonical_command_name(skill_dir.name)
        commands.append(
            CommandInfo(
                name=name,
                command_path=skill_dir / "SKILL.md",
                expectations_path=skill_dir / "expectations.md",
                canonical_slash=naming_policy.canonical_for(name),
                legacy_slashes=(f"/spec.{short_command_name(name)}",),
            )
        )
    return commands


def _discover_legacy_command_files(
    commands_dir: Path,
    *,
    naming_policy: CommandNamingPolicy,
) -> list[CommandInfo]:
    """Discover command files from the pre-agent-sync ``commands`` layout."""
    commands: list[CommandInfo] = []
    for command_path in sorted(commands_dir.glob("*.md")):
        stem = command_path.stem
        if stem.endswith(".expectations"):
            continue
        name = canonical_command_name(stem)
        commands.append(
            CommandInfo(
                name=name,
                command_path=command_path,
                expectations_path=_legacy_expectations_path_for(
                    commands_dir,
                    command_path.stem,
                ),
                canonical_slash=naming_policy.canonical_for(name),
                legacy_slashes=(f"/spec.{short_command_name(name)}",),
            )
        )
    return commands


def canonical_command_name(raw_name: str, *, with_slash: bool = False) -> str:
    """Return the canonical ``spec-<name>`` command spelling."""
    name = raw_name.strip()
    if name.startswith("/"):
        name = name[1:]
    if name.startswith("spec."):
        name = f"spec-{name.removeprefix('spec.')}"
    elif not name.startswith("spec-"):
        name = f"spec-{name}"
    return f"/{name}" if with_slash else name


def short_command_name(raw_name: str) -> str:
    """Return the command name without ``spec-`` or ``spec.``."""
    name = raw_name.strip()
    if name.startswith("/"):
        name = name[1:]
    if name.startswith("spec."):
        return name.removeprefix("spec.")
    if name.startswith("spec-"):
        return name.removeprefix("spec-")
    return name


def _legacy_expectations_path_for(commands_dir: Path, command_stem: str) -> Path:
    """Return sidecar path matching canonical and legacy command sources."""
    canonical_stem = canonical_command_name(command_stem)
    canonical_path = commands_dir / f"{canonical_stem}.expectations.md"
    if command_stem.startswith("spec-") or canonical_path.exists():
        return canonical_path
    return commands_dir / f"{command_stem}.expectations.md"


def normalize_command_name(raw_name: str) -> str:
    """Normalize command IDs and slash aliases to the registry command name.

    Args:
        raw_name: A bare ID (``feature``), dotted alias (``/spec.feature``),
            or hyphenated alias (``/spec-feature``).

    Returns:
        Bare command ID used for file and expectations lookup.
    """
    return canonical_command_name(raw_name)


def valid_command_names(commands_dir: Path) -> frozenset[str]:
    """Return all command names from ``commands_dir``."""
    return frozenset(command.name for command in discover_commands(commands_dir))


__all__ = [
    "CommandInfo",
    "CommandNamingPolicy",
    "canonical_command_name",
    "discover_commands",
    "normalize_command_name",
    "short_command_name",
    "valid_command_names",
]
