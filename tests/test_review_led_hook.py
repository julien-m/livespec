"""The default Git hook does not reinstate automatic certification."""

import os
import stat
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.cli import app

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "validator/hooks"


def _install(project: Path, interface: str) -> tuple[int, str]:
    if interface == "cli":
        result = CliRunner().invoke(app, ["install-hook", "--target-dir", str(project)])
        return result.exit_code, result.output
    run = subprocess.run(
        ["bash", str(ROOT / "scripts/install-hooks.sh"), str(project), str(ROOT)],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    return run.returncode, run.stdout + run.stderr


def _legacy_dispatcher(source: Path) -> bytes:
    """Render the four lines written by the old default installer."""
    return (
        "#!/usr/bin/env bash\n"
        "# livespec-expectations\n"
        f'python3 "{source}/hooks/livespec-last-reviewed.py" || exit 1\n'
        "livespec doctor --format json >/dev/null || exit 1\n"
    ).encode()


def test_default_hook_never_launches_certification(tmp_path: Path) -> None:
    """An available failing validator is neither executed nor presented as passed."""
    (tmp_path / ".specs").mkdir()
    binaries = tmp_path / "bin"
    binaries.mkdir()
    called = tmp_path / "validator-called"
    validator = binaries / "livespec"
    validator.write_text('#!/bin/sh\ntouch "$CALLED_PATH"\nexit 42\n')
    validator.chmod(0o755)
    hook = TEMPLATES / "pre-commit-hook"
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


@pytest.mark.parametrize("interface", ["bash", "cli"])
@pytest.mark.parametrize("historical", ["certification-template", "bash-dispatcher"])
def test_installer_migrates_exact_original_hook(
    tmp_path: Path, interface: str, historical: str
) -> None:
    """The supported installer removes the known certification hook, not custom code."""
    hooks = tmp_path / ".git/hooks"
    hooks.mkdir(parents=True)
    target = hooks / "pre-commit"
    original = (
        (TEMPLATES / "pre-commit-certification-hook").read_bytes()
        if historical == "certification-template"
        else _legacy_dispatcher(tmp_path / "previous source path")
    )
    target.write_bytes(original)
    code, output = _install(tmp_path, interface)
    assert code == 0, output
    assert "Replaced the original" in output
    assert target.read_bytes() == (TEMPLATES / "pre-commit-hook").read_bytes()
    assert stat.S_IMODE(target.stat().st_mode) == 0o755
    code, output = _install(tmp_path, interface)
    assert code == 0 and "already installed" in output
    assert target.read_bytes() == (TEMPLATES / "pre-commit-hook").read_bytes()


@pytest.mark.parametrize("interface", ["bash", "cli"])
@pytest.mark.parametrize("custom", ["python", "composite"])
def test_installer_preserves_custom_hook_content(
    tmp_path: Path, interface: str, custom: str
) -> None:
    """Migration does not silently delete a project's own checks."""
    hooks = tmp_path / ".git/hooks"
    hooks.mkdir(parents=True)
    target = hooks / "pre-commit"
    if custom == "python":
        original = b'#!/usr/bin/env python3\nprint("project check")\n'
    else:
        original = _legacy_dispatcher(tmp_path / "previous source") + b'echo "project check"\n'
    target.write_bytes(original)
    target.chmod(0o750)
    code, output = _install(tmp_path, interface)
    assert code == 0, output
    assert target.read_bytes() == original
    assert stat.S_IMODE(target.stat().st_mode) == 0o750
    assert "retained byte-for-byte" in output
    if custom == "python":
        run = subprocess.run([str(target)], capture_output=True, text=True, timeout=5, check=True)
        assert run.stdout == "project check\n"


@pytest.mark.parametrize("interface", ["bash", "cli"])
def test_installer_refuses_linked_hooks_directory(tmp_path: Path, interface: str) -> None:
    target = tmp_path / "shared-hooks"
    target.mkdir()
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "hooks").symlink_to(target, target_is_directory=True)
    code, output = _install(tmp_path, interface)
    assert code == 1 and "refusing to write linked" in output
    assert not (target / "pre-commit").exists()
