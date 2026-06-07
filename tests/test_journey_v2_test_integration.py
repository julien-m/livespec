"""Integration tests for `livespec test` and compiled User Journeys v2."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pytest import MonkeyPatch
from typer.testing import CliRunner

from tests.test_journey_v2_validation import _write_feature, _write_v2_journey
from validator.cli import app
from validator.journeys.compiler import compile_journeys

runner = CliRunner()


@dataclass(frozen=True)
class _DriverStub:
    name: str = "python"


def test_livespec_test_runs_compiled_journey_gate_without_compiling(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """FR-024: `livespec test` fails on stale compiled journeys."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    source = _write_v2_journey(specs)
    compile_journeys(tmp_path, journey="onboarding-first-project")
    source.write_text(source.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "validator.cli_commands.test_cmd.resolve_primary_driver",
        lambda _: _DriverStub(),
    )

    result = runner.invoke(app, ["test", "--feature", "001-onboarding", "--no-coverage"])

    assert result.exit_code != 0
    assert "journey_compiled_stale" in result.output
