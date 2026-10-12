"""Penflow CLI resolution works without an activated venv (feature 077, FR-007)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from validator.penflow_cli import PENFLOW_CLI_ENV, penflow_cli_missing, resolve_penflow_cli


def _executable(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o755)
    return path


@pytest.fixture
def interpreter_bin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fake environment bin directory holding the running interpreter."""
    bin_dir = tmp_path / "env" / "bin"
    bin_dir.mkdir(parents=True)
    monkeypatch.setattr(sys, "executable", str(bin_dir / "python"))
    monkeypatch.delenv(PENFLOW_CLI_ENV, raising=False)
    return bin_dir


def test_penflow_beside_interpreter_wins_over_path(
    tmp_path: Path, interpreter_bin: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sibling = _executable(interpreter_bin / "penflow")
    on_path = _executable(tmp_path / "path-bin" / "penflow")
    monkeypatch.setenv("PATH", str(on_path.parent))
    assert resolve_penflow_cli() == str(sibling)


def test_penflow_beside_interpreter_needs_no_path(
    interpreter_bin: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The unactivated-venv case: PATH lacks the venv, the interpreter's bin has penflow."""
    sibling = _executable(interpreter_bin / "penflow")
    monkeypatch.setenv("PATH", "")
    assert resolve_penflow_cli() == str(sibling)


def test_path_is_the_fallback(
    tmp_path: Path, interpreter_bin: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    on_path = _executable(tmp_path / "path-bin" / "penflow")
    monkeypatch.setenv("PATH", str(on_path.parent))
    assert resolve_penflow_cli() == str(on_path)


def test_non_executable_sibling_is_skipped(
    tmp_path: Path, interpreter_bin: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (interpreter_bin / "penflow").write_text("not runnable", encoding="utf-8")
    on_path = _executable(tmp_path / "path-bin" / "penflow")
    monkeypatch.setenv("PATH", str(on_path.parent))
    assert resolve_penflow_cli() == str(on_path)


def test_explicit_override_wins_and_never_falls_back(
    tmp_path: Path, interpreter_bin: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _executable(interpreter_bin / "penflow")
    override = _executable(tmp_path / "pinned" / "penflow")
    monkeypatch.setenv(PENFLOW_CLI_ENV, str(override))
    assert resolve_penflow_cli() == str(override)
    monkeypatch.setenv(PENFLOW_CLI_ENV, str(tmp_path / "missing" / "penflow"))
    assert resolve_penflow_cli() is None
    assert penflow_cli_missing("code").startswith(f"code: {PENFLOW_CLI_ENV}=")


def test_absent_everywhere_reports_searched_locations(
    interpreter_bin: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATH", "")
    assert resolve_penflow_cli() is None
    message = penflow_cli_missing("review_contract_penflow_cli_required")
    assert message.startswith("review_contract_penflow_cli_required: penflow not found in ")
    assert str(interpreter_bin) in message and PENFLOW_CLI_ENV in message


def test_injected_lookup_is_the_only_filesystem_seam(interpreter_bin: Path) -> None:
    calls: list[str] = []

    def lookup(name: str) -> str | None:
        calls.append(name)
        return None

    assert resolve_penflow_cli(lookup) is None
    assert calls == [str(interpreter_bin / "penflow"), "penflow"]


def test_unactivated_venv_interpreter_finds_its_own_penflow(tmp_path: Path) -> None:
    """End to end: a child interpreter with PATH stripped resolves penflow beside itself."""
    sibling = Path(sys.executable).parent / "penflow"
    if not os.access(sibling, os.X_OK):
        pytest.skip("this interpreter's environment has no Penflow CLI installed")
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"VIRTUAL_ENV", PENFLOW_CLI_ENV}
    }
    env["PATH"] = "/usr/bin:/bin"
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "from validator.penflow_cli import resolve_penflow_cli as r;print(r())",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == str(sibling)
