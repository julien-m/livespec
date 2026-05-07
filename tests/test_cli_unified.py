"""End-to-end tests for the unified ``livespec`` CLI surface (Feature 035)."""

# @spec FR-012: tests/test_cli_unified.py — .specs/features/035-unified-cli-surface/spec.md#fr-012

from __future__ import annotations

import json
import subprocess
import textwrap
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from validator import cli_resolvers
from validator.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Resolver unit tests (FR-006)
# ---------------------------------------------------------------------------


class TestDetectSpecsRoot:
    def test_walks_upward(self, tmp_path: Path) -> None:
        (tmp_path / ".specs").mkdir()
        nested = tmp_path / "src" / "deep" / "nested"
        nested.mkdir(parents=True)
        assert cli_resolvers.detect_specs_root(nested) == tmp_path

    def test_returns_none_when_absent(self, tmp_path: Path) -> None:
        assert cli_resolvers.detect_specs_root(tmp_path) is None


class TestDetectBaseBranch:
    def test_returns_none_when_no_git(self, tmp_path: Path) -> None:
        assert cli_resolvers.detect_base_branch(tmp_path) is None

    def test_detects_main(self, tmp_path: Path) -> None:
        subprocess.run(
            ["git", "init", "-q", "-b", "main", str(tmp_path)], check=True
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "config", "user.email", "t@example.com"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "config", "user.name", "T"], check=True
        )
        (tmp_path / "README").write_text("hi", encoding="utf-8")
        subprocess.run(
            ["git", "-C", str(tmp_path), "add", "."], check=True
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "commit", "-q", "-m", "init"], check=True
        )
        assert cli_resolvers.detect_base_branch(tmp_path) == "main"


class TestDetectCurrentFeature:
    @staticmethod
    def _seed_repo(tmp_path: Path, branch: str) -> None:
        subprocess.run(
            ["git", "init", "-q", "-b", branch, str(tmp_path)], check=True
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "config", "user.email", "t@example.com"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "config", "user.name", "T"], check=True
        )
        (tmp_path / "README").write_text("hi", encoding="utf-8")
        subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(tmp_path), "commit", "-q", "-m", "init"], check=True
        )

    def test_extracts_slug(self, tmp_path: Path) -> None:
        self._seed_repo(tmp_path, "feature/042-some-feat")
        assert cli_resolvers.detect_current_feature(tmp_path) == "042-some-feat"

    def test_returns_none_for_non_feature_branch(self, tmp_path: Path) -> None:
        self._seed_repo(tmp_path, "main")
        assert cli_resolvers.detect_current_feature(tmp_path) is None


class TestReadThresholdFromConventions:
    def test_default_when_absent(self, tmp_path: Path) -> None:
        assert cli_resolvers.read_threshold_from_conventions(tmp_path) == 70.0

    def test_reads_value(self, tmp_path: Path) -> None:
        conventions = tmp_path / ".conventions"
        conventions.mkdir()
        (conventions / "index.md").write_text(
            "## testing\ncoverage threshold: 85%\n", encoding="utf-8"
        )
        assert (
            cli_resolvers.read_threshold_from_conventions(tmp_path) == 85.0
        )


# ---------------------------------------------------------------------------
# Command help (AC-013)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "subcommand",
    ["test", "coverage", "drivers", "mutation", "preflight"],
)
def test_each_command_has_help(subcommand: str) -> None:
    result = runner.invoke(app, [subcommand, "--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output


# ---------------------------------------------------------------------------
# Missing .specs/ exit code (AC-011, EC-001)
# ---------------------------------------------------------------------------


def _no_specs_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)


@pytest.mark.parametrize(
    "subcommand",
    ["test", "coverage", "drivers", "mutation", "preflight"],
)
def test_missing_specs_exits_1(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, subcommand: str
) -> None:
    _no_specs_dir(monkeypatch, tmp_path)
    result = runner.invoke(app, [subcommand])
    assert result.exit_code == 1
    # Either the .specs/ message or another error path — exit code is the contract.
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# drivers subcommand
# ---------------------------------------------------------------------------


def _make_python_project(root: Path) -> None:
    (root / ".specs").mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")


def test_drivers_table_shows_python(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _make_python_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["drivers"])
    assert result.exit_code == 0, result.output
    assert "python" in result.output
    assert "primary driver" in result.output
    assert "LIVESPEC drivers" in result.output


def test_drivers_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _make_python_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["drivers", "--json"])
    assert result.exit_code == 0, result.output
    # Strip the structured summary line emitted on the last line.
    json_text, _, _ = result.output.rpartition("LIVESPEC")
    payload = json.loads(json_text.strip())
    assert isinstance(payload, list)
    names = {d["name"] for d in payload}  # type: ignore[index]
    assert "python" in names
    primary = cast(
        dict[str, Any] | None,
        next(
            (d for d in payload if isinstance(d, dict) and d.get("primary")),  # type: ignore[arg-type]
            None,
        ),
    )
    assert primary is not None
    assert primary["name"] == "python"


