# LiveSpec traceability anchors
# @spec(AC-004)
# @spec(AC-011)
# @spec(AC-012)
# @spec(AC-013)

"""Exit-code taxonomy, base-branch order, JSON channel and --help examples (Feature 035)."""

# @spec AC-011: Constitution exit codes — .specs/features/035-unified-cli-surface/spec.md#ac-011
# @spec AC-004: Base branch order — .specs/features/035-unified-cli-surface/spec.md#ac-004
# @spec AC-012: JSON summary on stderr — .specs/features/035-unified-cli-surface/spec.md#ac-012
# @spec AC-013: --help example per command — .specs/features/035-unified-cli-surface/spec.md#ac-013

from __future__ import annotations

import json
import shlex
import subprocess
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from validator import cli_resolvers
from validator.cli import app
from validator.drivers.mutation_report import MutationResult
from validator.drivers.schemas import CapabilityResult, DetectRule, DriverManifest

runner = CliRunner()
UNIFIED_COMMANDS = ("test", "coverage", "drivers", "mutation", "preflight")


def _python_project(root: Path) -> None:
    (root / ".specs").mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def _repo_with_branches(root: Path, branches: list[str]) -> None:
    """Create a repository whose initial commit is on ``work`` plus the given branches."""
    subprocess.run(["git", "init", "-q", "-b", "work", str(root)], check=True)
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "T")
    (root / "README").write_text("hi", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "init")
    for branch in branches:
        _git(root, "branch", branch)


def _coverage_result(exit_code: int) -> CapabilityResult:
    return CapabilityResult(
        capability_name="coverage",
        exit_code=exit_code,
        report_path="lcov.info",
        stdout="",
        stderr="",
    )


