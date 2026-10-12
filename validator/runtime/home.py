"""Runtime home, project root and LiveSpec root resolution."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .errors import RuntimeLockError
from .models import MANIFEST_NAME, PROJECT_VERSION_RELPATH
from .shim_core import HOME_ENV, find_project_root, is_livespec_root

DEFAULT_HOME = Path("~") / ".livespec"


@dataclass(frozen=True)
class RuntimeHome:
    """Machine-local store of snapshots, the ``current`` pointer and the shim."""

    root: Path

    @property
    def versions(self) -> Path:
        """Directory holding one read-only snapshot per runtime id."""
        return self.root / "versions"

    @property
    def current(self) -> Path:
        """Symlink selecting the runtime used by unpinned projects."""
        return self.root / "current"

    @property
    def shim(self) -> Path:
        """Generated ``livespec`` CLI shim."""
        return self.root / "bin" / "livespec"

    def snapshot(self, runtime_id: str) -> Path:
        """Return the final snapshot path of ``runtime_id``."""
        return self.versions / runtime_id


# @spec FR-004: Home and project resolution
#   — .specs/features/083-pinned-runtime-isolation/spec.md#fr-004
def resolve_home(option: Path | None, environ: Mapping[str, str] | None = None) -> RuntimeHome:
    """Resolve the runtime home: ``--home`` > ``$LIVESPEC_HOME`` > ``~/.livespec``.

    Args:
        option: Value of ``--home`` or None.
        environ: Environment mapping; defaults to ``os.environ``.

    Returns:
        The runtime home with an absolute, symlink-resolved root.
    """
    env = os.environ if environ is None else environ
    raw = option if option is not None else Path(env.get(HOME_ENV) or DEFAULT_HOME)
    return RuntimeHome(root=raw.expanduser().resolve())


def require_project_root(start: Path) -> Path:
    """Return the project root of ``start`` or raise.

    Args:
        start: ``--project`` value or the working directory.

    Returns:
        The resolved project root.

    Raises:
        RuntimeLockError: If no ancestor of ``start`` contains ``.specs/``.
    """
    root = find_project_root(start)
    if root is None:
        raise RuntimeLockError(f"no LiveSpec project (.specs/) found from {start}")
    return root


def is_snapshot_root(path: Path) -> bool:
    """Return whether ``path`` is a LiveSpec root carrying a runtime manifest."""
    return is_livespec_root(path) and (path / MANIFEST_NAME).is_file()


def executing_root() -> Path:
    """Return the LiveSpec root whose ``validator`` package is executing this code."""
    # validator/runtime/home.py -> parents[0]=runtime, [1]=validator, [2]=LiveSpec root.
    return Path(__file__).resolve().parents[2]


def executing_validator() -> Path:
    """Return the path of the ``validator`` package executing this code."""
    return Path(__file__).resolve().parents[1]


def read_project_version(project_root: Path) -> int:
    """Read ``.specs/livespec-version``; a missing file counts as 1 like the migration guard.

    Args:
        project_root: Project root containing ``.specs/``.

    Returns:
        The integer project version.

    Raises:
        RuntimeLockError: If the file holds a non-integer value.
    """
    path = project_root / PROJECT_VERSION_RELPATH
    if not path.is_file():
        return 1
    raw = path.read_text(encoding="utf-8").strip()
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeLockError(f"project version is not an integer: {path}") from exc


# Re-exported so callers resolve roots through the same predicates as the shim.
__all__ = [
    "DEFAULT_HOME",
    "HOME_ENV",
    "RuntimeHome",
    "executing_root",
    "executing_validator",
    "find_project_root",
    "is_livespec_root",
    "is_snapshot_root",
    "read_project_version",
    "require_project_root",
    "resolve_home",
]
