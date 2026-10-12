"""Atomic commands must invoke the hook resolver CLI with a name it accepts.

The atomic commands `/spec-specify` and `/spec-plan` are invoked directly by
users (not only as subagents of `/spec-feature`), so their SKILL.md carries
the ``livespec hooks resolve`` invocation itself. A typo in the documented
``--command`` value would make the CLI warn "unknown command" and silently
inject nothing, so the documented value is checked against the resolver's own
normalisation and command set.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from validator.command_registry import normalize_command_name
from validator.integrations import valid_command_names

SKILLS_DIR = Path(__file__).parent.parent / ".agent-sync" / "skills"
_INVOCATION = re.compile(r"livespec hooks resolve --event before --command (\S+?)[`\s]")


@pytest.mark.parametrize("command", ["spec-specify", "spec-plan"])
def test_atomic_command_documents_a_resolvable_hooks_invocation(command: str) -> None:
    """The documented before-hook call names this command in a form the CLI resolves."""
    text = (SKILLS_DIR / command / "SKILL.md").read_text(encoding="utf-8")

    documented = _INVOCATION.findall(text)

    assert documented, f"{command}/SKILL.md no longer invokes `livespec hooks resolve`"
    for name in documented:
        assert normalize_command_name(name) == command
        assert normalize_command_name(name) in valid_command_names()
    assert "--event after" in text, f"{command}/SKILL.md lost its after-hook invocation"