class TestBaseBranchOrder:
    """AC-004: origin/HEAD first, then main, master, develop, dev."""

    def test_origin_head_wins_over_local_branches(self, tmp_path: Path) -> None:
        _repo_with_branches(tmp_path, ["main", "master"])
        _git(tmp_path, "update-ref", "refs/remotes/origin/trunk", "HEAD")
        _git(tmp_path, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk")
        assert cli_resolvers.detect_base_branch(tmp_path) == "origin/trunk"

    @pytest.mark.parametrize(
        ("branches", "expected"),
        [
            (["dev", "develop", "master", "main"], "main"),
            (["dev", "develop", "master"], "master"),
            (["dev", "develop"], "develop"),
            (["dev"], "dev"),
        ],
    )
    def test_local_fallback_order(self, tmp_path: Path, branches: list[str], expected: str) -> None:
        _repo_with_branches(tmp_path, branches)
        assert cli_resolvers.detect_base_branch(tmp_path) == expected

    def test_none_when_no_candidate(self, tmp_path: Path) -> None:
        _repo_with_branches(tmp_path, [])
        assert cli_resolvers.detect_base_branch(tmp_path) is None


class TestExitCodes:
    """AC-011: 0 success, 1 run failure, 2 usage, 3 missing configuration, 130 Ctrl+C."""

    def test_no_driver_exits_3(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        (tmp_path / ".specs").mkdir()
        monkeypatch.chdir(tmp_path)
        assert runner.invoke(app, ["test"]).exit_code == 3

    def test_unknown_flag_exits_2(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        _python_project(tmp_path)
        monkeypatch.chdir(tmp_path)
        assert runner.invoke(app, ["coverage", "--no-such-flag"]).exit_code == 2

    def test_failing_suite_exits_1(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        _python_project(tmp_path)
        monkeypatch.chdir(tmp_path)
        with patch(
            "validator.cli_commands.test_selection.run_capability", return_value=_coverage_result(1)
        ):
            result = runner.invoke(app, ["test"])
        assert result.exit_code == 1, result.output

    def test_coverage_below_threshold_exits_1(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _python_project(tmp_path)
        (tmp_path / "lcov.info").write_text(
            "SF:foo.py\nDA:1,1\nDA:2,0\nDA:3,0\nend_of_record\n", encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)
        with patch(
            "validator.cli_commands.test_selection.run_capability", return_value=_coverage_result(0)
        ):
            result = runner.invoke(app, ["test"])
        assert result.exit_code == 1, result.output
        assert "FAIL" in result.output

    def test_unexpected_exception_exits_1(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _python_project(tmp_path)
        monkeypatch.chdir(tmp_path)
        with patch(
            "validator.cli_commands.test_selection.run_capability", side_effect=RuntimeError("boom")
        ):
            result = runner.invoke(app, ["test"])
        assert result.exit_code == 1, result.output
        assert "Error: boom" in result.output

    def test_ctrl_c_exits_130(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        _python_project(tmp_path)
        monkeypatch.chdir(tmp_path)
        with patch(
            "validator.cli_commands.test_selection.run_capability", side_effect=KeyboardInterrupt
        ):
            result = runner.invoke(app, ["test"])
        assert result.exit_code == 130, result.output

    def test_coverage_without_base_exits_3(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _python_project(tmp_path)
        monkeypatch.chdir(tmp_path)
        with patch("validator.cli_commands.coverage_cmd.detect_base_branch", return_value=None):
            result = runner.invoke(app, ["coverage"])
        assert result.exit_code == 3, result.output

    def test_coverage_without_lcov_exits_3(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _python_project(tmp_path)
        monkeypatch.chdir(tmp_path)
        with (
            patch("validator.cli_commands.coverage_cmd.detect_base_branch", return_value="main"),
            patch("validator.cli_commands.coverage_cmd.git_diff", return_value="+changed"),
        ):
            result = runner.invoke(app, ["coverage"])
        assert result.exit_code == 3, result.output
        assert "lcov" in result.output

    def test_coverage_capability_absent_exits_3(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _python_project(tmp_path)
        monkeypatch.chdir(tmp_path)
        bare = DriverManifest(name="python", detect=DetectRule(files=["pyproject.toml"]))
        with (
            patch("validator.cli_commands.coverage_cmd.detect_base_branch", return_value="main"),
            patch("validator.cli_commands.coverage_cmd.git_diff", return_value="+changed"),
            patch("validator.cli_commands.coverage_cmd.resolve_primary_driver", return_value=bare),
        ):
            result = runner.invoke(app, ["coverage"])
        assert result.exit_code == 3, result.output

    def test_mutation_capability_absent_exits_3(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _python_project(tmp_path)
        monkeypatch.chdir(tmp_path)
        with patch("validator.cli_commands.mutation_cmd.run_mutation", return_value=None):
            result = runner.invoke(app, ["mutation"])
        assert result.exit_code == 3, result.output

    def test_mutation_below_threshold_exits_1(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _python_project(tmp_path)
        monkeypatch.chdir(tmp_path)
        low = MutationResult(
            date="2026-10-12", driver="python", kill_rate=50.0, killed=5, survived=5, timeout=0
        )
        with patch("validator.cli_commands.mutation_cmd.run_mutation", return_value=low):
            result = runner.invoke(app, ["mutation", "--threshold", "70"])
        assert result.exit_code == 1, result.output

    def test_preflight_manifest_missing_exits_3(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _python_project(tmp_path)
        monkeypatch.chdir(tmp_path)
        assert runner.invoke(app, ["preflight"]).exit_code == 3

    def test_preflight_critical_tool_missing_exits_3(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _python_project(tmp_path)
        manifest = textwrap.dedent(
            """
            ## Tooling

            ### missing-tool
            - binary: livespec-definitely-missing-binary
            - install: pip install livespec-definitely-missing-binary
            """
        ).strip()
        (tmp_path / ".specs" / "preflight.md").write_text(manifest, encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["preflight"])
        assert result.exit_code == 3, result.output


def test_drivers_json_keeps_stdout_pure_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """AC-012 / FR-009: with --json the summary goes to stderr."""
    _python_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["drivers", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert any(entry["name"] == "python" for entry in payload)
    assert "LIVESPEC drivers" in result.stderr
    assert "LIVESPEC" not in result.stdout


def test_drivers_table_summary_stays_on_stdout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _python_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["drivers"])
    assert "LIVESPEC drivers" in result.stdout


@pytest.mark.parametrize("command_name", UNIFIED_COMMANDS)
def test_help_ends_with_executable_example(command_name: str) -> None:
    """AC-013 / SC-003: each --help shows one example its own parser accepts."""
    result = runner.invoke(app, [command_name, "--help"], terminal_width=200)
    assert result.exit_code == 0, result.output
    example_lines = [
        line.strip()
        for line in result.output.splitlines()
        if line.strip().startswith("Example: livespec ")
    ]
    assert len(example_lines) == 1, result.output
    argv = shlex.split(example_lines[0].removeprefix("Example: "))
    assert argv[:2] == ["livespec", command_name]
    root = typer.main.get_command(app)
    assert isinstance(root, typer.core.TyperGroup)
    command = root.commands[command_name]
    # Parsing without invoking proves every option and value in the example is
    # accepted: an unknown option or bad value raises a usage error here.
    context = command.make_context(command_name, argv[2:])
    assert set(context.params) >= {"debug"}


def test_help_example_parser_rejects_unknown_option() -> None:
    """Guard for the check above: a wrong example would not parse."""
    root = typer.main.get_command(app)
    assert isinstance(root, typer.core.TyperGroup)
    command = root.commands["coverage"]
    with pytest.raises(typer.TyperException):
        command.make_context("coverage", ["--no-such-option"])
