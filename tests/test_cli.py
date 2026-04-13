"""Tests for validator.cli — Typer CLI interface."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

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


class TestReviewSpecCli:
    """Tests for --review-spec CLI flag."""

    def test_review_spec_triggers_review(self, tmp_path: Path) -> None:
        """--review-spec flag triggers spec review."""
        from unittest.mock import patch

        specs = tmp_path / ".specs"
        specs.mkdir()
        (specs / "roadmap.md").write_text(
            "- [x] [001-test](features/001-test/)\n"
        )
        d = specs / "features" / "001-test"
        d.mkdir(parents=True)
        (d / "spec.md").write_text("---\ntitle: Test\nstatus: Draft\n---\n# Spec\n")

        response = json.dumps({"findings": [], "confidence": 5})
        with (
            patch("validator.llm_provider.is_available", return_value=True),
            patch("validator.llm_provider.call_llm", return_value=response),
        ):
            result = runner.invoke(
                app,
                ["validate", "--review-spec", str(d)],
            )

        assert result.exit_code == 0
        assert "Spec Review" in result.output

    def test_review_spec_no_provider_exits_1(self) -> None:
        """--review-spec with no provider exits 1."""
        from unittest.mock import patch

        with patch("validator.llm_provider.is_available", return_value=False):
            result = runner.invoke(
                app,
                ["validate", "--review-spec"],
            )

        assert result.exit_code == 1
        assert "No LLM provider" in result.output

    def test_review_spec_strict_exits_1_on_blocking(self, tmp_path: Path) -> None:
        """--review-spec --strict exits 1 on blocking findings."""
        from unittest.mock import patch

        specs = tmp_path / ".specs"
        specs.mkdir()
        (specs / "roadmap.md").write_text(
            "- [x] [001-test](features/001-test/)\n"
        )
        d = specs / "features" / "001-test"
        d.mkdir(parents=True)
        (d / "spec.md").write_text("---\ntitle: Test\nstatus: Draft\n---\n# Spec\n")

        response = json.dumps({
            "findings": [{
                "category": "testability",
                "severity": "blocking",
                "description": "FR vague",
                "suggestion": "Be specific",
            }],
            "confidence": 4,
        })
        with (
            patch("validator.llm_provider.is_available", return_value=True),
            patch("validator.llm_provider.call_llm", return_value=response),
        ):
            result = runner.invoke(
                app,
                ["validate", "--review-spec", "--strict", str(d)],
            )

        assert result.exit_code == 1

    def test_review_spec_json_output(self, tmp_path: Path) -> None:
        """--review-spec --format json outputs valid JSON."""
        from unittest.mock import patch

        specs = tmp_path / ".specs"
        specs.mkdir()
        (specs / "roadmap.md").write_text(
            "- [x] [001-test](features/001-test/)\n"
        )
        d = specs / "features" / "001-test"
        d.mkdir(parents=True)
        (d / "spec.md").write_text("---\ntitle: Test\nstatus: Draft\n---\n# Spec\n")

        response = json.dumps({"findings": [], "confidence": 5})
        with (
            patch("validator.llm_provider.is_available", return_value=True),
            patch("validator.llm_provider.call_llm", return_value=response),
        ):
            result = runner.invoke(
                app,
                ["validate", "--review-spec", "--format", "json", str(d)],
            )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "reviews" in data

    def test_review_plan_alias_works(self, tmp_path: Path) -> None:
        """--review-plan alias works same as --plan-review."""
        from unittest.mock import patch

        specs = tmp_path / ".specs"
        specs.mkdir()
        (specs / "roadmap.md").write_text(
            "- [x] [001-test](features/001-test/)\n"
        )
        d = specs / "features" / "001-test"
        d.mkdir(parents=True)
        (d / "spec.md").write_text("---\ntitle: Test\nstatus: Draft\n---\n# Spec\n")
        (d / "plan.md").write_text("---\nspec_ref: spec.md\n---\n# Plan\n")

        response = json.dumps({"findings": [], "confidence": 5})
        with (
            patch("validator.llm_provider.is_available", return_value=True),
            patch("validator.llm_provider.call_llm", return_value=response),
        ):
            result = runner.invoke(
                app,
                ["validate", "--review-plan", str(d)],
            )

        assert result.exit_code == 0
        assert "Plan Review" in result.output


class TestNoReviewFlag:
    """AC-013: --no-review flag is accepted by the CLI."""

    def test_no_review_flag_accepted(self, tmp_path: Path) -> None:
        """--no-review flag is accepted without error during validation."""
        specs = tmp_path / ".specs"
        specs.mkdir()
        features = specs / "features" / "001-test"
        features.mkdir(parents=True)
        shutil.copy2(FIXTURES_DIR / "valid_spec.md", features / "spec.md")

        result = runner.invoke(
            app,
            ["validate", "--no-review", str(features / "spec.md")],
        )
        # --no-review should not cause an error; normal validation proceeds
        assert result.exit_code == 0

    def test_no_review_appears_in_help(self) -> None:
        """--no-review flag is documented in validate help."""
        result = runner.invoke(app, ["validate", "--help"])
        assert result.exit_code == 0
        assert "--no-review" in result.output


class TestInstallHookHelp:
    """install-hook command exists."""

    def test_install_hook_help(self) -> None:
        result = runner.invoke(app, ["install-hook", "--help"])
        assert result.exit_code == 0
        assert "hook" in result.output.lower()
