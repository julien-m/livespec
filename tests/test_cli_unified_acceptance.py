# LiveSpec traceability anchors
# @spec(AC-003)
# @spec(AC-005)
# @spec(AC-008)
# @spec(AC-010)
# @spec(AC-014)

"""Acceptance tests for previously unmapped Feature 035 criteria."""

# @spec AC-003, AC-005, AC-008, AC-010, AC-014: unified CLI acceptance
# — .specs/features/035-unified-cli-surface/spec.md#ac-003

from __future__ import annotations

import datetime as dt
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from validator.cli import app
from validator.drivers.mutation_report import MutationResult
from validator.drivers.schemas import CapabilityResult
from validator.preflight_autofix import FixResult, PreflightItem

runner = CliRunner()


def _python_project(root: Path) -> None:
    (root / ".specs").mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")


def test_test_mutation_output_is_separate_from_coverage(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """AC-003: --mutation runs the mutation capability and prints its own output."""
    _python_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    def _fake(driver: object, capability: str, **_kw: object) -> CapabilityResult:
        stdout = "kill_rate=81%" if capability == "mutation" else "coverage ok"
        return CapabilityResult(
            capability_name=capability, exit_code=0, report_path=None, stdout=stdout, stderr=""
        )

    with patch("validator.cli_commands.test_selection.run_capability", side_effect=_fake) as run:
        result = runner.invoke(app, ["test", "--mutation"])
    assert result.exit_code == 0, result.output
    assert [call.args[1] for call in run.call_args_list] == ["coverage", "mutation"]
    assert result.output.index("coverage ok") < result.output.index("kill_rate=81%")
    assert "mutation=ran" in result.output


def test_coverage_base_flag_overrides_detection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """AC-005: --base is used verbatim and auto-detection is skipped."""
    _python_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    with (
        patch("validator.cli_commands.coverage_cmd.detect_base_branch") as detect,
        patch("validator.cli_commands.coverage_cmd.git_diff", return_value="") as diff,
    ):
        result = runner.invoke(app, ["coverage", "--base", "develop"])
    assert result.exit_code == 0, result.output
    detect.assert_not_called()
    assert diff.call_args.args[0] == "develop"
    assert "base=develop" in result.output


def test_mutation_writes_dated_report(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """AC-008: the historical report lands in .specs/reports/mutation-YYYY-MM-DD.md."""
    _python_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    good = MutationResult(
        date="2026-10-12", driver="python", kill_rate=90.0, killed=9, survived=1, timeout=0
    )
    with patch("validator.cli_commands.mutation_cmd.run_mutation", return_value=good):
        result = runner.invoke(app, ["mutation", "--threshold", "70"])
    assert result.exit_code == 0, result.output
    report = tmp_path / ".specs" / "reports" / f"mutation-{dt.date.today().isoformat()}.md"
    assert report.is_file()


def test_preflight_fix_delegates_to_feature_034(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """AC-010: --fix calls the feature 034 autofix (which re-verifies) without prompts."""
    _python_project(tmp_path)
    (tmp_path / ".specs" / "preflight.md").write_text(
        textwrap.dedent(
            """
            ## Tooling

            ### pytest-cov
            - binary: pytest
            - install: pip install pytest-cov
            """
        ).strip(),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    def _fake_fix(items: list[PreflightItem], **kwargs: object) -> list[FixResult]:
        assert kwargs["auto"] is True
        assert kwargs["dry_run"] is False
        return [FixResult(item=item, status="installed", message="ok") for item in items]

    with patch("validator.preflight_autofix.run_fix", side_effect=_fake_fix) as fix:
        result = runner.invoke(app, ["preflight", "--fix"])
    assert fix.called
    assert result.exit_code == 0, result.output
    assert "LIVESPEC preflight · OK" in result.output


@pytest.mark.parametrize(("flags", "traceback_shown"), [([], False), (["--debug"], True)])
def test_errors_are_one_line_unless_debug(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, flags: list[str], traceback_shown: bool
) -> None:
    """AC-014: a single actionable line, the stacktrace only with --debug."""
    _python_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    with patch(
        "validator.cli_commands.test_selection.run_capability", side_effect=RuntimeError("boom")
    ):
        result = runner.invoke(app, ["test", *flags])
    assert result.exit_code == 1
    assert ("Traceback (most recent call last)" in result.output) is traceback_shown
    assert "boom" in result.output
