"""Feature 083 CLI tests: runtime commands bypass the migration guard (AC-010, FR-009)."""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from tests.runtime_support import (
    commit_all,
    install,
    make_project,
    make_source,
    restore_write_bits,
    write,
)
from validator.cli import app
from validator.runtime.home import RuntimeHome
from validator.runtime.project import pin_project
from validator.version_guard import ProjectMigrationRequiredError, enforce_project_migrated


@pytest.fixture
def stale_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Project at livespec-version 21 pinned to a VERSION 22 runtime (migration pending)."""
    monkeypatch.setenv("HOME", str(tmp_path / "user-home"))
    home = RuntimeHome((tmp_path / "runtime-home").resolve())
    monkeypatch.setenv("LIVESPEC_HOME", str(home.root))
    checkout = make_source(tmp_path / "checkout", version=22)
    install(home, checkout)
    project = make_project(tmp_path / "consumer", version=21)
    write(project / ".specs/spec-system.md", "# spec system\n")
    pin_project(project, "current", home)
    write(checkout / "README.md", "next\n")
    commit_all(checkout, "next")
    monkeypatch.chdir(project)
    yield project
    restore_write_bits(tmp_path)


def _invoke(monkeypatch: pytest.MonkeyPatch, *args: str) -> Result:
    monkeypatch.setattr(sys, "argv", ["livespec", *args])
    return CliRunner().invoke(app, list(args))


def test_runtime_commands_run_on_stale_project(
    stale_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-010: upgrade, status, pin, install and defect are not blocked by the guard."""
    upgrade = _invoke(monkeypatch, "runtime", "upgrade", "--to", "current", "--json")
    assert upgrade.exit_code == 0, upgrade.stderr
    assert json.loads(upgrade.stdout)["migration_required"] is True
    status = _invoke(monkeypatch, "runtime", "status", "--json")
    assert "not migrated" not in status.stderr
    assert json.loads(status.stdout)["mode"] == "pinned"
    assert _invoke(monkeypatch, "runtime", "pin", "--json").exit_code == 0
    checkout = stale_project.parent / "checkout"
    install_args = ["runtime", "install", "--source", str(checkout), "--no-activate", "--json"]
    assert _invoke(monkeypatch, *install_args).exit_code == 0
    defect = _invoke(monkeypatch, "runtime", "defect", "--command", "x", "--error", "y")
    assert defect.exit_code == 0


def test_non_runtime_commands_stay_guarded(
    stale_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-010: livespec doctor on the same stale project is still blocked."""
    doctor = _invoke(monkeypatch, "doctor")
    assert doctor.exit_code == 1 and "not migrated" in doctor.stderr


def test_guard_exempts_only_the_runtime_group(stale_project: Path) -> None:
    """FR-009: runtime subcommands bypass the guard; other guarded commands still raise."""
    subcommands = ("install", "pin", "upgrade", "dev", "status", "defect")
    bypassed = []
    for sub in subcommands:
        enforce_project_migrated(["runtime", sub], cwd=stale_project)
        bypassed.append(sub)
    assert bypassed == list(subcommands)
    refused = []
    for command in (["doctor"], ["status"], ["goal", "render", "spec-implement"]):
        with pytest.raises(ProjectMigrationRequiredError):
            enforce_project_migrated(command, cwd=stale_project)
        refused.append(command[0])
    assert refused == ["doctor", "status", "goal"]


@pytest.mark.parametrize(
    ("args", "reason"),
    [
        (["runtime", "pin", "--runtime", "21-cccccccccccc", "--json"], "not installed"),
        (["runtime", "upgrade", "--to", "21-cccccccccccc", "--json"], "not installed"),
        (["runtime", "dev", "--source", ".", "--json"], "not a LiveSpec root"),
    ],
    ids=["pin-uninstalled", "upgrade-uninstalled", "dev-not-root"],
)
def test_refusals_exit_1_without_writing(
    stale_project: Path, monkeypatch: pytest.MonkeyPatch, args: list[str], reason: str
) -> None:
    """AC-007/AC-009/AC-011: refused selections exit 1 with the reason and change nothing."""
    before = {
        path: path.read_bytes() for path in (stale_project / ".specs").rglob("*") if path.is_file()
    }
    result = _invoke(monkeypatch, *args)
    assert result.exit_code == 1 and reason in result.stderr and result.stdout == ""
    after = {
        path: path.read_bytes() for path in (stale_project / ".specs").rglob("*") if path.is_file()
    }
    assert after == before


def test_domain_errors_exit_1_on_stderr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI contract: a refused install exits 1 with the reason on stderr, nothing on stdout."""
    monkeypatch.setenv("HOME", str(tmp_path / "user-home"))
    args = ["runtime", "install", "--source", str(tmp_path), "--home", str(tmp_path / "h")]
    result = _invoke(monkeypatch, *args)
    assert result.exit_code == 1 and result.stdout == ""
    assert "not a LiveSpec root" in result.stderr
