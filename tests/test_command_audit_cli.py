"""Tests for ``livespec command-audit``."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from validator.cli import app

runner = CliRunner()


def test_command_audit_reports_all_builtin_commands() -> None:
    result = runner.invoke(app, ["command-audit", "--repo", ".", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["summary"]["commands"] == 21
    assert payload["summary"]["score"] == 5
    assert payload["summary"]["failed"] == 0
    assert {entry["name"] for entry in payload["commands"]} >= {
        "spec-check",
        "spec-feature",
    }


def test_command_audit_fails_when_expectations_are_missing(tmp_path: Path) -> None:
    commands_dir = tmp_path / "commands"
    commands_dir.mkdir()
    (commands_dir / "spec-demo.md").write_text("# Command: /spec-demo\n", encoding="utf-8")

    result = runner.invoke(app, ["command-audit", "--repo", str(tmp_path), "--json"])

    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert payload["summary"]["failed"] == 1
    assert payload["commands"][0]["score"] < 5
    assert any(check["status"] == "FAIL" for check in payload["commands"][0]["checks"])


def test_command_audit_fails_when_antidrift_import_is_missing(tmp_path: Path) -> None:
    commands_dir = tmp_path / "commands"
    commands_dir.mkdir()
    (commands_dir / "spec-demo.md").write_text("# Command: /spec-demo\n", encoding="utf-8")
    expectation_text = Path(".agent-sync/skills/spec-status/expectations.md").read_text(
        encoding="utf-8"
    )
    (commands_dir / "spec-demo.expectations.md").write_text(
        expectation_text.replace("command: spec-status", "command: spec-demo", 1),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["command-audit", "--repo", str(tmp_path), "--json"])

    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    command_file_check = next(
        check for check in payload["commands"][0]["checks"] if check["name"] == "command_file"
    )
    assert command_file_check["status"] == "FAIL"


def test_command_audit_fails_when_source_filename_is_not_canonical(tmp_path: Path) -> None:
    commands_dir = tmp_path / "commands"
    commands_dir.mkdir()
    source_text = Path(".agent-sync/skills/spec-status/SKILL.md").read_text(encoding="utf-8")
    expectation_text = Path(".agent-sync/skills/spec-status/expectations.md").read_text(
        encoding="utf-8"
    )
    (commands_dir / "demo.md").write_text(
        source_text.replace("/spec-status", "/spec-demo", 1),
        encoding="utf-8",
    )
    (commands_dir / "demo.expectations.md").write_text(
        expectation_text.replace("command: spec-status", "command: spec-demo", 1),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["command-audit", "--repo", str(tmp_path), "--json"])

    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    source_file_check = next(
        check for check in payload["commands"][0]["checks"] if check["name"] == "source_filename"
    )
    assert source_file_check["status"] == "FAIL"
    assert "spec-demo.md" in source_file_check["detail"]


def test_command_audit_fails_subagent_internal_command_without_workdir_guard(
    tmp_path: Path,
) -> None:
    commands_dir = tmp_path / "commands"
    commands_dir.mkdir()
    source_text = """\
# Command: /spec-demo

**Read** system/anti-drift-block.md before starting.

## Internal Command Invocations

- [subagent] `/spec-fix <feature>` — executable nested command with child goal.
"""
    expectation_text = Path(".agent-sync/skills/spec-status/expectations.md").read_text(
        encoding="utf-8"
    )
    (commands_dir / "spec-demo.md").write_text(source_text, encoding="utf-8")
    (commands_dir / "spec-demo.expectations.md").write_text(
        expectation_text.replace("command: spec-status", "command: spec-demo", 1),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["command-audit", "--repo", str(tmp_path), "--json"])

    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    workdir_check = next(
        check
        for check in payload["commands"][0]["checks"]
        if check["name"] == "internal_subagent_workdir"
    )
    assert workdir_check["status"] == "FAIL"
    assert "project_root" in workdir_check["detail"]


def test_command_audit_enforces_hyphenated_policy() -> None:
    result = runner.invoke(
        app,
        ["command-audit", "--repo", ".", "--naming-policy", "hyphenated", "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["summary"]["naming_policy"] == "hyphenated"
    assert all(
        entry["canonical_slash"].startswith("/spec-") for entry in payload["commands"]
    )
    assert all(
        entry["command_path"].endswith(f".agent-sync/skills/{entry['name']}/SKILL.md")
        for entry in payload["commands"]
    )
