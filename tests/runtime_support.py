"""Shared builders for feature 083 runtime tests; everything lives in temporary directories.

Provides temporary LiveSpec git sources (minimal or carrying a copy of the real
runtime directories), consumer project fixtures, write-bit restoration for read-only
snapshots and a stub checkout recording how the shim executed it. The independent
digest and the protected-set fingerprint live in the test modules asserting on them.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from validator.runtime.home import RuntimeHome
from validator.runtime.models import SNAPSHOT_TEST_EVIDENCE, InstallResult
from validator.runtime.snapshot import InstallRequest, install_runtime

WORKTREE = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
FIXED_NOW = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)
# Worktree directories the real validator reads at import or run time.
REAL_CODE_DIRECTORIES = (
    "validator",
    "livespec",
    "system",
    ".agent-sync",
    "scripts",
    "migrations",
    "templates",
    "stacks",
)
_GIT_ENV = {
    "GIT_AUTHOR_NAME": "Runtime Test",
    "GIT_AUTHOR_EMAIL": "runtime@example.invalid",
    "GIT_COMMITTER_NAME": "Runtime Test",
    "GIT_COMMITTER_EMAIL": "runtime@example.invalid",
    "GIT_CONFIG_NOSYSTEM": "1",
}
# Stub CLI used by dev-mode shim tests: records argv, stdin, home and its own file.
_STUB_CLI = '''"""Stub LiveSpec CLI recording how the shim executed it."""
import json
import os
import sys
import tempfile


def app():
    payload = {
        "argv": sys.argv[1:],
        "stdin": sys.stdin.read(),
        "home": os.environ.get("LIVESPEC_HOME"),
        "file": __file__,
    }
    print(json.dumps(payload))
    raise SystemExit(7)
'''


def fixed_clock() -> datetime:
    """Return the deterministic clock used by runtime tests."""
    return FIXED_NOW


def git(repo: Path, *args: str) -> str:
    """Run git in ``repo`` with a deterministic identity and return stdout."""
    completed = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **_GIT_ENV},
    )
    return completed.stdout


def commit_all(repo: Path, message: str) -> str:
    """Stage everything, commit and return the full commit hash."""
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD").strip()


def write(path: Path, text: str, mode: int | None = None) -> Path:
    """Write ``text`` to ``path`` (creating parents), optionally chmod-ing it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if mode is not None:
        path.chmod(mode)
    return path


def _populate_shape(root: Path, version: int) -> None:
    write(root / "VERSION", f"{version}\n")
    write(root / ".agent-sync/skills/spec-check/SKILL.md", "# spec-check\n")
    write(root / ".agent-sync/skills/spec-implement/SKILL.md", "# spec-implement\n")
    write(root / ".agent-sync/rules/livespec/commands.md", "# commands\n")
    write(root / "system/tool-project-boundary.md", "# Tool/project boundary\n")
    write(root / "scripts/run.sh", "#!/bin/sh\necho run\n", mode=0o755)
    write(root / ".specs/README.md", "# excluded from snapshots\n")
    write(root / "tests/test_excluded.py", "# excluded from snapshots\n")
    (root / "docs").mkdir(exist_ok=True)
    os.symlink("../VERSION", root / "docs/version-link")


def _copy_real_code(root: Path) -> None:
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    for name in REAL_CODE_DIRECTORIES:
        shutil.copytree(WORKTREE / name, root / name, ignore=ignore, symlinks=True)
    # The bundled catalogs cite this evidence; install refuses a tree without it.
    for entry in SNAPSHOT_TEST_EVIDENCE:
        if entry.endswith("/"):
            shutil.copytree(WORKTREE / entry, root / entry, ignore=ignore)
        else:
            shutil.copy2(WORKTREE / entry, root / entry)


def make_source(root: Path, version: int = 21, real_code: bool = False) -> Path:
    """Create and commit a temporary LiveSpec git source.

    Args:
        root: Directory to create.
        version: Committed VERSION value.
        real_code: Copy the real runtime directories of this worktree (working-tree
            bytes, so uncommitted feature code is included) instead of a stub package.

    Returns:
        The repository root.
    """
    root.mkdir(parents=True)
    git(root, "init", "-q", "-b", "main")
    if real_code:
        _copy_real_code(root)
        write(root / "VERSION", f"{version}\n")
        write(root / ".specs/README.md", "# excluded from snapshots\n")
        write(root / "tests/test_excluded.py", "# excluded from snapshots\n")
    else:
        _populate_shape(root, version)
        write(root / "validator/__init__.py", '"""Stub validator package."""\n')
    commit_all(root, "initial")
    return root


def make_stub_checkout(root: Path) -> Path:
    """Create a non-git LiveSpec root whose ``validator.cli.app`` records its execution."""
    write(root / "VERSION", "21\n")
    (root / ".agent-sync/skills").mkdir(parents=True)
    write(root / "validator/__init__.py", '"""Stub validator package."""\n')
    write(root / "validator/cli.py", _STUB_CLI)
    return root


def install(
    home: RuntimeHome, source: Path, ref: str | None = None, activate: bool = True
) -> InstallResult:
    """Install ``source`` into ``home`` with the test interpreter and fixed clock."""
    request = InstallRequest(
        home=home, python=PYTHON, clock=fixed_clock, source=source, ref=ref, activate=activate
    )
    return install_runtime(request)


def make_project(root: Path, version: int = 21) -> Path:
    """Create a consumer project with ``.specs/livespec-version``."""
    write(root / ".specs/livespec-version", f"{version}\n")
    return root


def link_into(project: Path, relative: str, target: Path) -> Path:
    """Create ``<project>/.agent-sync.local/<relative>`` as a symlink to ``target``."""
    link = project / ".agent-sync.local" / relative
    link.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(str(target), link)
    return link


def restore_write_bits(root: Path) -> None:
    """Give the owner write permission on every directory and file below ``root``."""
    if not root.exists():
        return
    for dirpath, dirnames, filenames in os.walk(root):
        for name in [*dirnames, *filenames]:
            path = Path(dirpath) / name
            if not path.is_symlink():
                path.chmod(path.stat().st_mode | stat.S_IWUSR)
        Path(dirpath).chmod(Path(dirpath).stat().st_mode | stat.S_IWUSR)


def tree_hashes(root: Path, *, excluded_prefixes: tuple[str, ...] = ()) -> dict[str, str]:
    """Hash files/symlinks below ``root``, without reading explicitly excluded paths."""
    hashes: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        # Worktree-only callers must skip volatile Git internals before any file read.
        if relative.startswith(excluded_prefixes):
            continue
        if path.is_symlink():
            hashes[relative] = "link:" + os.readlink(path)
        elif path.is_file():
            hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def run_shim(
    home: RuntimeHome, cwd: Path, *args: str, stdin: str = "", env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Execute ``<home>/bin/livespec`` in ``cwd`` and capture its output.

    Stdin comes from a temporary file: feeding a pipe while draining a large
    stdout through ``communicate()`` was observed to stall on macOS.
    """
    with tempfile.TemporaryFile() as feed:
        feed.write(stdin.encode("utf-8"))
        feed.seek(0)
        return subprocess.run(
            [str(home.shim), *args],
            cwd=cwd,
            stdin=feed,
            capture_output=True,
            text=True,
            env=env if env is not None else dict(os.environ),
            timeout=120,
            check=False,
        )
