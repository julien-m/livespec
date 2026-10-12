"""Every ``livespec <command> [<subcommand>]`` cited by a skill exists in the real CLI.

Extends the ``livespec conventions`` / ``livespec hooks resolve`` contracts to all
skills: an agent following a SKILL.md must never be told to run a command path
that the shipped Typer application does not define.
"""

from __future__ import annotations

import re
from pathlib import Path

import typer

from validator.cli import app

SKILLS_DIR = Path(__file__).resolve().parents[1] / ".agent-sync" / "skills"
_WORD = re.compile(r"[a-z][a-z0-9._-]*")
_INLINE = re.compile(r"`(livespec [^`]+)`")


def _cited_invocations() -> list[tuple[str, str]]:
    cited: list[tuple[str, str]] = []
    for skill in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        for line in skill.read_text(encoding="utf-8").splitlines():
            cited.extend((skill.parent.name, m.group(1)) for m in _INLINE.finditer(line))
            if line.strip().startswith("livespec "):  # fenced command lines
                cited.append((skill.parent.name, line.strip()))
    return cited


def _unknown_path(invocation: str) -> str | None:
    """Return the first token that does not resolve to a command, if any."""
    command: object = typer.main.get_command(app)
    for token in invocation.split()[1:]:
        commands = getattr(command, "commands", None)
        if commands is None or not _WORD.fullmatch(token):
            return None  # reached a leaf command, an option, or a placeholder
        if token not in commands:
            return token
        command = commands[token]
    return None


def test_skill_cited_livespec_command_paths_exist() -> None:
    invocations = _cited_invocations()
    unknown = sorted(
        {
            f"{skill}: `{inv}` ({token!r})"
            for skill, inv in invocations
            if (token := _unknown_path(inv))
        }
    )

    assert len(invocations) > 50, "skill CLI invocation scan found too few citations"
    assert not unknown, "Skills cite CLI command paths that do not exist:\n" + "\n".join(unknown)
