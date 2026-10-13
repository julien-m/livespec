"""Finalize writes the one changelog entry format that validation accepts (058 FR-002).

Regression for the Handy report: ``finalize apply`` wrote ``### YYYY-MM-DD — <line>``
while ``validator/rules/changelog_entries.py`` requires ``## YYYY-MM-DD — [Tag]:``, so a
freshly finalized feature changelog failed ``livespec validate``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.test_finalize import _make_specs_tree
from validator.cli import app
from validator.finalize_registry import entry_heading
from validator.rules import validate_by_type

FEATURE = "004-notifications"


def _apply(root: Path, monkeypatch: pytest.MonkeyPatch, command: str, body: str) -> str:
    monkeypatch.chdir(root)
    entry = root / "entry.md"
    entry.write_text(body)
    options = ["--feature", FEATURE, "--command", command, "--entry-file", str(entry)]
    result = CliRunner().invoke(app, ["finalize", "apply", *options, "--json"])
    assert result.exit_code == 0, result.output
    return (root / ".specs/features" / FEATURE / "changelog.md").read_text()


# @spec FR-002: Feature changelog entry heading
#   — .specs/features/058-deterministic-finalization/spec.md#fr-002
def test_first_finalized_changelog_passes_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_specs_tree(tmp_path)
    (tmp_path / ".specs/features" / FEATURE / "changelog.md").unlink()
    content = _apply(tmp_path, monkeypatch, "spec-plan", "Technical plan generated\n\n- Steps: 9")
    assert re.search(r"^## \d{4}-\d{2}-\d{2} — \[Plan\]: Technical plan generated$", content, re.M)
    assert "### " not in content
    assert validate_by_type(content, "changelog", []) == []
    result = CliRunner().invoke(app, ["validate", str(tmp_path / ".specs/features" / FEATURE)])
    assert "No valid changelog entry" not in result.output, result.output


@pytest.mark.parametrize(
    ("command", "first_line", "expected"),
    [
        ("spec-fix", "[Bugfix]: Restore paste", "[Bugfix]: Restore paste"),
        ("spec-implement", "Feature: Initial implementation", "[Feature]: Initial implementation"),
        ("spec-plan", "### Plan created — Smart paste", "[Plan]: Plan created — Smart paste"),
        (
            "spec-implement",
            "Implemented the CLI: get and set",
            "[Feature]: Implemented the CLI: get and set",
        ),
        ("spec-journey", "Journey bound", "[Journey]: Journey bound"),
        ("spec-plan", "## 2026-10-12 — [Plan]: Generated", "[Plan]: Generated"),
        ("spec-plan", "### 2026-10-12 — ### Plan: Generated", "[Plan]: Generated"),
    ],
)
def test_entry_heading_tags(command: str, first_line: str, expected: str) -> None:
    assert entry_heading(first_line, command, "2026-10-13") == f"## 2026-10-13 — {expected}"


def test_legacy_finalized_entries_stay_valid_and_bare_h3_does_not() -> None:
    legacy = (
        "# Changelog - 007-smart-paste\n\n### 2026-10-12 — ### Plan: generated\n\n- Type: Plan\n\n"
        "<!-- finalize:spec-plan:2026-10-12:307d8e77 -->\n"
    )
    assert validate_by_type(legacy, "changelog", []) == []
    bare = "# Changelog\n\n### 2026-10-12 — Plan generated\n\n- Type: Plan\n"
    assert validate_by_type(bare, "changelog", []) != []
