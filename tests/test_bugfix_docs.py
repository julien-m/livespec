"""The bugfix lane is documented in spec-fix, expectations, spec-system, README (084 AC-014)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import typer

from validator.cli import app

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agent-sync/skills/spec-fix"


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_skill_documents_mode_conditions_gate_fallback_and_record() -> None:
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    for expected in (
        "### `--bugfix` Mode",
        "| `--bugfix` |",
        "owner feature identified",
        "no FR/AC/SC definition text change",
        "RED before and GREEN after",
        "`max_files`/`max_lines`",
        "livespec bugfix capture --feature <slug> --expect red",
        "livespec bugfix gate --feature <slug> --red <red-receipt>",
        "livespec validate <feature-dir> --progression implement",
        "livespec bugfix record --feature <slug>",
        "feature-scope conventions gate",
        "`--visual` fixes never use the lane",
        "project test suite",
    ):
        assert expected in text, expected


def test_expectations_cover_the_lane_and_are_reviewed() -> None:
    text = (SKILL / "expectations.md").read_text(encoding="utf-8")
    assert "## Bugfix lane (084)" in text
    assert "Bugfix gate: FALLBACK" in text
    assert "last_reviewed: 2026-10-12" in text


@pytest.mark.parametrize("relative", ["system/spec-system.md", ".specs/spec-system.md"])
def test_both_spec_system_copies_describe_the_lane_once(relative: str) -> None:
    text = _read(relative)
    assert text.count("### Bugfix lane (`/spec-fix <feature> --bugfix`)") == 1
    assert "livespec bugfix gate" in text and "Bugfix gate: FALLBACK" in text


def test_every_cited_bugfix_command_exists() -> None:
    commands: dict[str, object] = getattr(typer.main.get_command(app), "commands", {})
    subcommands: dict[str, object] = getattr(commands["bugfix"], "commands", {})
    cited = set(re.findall(r"livespec bugfix ([a-z]+)", (SKILL / "SKILL.md").read_text()))
    assert cited == {"capture", "gate", "record"}
    assert cited <= set(subcommands)


def test_readme_lists_the_bugfix_commands() -> None:
    text = _read("README.md")
    for command in ("bugfix capture", "bugfix gate", "bugfix record"):
        assert f"livespec {command}" in text
