"""Official hook installation precedes backend capture and remains idempotent afterward."""

import subprocess
import time
from pathlib import Path

import pytest

from tests.test_init_profile import hybrid
from tests.test_init_recovery import ROOT, environment, execute, tree
from validator import init_from_code
from validator.init_profile import InitError
from validator.init_recovery import conventions_are_valid

CUSTOM_HOOK = '#!/bin/sh\nprintf "custom precommit preserved\\n"\n'


@pytest.mark.parametrize(
    ("has_hook", "has_ignore"), [(False, False), (True, False), (False, True), (True, True)]
)
def test_backend_official_hook_then_after_init_skip_then_verify(
    tmp_path: Path,
    has_hook: bool,
    has_ignore: bool,
) -> None:
    project = tmp_path / "git project"
    project.mkdir()
    hybrid(project)
    subprocess.run(["git", "init", "-q", str(project)], check=True, timeout=5)
    hook = project / ".git/hooks/pre-commit"
    if has_hook:
        hook.write_text(CUSTOM_HOOK)
        hook.chmod(0o755)
    if has_ignore:
        (project / ".gitignore").write_text("USER CUSTOM IGNORE\n.specs/.previews/\n")
    env = environment(tmp_path)
    initialized = execute(project, env)
    assert initialized.returncode == 0, initialized.stderr
    assert hook.is_file(), "backend must install official hook before capturing integration hashes"
    assert "# livespec-expectations" in hook.read_text()
    assert ".specs/.previews/" in (project / ".gitignore").read_text().splitlines()
    if has_hook:
        assert hook.read_text().startswith(CUSTOM_HOOK)
        backup = next((project / ".livespec-backups").iterdir())
        assert (backup / ".git/hooks/pre-commit").read_text() == CUSTOM_HOOK
    hook_bytes = hook.read_bytes()
    ignore_bytes = (project / ".gitignore").read_bytes()
    convention_bytes = tree(project / ".conventions")
    forced = execute(project, env, "--force")
    assert forced.returncode == 0, forced.stderr
    assert hook.read_bytes() == hook_bytes
    assert (project / ".gitignore").read_bytes() == ignore_bytes
    backups = list((project / ".livespec-backups").iterdir())
    assert len(backups) == (2 if has_hook else 1)
    assert any((backup / ".git/hooks/pre-commit").read_bytes() == hook_bytes for backup in backups)
    before = tree(project)
    official = subprocess.run(
        ["bash", str(ROOT / "scripts/install-hooks.sh"), str(project), str(ROOT)],
        env=env,
        stdin=subprocess.DEVNULL,
        text=True,
        capture_output=True,
        timeout=5,
    )
    assert official.returncode == 0, official.stderr
    assert "already installed" in official.stdout
    assert tree(project) == before
    # Apply the after-init valid-conventions branch: existing routing is retained unchanged.
    assert conventions_are_valid(project)
    assert tree(project / ".conventions") == convention_bytes
    verified = execute(project, env, "--verify-only")
    assert verified.returncode == 0, verified.stderr
    assert tree(project) == before
    assert (project / ".gitignore").read_text().splitlines().count(".specs/.previews/") == 1


def test_hook_installer_uses_remaining_deadline_and_cancels_descendants(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scripts = tmp_path / "fixture/scripts"
    scripts.mkdir(parents=True)
    (scripts / "install-hooks.sh").write_text("(sleep .4; echo bad > late) & wait\n")
    monkeypatch.setattr(init_from_code, "LIVESPEC_ROOT", scripts.parent)
    deadline = time.monotonic() + 0.15
    time.sleep(0.08)
    started = time.monotonic()
    with pytest.raises(InitError, match=r"install pre-commit hooks.*timeout"):
        init_from_code._install_hooks(tmp_path, deadline)
    assert time.monotonic() - started < 0.3
    time.sleep(0.5)
    assert not (tmp_path / "late").exists()


@pytest.mark.parametrize("external", [False, True])
def test_symlinked_hook_is_rejected_before_any_mutation(tmp_path: Path, external: bool) -> None:
    project = tmp_path / "app"
    project.mkdir()
    hybrid(project)
    subprocess.run(["git", "init", "-q", str(project)], check=True, timeout=5)
    target = (tmp_path if external else project) / "custom-hook"
    target.write_text(CUSTOM_HOOK)
    (project / ".git/hooks/pre-commit").symlink_to(target)
    env = environment(tmp_path)
    before = tree(project)
    result = execute(project, env, "--force")
    assert result.returncode != 0
    assert "writable" in result.stderr
    assert tree(project) == before and target.read_text() == CUSTOM_HOOK


def test_real_ignore_drift_is_still_rejected(tmp_path: Path) -> None:
    project = tmp_path / "app"
    project.mkdir()
    hybrid(project)
    env = environment(tmp_path)
    assert execute(project, env).returncode == 0
    (project / ".gitignore").write_text((project / ".gitignore").read_text() + "real-user-drift\n")
    before = tree(project)
    result = execute(project, env, "--verify-only")
    assert result.returncode != 0 and ".gitignore: generated content drift" in result.stderr
    assert tree(project) == before
