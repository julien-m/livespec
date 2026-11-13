"""The default Git hook does not reinstate automatic certification."""

import os
import subprocess
from pathlib import Path


def test_default_hook_never_launches_certification(tmp_path: Path) -> None:
    """An available failing validator is neither executed nor presented as passed."""
    (tmp_path / ".specs").mkdir()
    binaries = tmp_path / "bin"
    binaries.mkdir()
    called = tmp_path / "validator-called"
    validator = binaries / "livespec"
    validator.write_text('#!/bin/sh\ntouch "$CALLED_PATH"\nexit 42\n')
    validator.chmod(0o755)
    hook = Path(__file__).resolve().parents[1] / "validator/hooks/pre-commit-hook"
    result = subprocess.run(
        ["sh", str(hook)],
        cwd=tmp_path,
        env={**os.environ, "PATH": f"{binaries}:{os.environ['PATH']}", "CALLED_PATH": str(called)},
        capture_output=True,
        text=True,
        timeout=2,
        check=False,
    )
    assert result.returncode == 0
    assert not called.exists()
    assert "independent final review" in result.stdout
    assert "passed" not in result.stdout.lower()


def test_installer_migrates_exact_original_hook(tmp_path: Path) -> None:
    """The supported installer removes the known certification hook, not custom code."""
    from typer.testing import CliRunner

    from validator.cli import app

    sources = Path(__file__).resolve().parents[1] / "validator/hooks"
    hooks = tmp_path / ".git/hooks"
    hooks.mkdir(parents=True)
    target = hooks / "pre-commit"
    target.write_bytes((sources / "pre-commit-certification-hook").read_bytes())
    result = CliRunner().invoke(app, ["install-hook", "--target-dir", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert target.read_bytes() == (sources / "pre-commit-hook").read_bytes()


def test_installer_preserves_custom_hook_content(tmp_path: Path) -> None:
    """Migration does not silently delete a project's own checks."""
    from typer.testing import CliRunner

    from validator.cli import app

    hooks = tmp_path / ".git/hooks"
    hooks.mkdir(parents=True)
    target = hooks / "pre-commit"
    original = b"#!/bin/sh\nprintf '%s\\n' 'project check'\n"
    target.write_bytes(original)
    result = CliRunner().invoke(app, ["install-hook", "--target-dir", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert target.read_bytes().startswith(original)
    assert "custom checks remain unchanged" in result.output
