"""Goal invocations responsibilities behind the public contract facade."""

from __future__ import annotations

import re
from pathlib import Path

from . import goal_contracts as _contracts

__all__ = [
    "_extract_internal_command_invocations",
    "_is_documentary_internal_invocation_reference",
    "_looks_like_executable_internal_invocation",
    "_parse_internal_invocation_line",
    "_reject_undocumented_internal_spec_invocation",
    "_validate_internal_subagent_context_guard",
    "validate_internal_command_invocation_guards",
]


def _extract_internal_command_invocations(skill_path: Path) -> list[dict[str, str]]:
    """Parse and validate executable internal slash-command invocations.

    The ``## Internal Command Invocations`` section is the machine-readable
    allowlist for nested slash calls. Executed ``/spec-*`` calls must run in an
    independent native sub-agent so each sub-command can set and complete its
    own goal. Text-only next-step hints use ``suggestion`` mode.
    """
    if not skill_path.exists():
        return []
    text = skill_path.read_text(encoding="utf-8")
    # Locate the machine-readable invocation section by its level-2 heading.
    match = re.search(
        r"^##\s+Internal Command Invocations\s*$",
        text,
        flags=re.MULTILINE,
    )
    if match is None:
        _contracts._reject_undocumented_internal_spec_invocation(skill_path, text)
        return []
    section = text[match.end() :]
    next_heading = re.search(r"^##\s+", section, flags=re.MULTILINE)
    if next_heading is not None:
        section = section[: next_heading.start()]

    return _parse_invocation_section(section, skill_path)


def _parse_invocation_section(section: str, skill_path: Path) -> list[dict[str, str]]:
    invocations: list[dict[str, str]] = []
    for line_number, line in enumerate(section.splitlines(), 1):
        parsed = _contracts._parse_internal_invocation_line(
            line,
            skill_path=skill_path,
            line_number=line_number,
        )
        if parsed is None:
            continue
        if parsed["mode"] not in _contracts.ALLOWED_INTERNAL_INVOCATION_MODES:
            raise _contracts.ExpectationsInvalid(
                skill_path.as_posix(),
                "Internal Command Invocations rows must use mode subagent or suggestion "
                f"at Internal Command Invocations line {line_number}: "
                f"{parsed['mode']}",
            )
        if parsed["mode"] == "subagent" and not parsed["command"].startswith("/spec-"):
            raise _contracts.ExpectationsInvalid(
                skill_path.as_posix(),
                "Internal Command Invocations subagent rows must execute /spec-* "
                f"commands at line {line_number}: {parsed['command']}",
            )
        if parsed["mode"] == "subagent":
            _contracts._validate_internal_subagent_context_guard(
                parsed,
                skill_path=skill_path,
                line_number=line_number,
            )
        invocations.append(parsed)
    return invocations


def validate_internal_command_invocation_guards(skill_path: Path) -> None:
    """Validate nested slash-command rows for audit callers."""
    _contracts._extract_internal_command_invocations(skill_path)


def _validate_internal_subagent_context_guard(
    invocation: dict[str, str],
    *,
    skill_path: Path,
    line_number: int,
) -> None:
    """Require project-root propagation on native nested slash-command rows."""
    haystack = " ".join((invocation["command"], invocation["purpose"])).lower()
    missing = [
        label
        for label, accepted_terms in _contracts.INTERNAL_SUBAGENT_GUARD_REQUIREMENTS
        if not any(term in haystack for term in accepted_terms)
    ]
    if not missing:
        return
    raise _contracts.ExpectationsInvalid(
        skill_path.as_posix(),
        "Internal Command Invocations subagent rows must mention project_root, "
        "cwd/working directory, and .specs/spec-system.md "
        f"at line {line_number}; missing: {', '.join(missing)}",
    )


def _reject_undocumented_internal_spec_invocation(
    skill_path: Path,
    text: str,
) -> None:
    """Reject executable nested slash commands without an allowlist section."""
    current_command = skill_path.parent.name
    in_fence = False
    for line_number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        lowered = line.lower()
        if "/spec-" not in lowered:
            continue
        if not any(verb in lowered for verb in ("run", "execute", "spawn")):
            continue
        if not _contracts._looks_like_executable_internal_invocation(stripped):
            continue
        commands = set(re.findall(r"/(spec-[a-z0-9-]+)", lowered))
        if commands and commands <= {current_command}:
            continue
        if _contracts._is_documentary_internal_invocation_reference(stripped):
            continue
        raise _contracts.ExpectationsInvalid(
            skill_path.as_posix(),
            "Executable internal /spec-* invocation requires "
            "## Internal Command Invocations "
            f"at line {line_number}: {line.strip()}",
        )


def _looks_like_executable_internal_invocation(line: str) -> bool:
    """Return True when a line directs the agent to execute a slash command."""
    normalized = re.sub(r"^[-*]\s+", "", line.strip())
    normalized = re.sub(r"^\d+\.\s+", "", normalized)
    lowered = normalized.lower()
    if lowered.startswith(("run ", "run `", "execute ", "execute `", "spawn ", "spawn `")):
        return True
    return any(
        marker in lowered
        for marker in (
            " must run ",
            " must execute ",
            " must spawn ",
            " then run ",
            " then execute ",
            " then spawn ",
        )
    )


def _is_documentary_internal_invocation_reference(line: str) -> bool:
    """Return True for examples, recovery hints, and display text, not execution."""
    lowered = line.lower()
    if line.startswith("|") or lowered.startswith((">", "#", "**")):
        return True
    documentary_markers = (
        "suggest",
        "recovery",
        "recover",
        "re-run",
        "rerun",
        "blocked",
        "error",
        "message",
        "output",
        "example",
        "usage",
        "typically run",
        "can run",
        "if `.specs/` does not exist",
        "if .specs/ does not exist",
        "does not exist",
        "not initialized",
        "on blocked",
        "resume with",
        "next useful action",
        "legacy alias",
        "aliases such as",
    )
    return any(marker in lowered for marker in documentary_markers)


def _parse_internal_invocation_line(
    line: str,
    *,
    skill_path: Path,
    line_number: int,
) -> dict[str, str] | None:
    """Parse ``- [mode] `command` — purpose`` invocation rows."""
    stripped = line.strip()
    if stripped in _contracts.MARKDOWN_HORIZONTAL_RULES:
        return None
    if not stripped or not stripped.startswith("-"):
        return None
    # Parse "- [mode] `command` — purpose" rows from the invocation allowlist.
    match = re.match(r"^-\s+\[([^\]]+)\]\s+`([^`]+)`(?:\s+[—-]\s+(.+))?$", stripped)
    if match is None:
        raise _contracts.ExpectationsInvalid(
            skill_path.as_posix(),
            f"Malformed Internal Command Invocations bullet row at line {line_number}: {stripped}",
        )
    mode = match.group(1).strip()
    command = match.group(2).strip()
    purpose = (match.group(3) or "").strip()
    return {
        "mode": mode,
        "command": command,
        "purpose": purpose,
    }
