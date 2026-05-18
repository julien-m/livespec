"""Tests for command run finalization and verification."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from validator.cli import app

runner = CliRunner()


def test_run_finalize_records_and_verifies_success(tmp_path: Path) -> None:
    (tmp_path / ".specs").mkdir()
    stdout_file = tmp_path / "stdout.txt"
    stdout_file.write_text("LiveSpec features summary\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "run",
            "finalize",
            "--command",
            "status",
            "--exit-code",
            "0",
            "--stdout-file",
            str(stdout_file),
            "--cwd",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "outcome   success" in result.output
    assert list((tmp_path / ".specs" / ".runs").glob("spec-status-*.json"))


def test_run_finalize_returns_drift_exit_code(tmp_path: Path) -> None:
    (tmp_path / ".specs").mkdir()
    stdout_file = tmp_path / "stdout.txt"
    stdout_file.write_text("LiveSpec roadmap only\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "run",
            "finalize",
            "--command",
            "status",
            "--exit-code",
            "0",
            "--stdout-file",
            str(stdout_file),
            "--cwd",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1, result.output
    assert "outcome   drift" in result.output


def test_run_finalize_accepts_legacy_slash_alias(tmp_path: Path) -> None:
    (tmp_path / ".specs").mkdir()
    stdout_file = tmp_path / "stdout.txt"
    stdout_file.write_text("LiveSpec features summary\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "run",
            "finalize",
            "--command",
            "/spec.status",
            "--exit-code",
            "0",
            "--stdout-file",
            str(stdout_file),
            "--cwd",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert list((tmp_path / ".specs" / ".runs").glob("spec-status-*.json"))
