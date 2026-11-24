"""Official hook installation precedes backend capture and remains idempotent afterward."""

import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml

from tests.init_clock_support import FakeClock, install_deadline_seams
from tests.test_init_profile import hybrid
from tests.test_init_recovery import ROOT, environment, execute, tree
from validator import init_from_code
from validator.init_profile import InitError
from validator.init_recovery import conventions_are_valid

CUSTOM_HOOK = '#!/bin/sh\nprintf "custom precommit preserved\\n"\n'


def assert_conventions_ignored(project: Path) -> None:
    """Verify both generated files match the target's Git exclusion."""
    files = (".conventions/index.md", ".conventions/manifest.yaml")
    assert all((project / file).is_file() for file in files)
    for file in files:
        subprocess.run(
            ["git", "-c", "core.excludesFile=/dev/null", "check-ignore", "-q", "--", file],
            cwd=project,
            timeout=5,
            check=True,
        )
    result = subprocess.run(
        ["git", "-c", "core.excludesFile=/dev/null", "check-ignore", "-v", "--", *files],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    )
    assert [line.split("\t", 1)[0].split(":")[0] for line in result.stdout.splitlines()] == [
        ".gitignore",
        ".gitignore",
    ]


def test_interactive_install_generates_ignored_conventions(tmp_path: Path) -> None:
    project = tmp_path / "interactive project"
    project.mkdir()
    subprocess.run(["git", "init", "-q", str(project)], check=True, timeout=5)
    assert not (project / ".gitignore").exists()
    env = environment(tmp_path)
    env["PYTHONPATH"] = str(ROOT)
    subprocess.run(
        ["bash", str(ROOT / "scripts/init.sh"), str(project)],
        env=env,
        check=True,
        timeout=30,
    )
    # Apply the documented fresh-project version and the interview's stack choice.
    (project / ".specs/livespec-version").write_bytes((ROOT / "VERSION").read_bytes())
    (project / ".specs/stacks/_default.md").write_text("# Stack\n\nPython CLI\n")
    subprocess.run(
        [sys.executable, "-B", "-m", "validator.cli", "conventions", "refresh", "--repo", "."],
        cwd=project,
        env=env,
        check=True,
        timeout=30,
    )
    assert_conventions_ignored(project)
    assert_conventions_manifest(project, Path(env["AIRESOURCES"]))


def assert_conventions_manifest(project: Path, resources: Path) -> None:
    """Verify the normal refresh workflow can use the generated manifest."""
    manifest = yaml.safe_load((project / ".conventions/manifest.yaml").read_text())
    assert manifest["ai_resources_path"] == str(resources)
    assert manifest["generated"]
    sources = manifest["domains"]["code"]["sources"]
    assert sources and all((resources / source).is_file() for source in sources)


@pytest.mark.parametrize(
    ("has_hook", "has_ignore"), [(False, False), (True, False), (False, True), (True, True)]
)
def test_backend_official_hook_then_after_init_skip_then_verify(
    tmp_path: Path,
    has_hook: bool,
    has_ignore: bool,
    monkeypatch: pytest.MonkeyPatch,
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
        (project / ".gitignore").write_text(
            "USER CUSTOM IGNORE\n.specs/.previews/\n.conventions/\n!.conventions/\n"
        )
    env = environment(tmp_path)
    initialized = execute(project, env)
    assert initialized.returncode == 0, initialized.stderr
    assert_conventions_ignored(project)
    assert_conventions_manifest(project, Path(env["AIRESOURCES"]))
    assert hook.is_file(), "backend must install official hook before capturing integration hashes"
    assert "this hook runs no automatic certification" in hook.read_text()
    assert "livespec doctor" not in hook.read_text()
    assert ".specs/.previews/" in (project / ".gitignore").read_text().splitlines()
    if has_hook:
        assert hook.read_text().startswith(CUSTOM_HOOK)
        backup = next((project / ".livespec-backups").iterdir())
        assert (backup / ".git/hooks/pre-commit").read_text() == CUSTOM_HOOK
    if has_ignore:
        assert (project / ".gitignore").read_text().startswith("USER CUSTOM IGNORE\n")
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
    # The in-process check resolves the same fixture corpus as the backend, not the caller's.
    monkeypatch.setenv("AIRESOURCES", env["AIRESOURCES"])
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
    (scripts / "install-hooks.sh").write_text("(sleep 1; echo bad > late) & wait\n")
    monkeypatch.setattr(init_from_code, "LIVESPEC_ROOT", scripts.parent)
    clock = FakeClock()
    timeouts = install_deadline_seams(monkeypatch, clock)
    deadline = clock.now + 0.15
    clock.now += 0.08  # earlier init steps already consumed part of the run budget
    with pytest.raises(InitError, match=r"install pre-commit hooks.*timeout"):
        init_from_code._install_hooks(tmp_path, deadline)
    # The installer got the remaining 0.07 s, not a fresh budget; the late write never lands.
    assert timeouts[0] == pytest.approx(0.07)
    time.sleep(1.2)
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
