"""Install LiveSpec's advisory Git hook while preserving project-owned hooks."""

from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

# The former Bash installer embedded its current absolute source path in an otherwise
# fixed four-line dispatcher. Matching every byte around that path excludes composite hooks.
_LEGACY_DISPATCHER = re.compile(
    rb"#!/usr/bin/env bash\n# livespec-expectations\n"
    rb'python3 "/[^\r\n]*/hooks/livespec-last-reviewed\.py" \|\| exit 1\n'
    rb"livespec doctor --format json >/dev/null \|\| exit 1\n"
)


class HookInstallError(RuntimeError):
    """The hook destination cannot be used safely."""


def install_advisory_hook(project_root: Path) -> str:
    """Install at the project's default hook path and describe the observed outcome.

    The installer replaces only its own exact historical hook bytes. Existing custom
    bytes and permissions stay intact. A linked destination or ancestor is refused.
    """
    git_dir = project_root / ".git"
    hooks_dir = git_dir / "hooks"
    hook = hooks_dir / "pre-commit"
    for path in (git_dir, hooks_dir, hook):
        if path.is_symlink():
            raise HookInstallError(f"refusing to write linked pre-commit hook path: {path}")
    if not git_dir.is_dir():
        raise HookInstallError(f"{git_dir} does not exist as a directory")

    templates = Path(__file__).parent / "hooks"
    advisory = (templates / "pre-commit-hook").read_bytes()
    if hook.exists():
        if not hook.is_file():
            raise HookInstallError(f"pre-commit hook is not a regular file: {hook}")
        existing = hook.read_bytes()
        if existing == advisory:
            return "LiveSpec advisory hook already installed."
        historical = (templates / "pre-commit-certification-hook").read_bytes()
        if existing != historical and not _LEGACY_DISPATCHER.fullmatch(existing):
            return "Existing pre-commit hook retained byte-for-byte with its original mode."
        _replace_hook(hook, advisory)
        return "Replaced the original LiveSpec certification hook with the advisory hook."

    hooks_dir.mkdir(exist_ok=True)
    _replace_hook(hook, advisory)
    return f"Installed LiveSpec advisory pre-commit hook at {hook}"


def _replace_hook(hook: Path, content: bytes) -> None:
    # Publishing an executable sibling by rename avoids leaving a partial hook if a write fails.
    descriptor, staged_name = tempfile.mkstemp(prefix=".pre-commit-", dir=hook.parent)
    staged = Path(staged_name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(content)
        staged.chmod(0o755)
        staged.replace(hook)
    finally:
        staged.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        print(install_advisory_hook(Path(sys.argv[1])))
    except (HookInstallError, OSError) as error:
        sys.exit(f"Error: {error}")
