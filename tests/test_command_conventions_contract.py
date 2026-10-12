"""Convention commands documented in LiveSpec skills must exist in the real CLI.

Skills such as ``spec-fix`` and ``spec-implement`` tell agents to
run ``livespec conventions <subcommand> <flags>``. A renamed subcommand or flag
would make those steps fail at runtime, so every documented invocation is
resolved against the Typer application that ships the CLI.
"""

from __future__ import annotations

import re
from pathlib import Path

import typer
from typer.core import TyperGroup

from validator.cli import app

SKILLS_DIR = Path(__file__).resolve().parents[1] / ".agent-sync" / "skills"
_INVOCATION = re.compile(r"`(livespec conventions [^`]+)`")


def _documented_invocations() -> list[tuple[str, str]]:
    return [
        (skill.parent.name, match.group(1))
        for skill in sorted(SKILLS_DIR.glob("*/SKILL.md"))
        for match in _INVOCATION.finditer(skill.read_text(encoding="utf-8"))
    ]


def test_documented_conventions_invocations_resolve_to_real_cli_options() -> None:
    root = typer.main.get_command(app)
    assert isinstance(root, TyperGroup)
    conventions = root.commands["conventions"]
    assert isinstance(conventions, TyperGroup)
    invocations = _documented_invocations()
    documenting_skills = {skill for skill, _ in invocations}

    assert {"spec-fix", "spec-implement"} <= documenting_skills
    for skill, invocation in invocations:
        tokens = invocation.split()
        subcommand = conventions.commands.get(tokens[2])
        assert subcommand is not None, f"{skill}: unknown subcommand in `{invocation}`"
        options = {opt for param in subcommand.params for opt in param.opts + param.secondary_opts}
        unknown = [t for t in tokens[3:] if t.startswith("--") and t.split("=")[0] not in options]
        assert not unknown, f"{skill}: `{invocation}` uses unknown option(s) {unknown}"
