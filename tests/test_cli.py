"""Tests for validator.cli — Typer CLI interface."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.cli import app

FIXTURES_DIR = Path(__file__).parent / "fixtures"

runner = CliRunner()


class TestValidateHelp:
    """Basic CLI availability."""

    def test_validate_help(self) -> None:
        result = runner.invoke(app, ["validate", "--help"])
        assert result.exit_code == 0
        assert "Validate" in result.output or "validate" in result.output.lower()


class TestMutualExclusion:
    """--staged and PATH cannot be used together."""

    def test_staged_and_path_mutually_exclusive(self, tmp_path: Path) -> None:
        # Create a minimal .specs/ so the CLI finds it
        specs = tmp_path / ".specs"
        specs.mkdir()
        result = runner.invoke(
            app,
            ["validate", "--staged", str(specs / "some.md")],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()


class TestSmartFlag:
    """--smart flag raises error (not implemented)."""

    def test_smart_raises_error(self, tmp_path: Path) -> None:
        specs = tmp_path / ".specs"
        specs.mkdir()
        result = runner.invoke(app, ["validate", "--smart"], catch_exceptions=False)
        # May fail on specs not found or smart error; either is non-zero
        assert result.exit_code != 0


class TestJsonFormat:
    """--format json produces valid JSON."""

    def test_json_output(self, tmp_path: Path) -> None:
        specs = tmp_path / ".specs"
        specs.mkdir()
        features = specs / "features" / "001-test"
        features.mkdir(parents=True)
        shutil.copy2(FIXTURES_DIR / "valid_spec.md", features / "spec.md")

        result = runner.invoke(
            app,
            ["validate", "--format", "json", str(features / "spec.md")],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "files" in data
        assert "summary" in data


class TestInstallHookHelp:
    """install-hook command exists."""

    def test_install_hook_help(self) -> None:
        result = runner.invoke(app, ["install-hook", "--help"])
        assert result.exit_code == 0
        assert "hook" in result.output.lower()
