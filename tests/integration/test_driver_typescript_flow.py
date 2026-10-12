# LiveSpec traceability anchors
# @spec(AC-002)
# @spec(AC-003)
# @spec(AC-009)
# @spec(AC-012)

"""`livespec test` builds TS/JS commands from the project's runner and package manager."""

# @spec AC-002: jest vs vitest detection drives the command
# — .specs/features/018-driver-typescript-javascript/spec.md#ac-002
# @spec AC-012: npm / pnpm / yarn / bun prefix follows the project
# — .specs/features/018-driver-typescript-javascript/spec.md#ac-012

from __future__ import annotations

import json
import stat
from collections.abc import Mapping
from pathlib import Path

import pytest
from pytest import MonkeyPatch
from typer.testing import CliRunner

from validator.cli import app

_FAKE_TOOL = """#!/usr/bin/env python3
import json, pathlib, sys
log = pathlib.Path(sys.argv[0]).with_name("calls.jsonl")
with log.open("a") as handle:
    handle.write(json.dumps([pathlib.Path(sys.argv[0]).name, *sys.argv[1:]]) + "\\n")
if any(arg.startswith("--coverage") for arg in sys.argv[1:]):
    report = pathlib.Path("coverage/lcov.info")
    report.parent.mkdir(exist_ok=True)
    report.write_text("SF:a.ts\\nDA:1,1\\nend_of_record\\n")
"""


def _project(tmp_path: Path, monkeypatch: MonkeyPatch, package: Mapping[str, object]) -> Path:
    """Create a LiveSpec JS project and put fake npx/pnpm/yarn/bunx first on PATH."""
    project = tmp_path / "project"
    (project / ".specs").mkdir(parents=True)
    (project / "package.json").write_text(json.dumps(package), encoding="utf-8")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in ("npx", "pnpm", "yarn", "bunx"):
        fake = bin_dir / tool
        fake.write_text(_FAKE_TOOL, encoding="utf-8")
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{bin_dir}:/usr/bin:/bin")
    monkeypatch.chdir(project)
    return project


def _calls(tmp_path: Path) -> list[list[str]]:
    lines = (tmp_path / "bin" / "calls.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


@pytest.mark.level_3a
def test_jest_project_with_pnpm_runs_jest_coverage(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """A jest config plus pnpm lockfile yields `pnpm exec jest --coverage ...`."""
    project = _project(tmp_path, monkeypatch, {"name": "app", "devDependencies": {"jest": "29"}})
    (project / "jest.config.js").write_text("module.exports = {};\n", encoding="utf-8")
    (project / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")

    result = CliRunner().invoke(app, ["test"])

    assert result.exit_code == 0, result.output
    assert _calls(tmp_path) == [["pnpm", "exec", "jest", "--coverage", "--coverageReporters=lcov"]]
    assert "Coverage: 100.0%" in result.output


@pytest.mark.level_3a
def test_vitest_project_with_bun_package_manager_field_runs_vitest_coverage(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """`packageManager: bun@…` wins over a stale npm lockfile; vitest is detected."""
    package = {"name": "app", "packageManager": "bun@1.1.0", "devDependencies": {"vitest": "2"}}
    project = _project(tmp_path, monkeypatch, package)
    (project / "package-lock.json").write_text("{}", encoding="utf-8")

    result = CliRunner().invoke(app, ["test"])

    assert result.exit_code == 0, result.output
    assert _calls(tmp_path) == [["bunx", "vitest", "run", "--coverage", "--coverage.reporter=lcov"]]


@pytest.mark.level_3a
def test_project_override_keeps_priority_over_detection(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """`.specs/drivers/typescript.yaml` commands run verbatim, without detection."""
    project = _project(tmp_path, monkeypatch, {"name": "app", "devDependencies": {"jest": "29"}})
    (project / "yarn.lock").write_text("", encoding="utf-8")
    (project / ".specs" / "drivers").mkdir()
    (project / ".specs" / "drivers" / "typescript.yaml").write_text(
        "name: typescript\ndetect:\n  files: [package.json]\ncoverage:\n"
        "  command: npx vitest run --coverage --coverage.reporter=lcov\n"
        "  report_path: coverage/lcov.info\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["test"])

    assert result.exit_code == 0, result.output
    assert _calls(tmp_path) == [["npx", "vitest", "run", "--coverage", "--coverage.reporter=lcov"]]


@pytest.mark.level_3a
def test_mutation_without_stryker_emits_install_hint_and_succeeds(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """AC-009: `livespec test --mutation` skips Stryker with a pnpm install hint."""
    project = _project(tmp_path, monkeypatch, {"name": "app", "devDependencies": {"vitest": "2"}})
    (project / "pnpm-lock.yaml").write_text("", encoding="utf-8")

    result = CliRunner().invoke(app, ["test", "--no-coverage", "--mutation"])

    assert result.exit_code == 0, result.output
    assert "Install: pnpm add -D @stryker-mutator/core" in result.output
    assert not (tmp_path / "bin" / "calls.jsonl").exists()
