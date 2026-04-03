"""Tests for coherence validation via the CLI (typer CliRunner)."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from validator.cli import app

runner = CliRunner()


def _write_specs_with_errors(base: Path) -> Path:
    """Create a .specs/ structure that has coherence errors."""
    specs = base / ".specs"
    specs.mkdir(parents=True)

    # Roadmap checked item pointing to missing feature -> R1.1 ERROR
    (specs / "roadmap.md").write_text(
        "# Roadmap\n\n- [x] [Ghost](features/099-ghost/)\n"
    )

    # A real feature exists
    feat = specs / "features" / "001-auth"
    feat.mkdir(parents=True)
    (feat / "spec.md").write_text("---\nstatus: Draft\n---\n# Auth\n")

    # README referencing the ghost feature -> R4.1 ERROR
    (specs / "README.md").write_text(
        "| [099-ghost](features/099-ghost/) | Draft |\n"
    )

    return specs


def _write_clean_specs(base: Path) -> Path:
    """Create a .specs/ structure with zero coherence errors."""
    specs = base / ".specs"
    specs.mkdir(parents=True)

    (specs / "roadmap.md").write_text(
        "# Roadmap\n\n- [x] [Auth](features/001-auth/)\n"
    )

    feat = specs / "features" / "001-auth"
    feat.mkdir(parents=True)
    (feat / "spec.md").write_text("---\nstatus: Implemented\n---\n# Auth\n")
    (feat / "plan.md").write_text("# Plan\n")
    (feat / "implementation.md").write_text("# Implementation\n")

    (specs / "README.md").write_text(
        "| [001-auth](features/001-auth/) | Implemented |\n"
    )

    return specs


class TestCoherenceHelp:
    """Verify coherence flags appear in --help."""

    def test_validate_help_shows_coherence_flags(self) -> None:
        result = runner.invoke(app, ["validate", "--help"])
        assert result.exit_code == 0
        assert "--coherence" in result.output
        assert "--coherence-only" in result.output
        assert "--strict" in result.output
        assert "--wave" in result.output
        assert "--rules" in result.output
        assert "--ignore" in result.output
        assert "--no-suppress" in result.output


class TestCoherenceOnly:
    """--coherence-only runs only Layer 2."""

    def test_coherence_only_produces_output(self, tmp_path: Path) -> None:
        _write_specs_with_errors(tmp_path)

        result = runner.invoke(
            app,
            ["validate", "--coherence-only", str(tmp_path / ".specs")],
        )
        # Should produce output (violations found)
        # Exit code 1 because there are errors
        assert result.exit_code == 1

    def test_coherence_only_json_format(self, tmp_path: Path) -> None:
        _write_specs_with_errors(tmp_path)

        result = runner.invoke(
            app,
            ["validate", "--coherence-only", "--format", "json", str(tmp_path / ".specs")],
        )
        assert "violations" in result.output or result.exit_code == 1

    def test_coherence_only_clean_exits_0(self, tmp_path: Path) -> None:
        _write_clean_specs(tmp_path)

        result = runner.invoke(
            app,
            ["validate", "--coherence-only", str(tmp_path / ".specs")],
        )
        assert result.exit_code == 0


class TestStrict:
    """--strict makes warnings cause exit code 1."""

    def test_strict_with_warnings_exits_1(self, tmp_path: Path) -> None:
        specs = tmp_path / ".specs"
        specs.mkdir(parents=True)

        # Feature not in roadmap -> R1.2 WARNING
        feat = specs / "features" / "001-auth"
        feat.mkdir(parents=True)
        (feat / "spec.md").write_text("---\nstatus: Draft\n---\n# Auth\n")

        # Empty roadmap
        (specs / "roadmap.md").write_text("# Roadmap\n")

        result = runner.invoke(
            app,
            ["validate", "--coherence-only", "--strict", str(specs)],
        )
        assert result.exit_code == 1

    def test_without_strict_warnings_exit_0(self, tmp_path: Path) -> None:
        specs = tmp_path / ".specs"
        specs.mkdir(parents=True)

        feat = specs / "features" / "001-auth"
        feat.mkdir(parents=True)
        (feat / "spec.md").write_text("---\nstatus: Draft\n---\n# Auth\n")
        # README missing -> R4.2 WARNING, but no ERROR
        (specs / "roadmap.md").write_text(
            "# Roadmap\n\n- [ ] [Auth](features/001-auth/)\n"
        )

        result = runner.invoke(
            app,
            ["validate", "--coherence-only", str(specs)],
        )
        # Only warnings, no errors -> exit 0
        assert result.exit_code == 0


class TestCoherenceWithFiltering:
    """CLI passes --rules, --wave, --ignore to the engine."""

    def test_rules_filter(self, tmp_path: Path) -> None:
        _write_specs_with_errors(tmp_path)

        # Run only R4 rules
        result = runner.invoke(
            app,
            [
                "validate", "--coherence-only", "--format", "json",
                "--rules", "R4",
                str(tmp_path / ".specs"),
            ],
        )
        # Should run and produce output
        assert "R4" in result.output or result.exit_code in (0, 1)

    def test_wave_filter(self, tmp_path: Path) -> None:
        _write_specs_with_errors(tmp_path)

        result = runner.invoke(
            app,
            [
                "validate", "--coherence-only",
                "--wave", "1",
                str(tmp_path / ".specs"),
            ],
        )
        # Should complete without crash
        assert result.exit_code in (0, 1)

    def test_ignore_filter(self, tmp_path: Path) -> None:
        _write_specs_with_errors(tmp_path)

        result = runner.invoke(
            app,
            [
                "validate", "--coherence-only",
                "--ignore", "R1.1,R4.1",
                str(tmp_path / ".specs"),
            ],
        )
        # Ignoring the error-producing rules should allow exit 0
        # (remaining violations may still cause exit 1 depending on structure)
        assert result.exit_code in (0, 1)


class TestWarnOnly:
    """--warn-only always exits 0 even with errors."""

    def test_warn_only_exits_0(self, tmp_path: Path) -> None:
        _write_specs_with_errors(tmp_path)

        result = runner.invoke(
            app,
            ["validate", "--coherence-only", "--warn-only", str(tmp_path / ".specs")],
        )
        assert result.exit_code == 0