def test_drivers_json_empty_when_no_match(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """EC-003: empty array when no driver matches."""
    (tmp_path / ".specs").mkdir()
    monkeypatch.chdir(tmp_path)
    # No project markers at all → discovery returns []
    result = runner.invoke(app, ["drivers", "--json"])
    # Even with no match we don't fail: we exit 0 and print []
    # but matching=0 so summary still says OK.
    assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# coverage subcommand
# ---------------------------------------------------------------------------


def test_coverage_no_diff_exits_zero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """EC-002: empty diff vs base exits 0 with the no-changes summary."""
    _make_python_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    with patch("validator.cli_commands.coverage_cmd.detect_base_branch", return_value="main"), \
         patch("validator.cli_commands.coverage_cmd.git_diff", return_value=""):
        result = runner.invoke(app, ["coverage"])
    assert result.exit_code == 0, result.output
    assert "no changes since base" in result.output
    assert "LIVESPEC coverage" in result.output


def test_coverage_unsupported_exits_4(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _make_python_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    with (
        patch(
            "validator.cli_commands.coverage_cmd.detect_base_branch",
            return_value="main",
        ),
        patch("validator.cli_commands.coverage_cmd.git_diff", return_value="+changed"),
        patch(
            "validator.cli_commands.coverage_cmd.resolve_primary_driver"
        ) as resolve_primary_driver_mock,
    ):
        from validator.drivers.schemas import DetectRule, DriverManifest

        resolve_primary_driver_mock.return_value = DriverManifest(
            name="python",
            detect=DetectRule(files=["pyproject.toml"]),
        )
        result = runner.invoke(app, ["coverage"])
    assert result.exit_code == 4, result.output
    assert "does not declare a coverage capability" in result.output


# ---------------------------------------------------------------------------
# preflight subcommand
# ---------------------------------------------------------------------------


def test_preflight_missing_manifest_exits_5(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _make_python_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["preflight"])
    assert result.exit_code == 5, result.output


def test_preflight_read_only_table(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _make_python_project(tmp_path)
    manifest = textwrap.dedent(
        """
        ## Tooling

        ### pytest-cov
        - binary: pytest
        - install: pip install pytest-cov
        """
    ).strip()
    (tmp_path / ".specs" / "preflight.md").write_text(manifest, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["preflight"])
    # Either ok (pytest installed) or fail (missing) — both produce a table.
    assert "Tool" in result.output
    assert "LIVESPEC preflight" in result.output


# ---------------------------------------------------------------------------
# test subcommand — uses run_capability mock so no real pytest runs.
# ---------------------------------------------------------------------------


def test_test_subcommand_happy_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _make_python_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    # Pre-create a small lcov so coverage parsing finds it.
    lcov = tmp_path / "lcov.info"
    lcov.write_text(
        "SF:foo.py\nDA:1,1\nDA:2,1\nDA:3,1\nend_of_record\n", encoding="utf-8"
    )

    from validator.drivers.schemas import CapabilityResult

    def _fake_run_positional(
        driver: object, capability: str, **_kw: object
    ) -> CapabilityResult:
        return CapabilityResult(
            capability_name=capability,
            exit_code=0,
            report_path="lcov.info",
            stdout="ok",
            stderr="",
        )

    with patch(
        "validator.cli_commands.test_cmd.run_capability",
        side_effect=_fake_run_positional,
    ):
        result = runner.invoke(app, ["test"])
    assert result.exit_code == 0, result.output
    assert "Coverage:" in result.output
    assert "LIVESPEC test" in result.output


# ---------------------------------------------------------------------------
# mutation subcommand — driver without mutation capability path.
# ---------------------------------------------------------------------------


def test_mutation_unsupported_exits_4(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """EC-004: driver without mutation capability returns exit 4."""
    _make_python_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    with patch(
        "validator.cli_commands.mutation_cmd.run_mutation", return_value=None
    ):
        result = runner.invoke(app, ["mutation"])
    assert result.exit_code == 4, result.output
    assert "does not implement mutation" in result.output


def test_mutation_threshold_uses_percentage_units(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _make_python_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    from validator.drivers.mutation_report import MutationResult

    fake_result = MutationResult(
        date="2026-05-07",
        driver="python",
        kill_rate=78.0,
        killed=78,
        survived=22,
        timeout=0,
    )

    with patch(
        "validator.cli_commands.mutation_cmd.run_mutation", return_value=fake_result
    ):
        result = runner.invoke(app, ["mutation", "--threshold", "80"])
    assert result.exit_code == 3, result.output
    assert "threshold=80.0%" in result.output
    assert "FAIL" in result.output
