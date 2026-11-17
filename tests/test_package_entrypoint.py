"""Packaged command dispatch must retain the installed shim's process contract."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _invoke(
    home: Path, cwd: Path, args: list[str], launcher: Path | None = None
) -> subprocess.CompletedProcess[str]:
    entry = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["scripts"]["livespec"]
    env = {**os.environ, "LIVESPEC_HOME": str(home), "PYTHONPATH": str(ROOT)}
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from importlib.metadata import EntryPoint; "
            "entry = sys.argv.pop(1); sys.argv[0] = sys.argv.pop(1); "
            "raise SystemExit(EntryPoint(name='livespec', value=entry, "
            "group='console_scripts').load()())",
            entry,
            str(launcher) if launcher else "livespec",
            *args,
        ],
        cwd=cwd,
        env=env,
        input="caller input",
        text=True,
        capture_output=True,
        timeout=10,
    )


def test_package_command_preserves_shim_arguments_input_cwd_and_exit(tmp_path: Path) -> None:
    home = tmp_path / "custom-home"
    shim = home / "bin" / "livespec"
    shim.parent.mkdir(parents=True)
    shim.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "print(json.dumps(dict(args=sys.argv[1:], cwd=os.getcwd(), input=sys.stdin.read())))\n"
        "raise SystemExit(7)\n"
    )
    shim.chmod(0o755)
    args = ["journey", "list", "--json"]
    result = _invoke(home, tmp_path, args)
    assert result.returncode == 7, result.stderr
    assert json.loads(result.stdout) == {
        "args": args,
        "cwd": str(tmp_path.resolve()),
        "input": "caller input",
    }


@pytest.mark.parametrize("state", ["missing", "non-executable", "recursive"])
def test_missing_or_invalid_shim_never_falls_back_to_checkout(tmp_path: Path, state: str) -> None:
    home = tmp_path / "runtime-home"
    shim = home / "bin" / "livespec"
    shim.parent.mkdir(parents=True)
    if state == "non-executable":
        shim.write_text("not executable\n")
    elif state == "recursive":
        # Simulate installing the console command over the shim itself.
        shim.symlink_to(sys.executable)
    result = _invoke(
        home, tmp_path, ["journey", "list", "--json"], shim if state == "recursive" else None
    )
    assert result.returncode == 3, result.stderr
    assert result.stdout == ""
    assert "livespec-shim:" in result.stderr
    assert "python -m validator.cli runtime install" in result.stderr
