"""Pure auto-detection helpers for the unified ``livespec`` CLI surface.

The functions in this module are intentionally side-effect-free (they may
read files but never mutate anything) so they can be unit-tested without a
fixture filesystem on every call.
"""

# @spec FR-006: Pure resolver helpers — .specs/features/035-unified-cli-surface/spec.md#fr-006

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .drivers.test_config import DEFAULT_THRESHOLD
from .exceptions import FeatureResolutionError


def detect_specs_root(start: Path | None = None) -> Path | None:
    """Walk upward from ``start`` looking for a ``.specs/`` directory.

    Args:
        start: Path to begin the search from. Defaults to the current working
            directory.

    Returns:
        The directory that contains ``.specs/`` (i.e. the project root), or
        ``None`` if no such directory is found before the filesystem root.
    """
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".specs").is_dir():
            return candidate
    return None


# @spec AC-004: origin/HEAD first, then local branches
# — .specs/features/035-unified-cli-surface/spec.md#ac-004
_LOCAL_BRANCH_ORDER: tuple[str, ...] = ("main", "master", "develop", "dev")
_REMOTE_HEAD_REF = "refs/remotes/origin/HEAD"
_REMOTE_PREFIX = "refs/remotes/"


def _run_git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    """Run one read-only git query, returning ``None`` when git is unavailable."""
    try:
        return subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None


def detect_base_branch(project_root: Path | None = None) -> str | None:
    """Return the base branch to diff against (AC-004).

    The remote default branch wins: ``refs/remotes/origin/HEAD`` resolved to
    ``origin/<branch>``. Without it, the first existing local branch among
    ``main``, ``master``, ``develop`` and ``dev`` is returned. Tags never match.

    Args:
        project_root: Working directory used for the ``git`` invocation. Defaults
            to the current working directory.

    Returns:
        ``origin/<branch>``, a local branch name, or ``None`` when no candidate
        exists or ``git`` is not available on ``PATH``.
    """
    cwd = project_root or Path.cwd()
    remote_head = _run_git(cwd, "symbolic-ref", "--quiet", _REMOTE_HEAD_REF)
    if remote_head is None:
        return None
    target = remote_head.stdout.strip()
    if remote_head.returncode == 0 and target.startswith(_REMOTE_PREFIX):
        return target.removeprefix(_REMOTE_PREFIX)
    for branch in _LOCAL_BRANCH_ORDER:
        verified = _run_git(cwd, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}")
        if verified is not None and verified.returncode == 0:
            return branch
    return None


def resolve_feature_dir(project_root: Path, value: str) -> Path:
    """Resolve a ``--feature`` value to exactly one feature directory (AC-002).

    An exact directory name under ``.specs/features/`` wins. Otherwise the value
    is a number matched as ``<value>-*``, so ``005`` never matches ``005.1-*``.

    Args:
        project_root: Project root containing ``.specs/features/``.
        value: The number (``035``) or full directory name (``035-unified-cli-surface``).

    Returns:
        The single matching feature directory.

    Raises:
        FeatureResolutionError: When zero or several directories match.
    """
    # @spec AC-002: Unique feature directory
    # — .specs/features/035-unified-cli-surface/spec.md#ac-002
    features_dir = project_root / ".specs" / "features"
    if value and "/" not in value and (features_dir / value).is_dir():
        return features_dir / value
    matches = sorted(p for p in features_dir.glob(f"{value}-*") if p.is_dir()) if value else []
    if len(matches) != 1:
        raise FeatureResolutionError(value, [p.name for p in matches])
    return matches[0]


_FEATURE_BRANCH_RE = re.compile(r"^feature/(\d{3}-[a-z0-9][a-z0-9-]*)$")


def detect_current_feature(project_root: Path | None = None) -> str | None:
    """Parse the current git branch into a feature slug.

    The expected branch shape is ``feature/NNN-kebab-name``. Anything else
    (including detached HEAD) returns ``None``.

    Args:
        project_root: Repository root used for the ``git`` call. Defaults to
            the current working directory.

    Returns:
        The slug ``NNN-kebab-name`` extracted from the branch name, or
        ``None`` when the heuristic does not apply.
    """
    cwd = project_root or Path.cwd()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(cwd),
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    branch = result.stdout.strip()
    match = _FEATURE_BRANCH_RE.match(branch)
    return match.group(1) if match else None


_THRESHOLD_RE = re.compile(
    r"(?:coverage[-_ ]?threshold|threshold)\s*[:=]\s*(\d+(?:\.\d+)?)\s*%?",
    re.IGNORECASE,
)


def read_threshold_from_conventions(project_root: Path | None = None) -> float:
    """Read the coverage threshold declared in ``.conventions/index.md``.

    The function looks for the first line of the form
    ``coverage threshold: NN`` (case-insensitive, optional ``%`` suffix)
    inside ``.conventions/index.md``. If the file does not exist or the
    pattern does not match, the historical default :data:`DEFAULT_THRESHOLD`
    is returned.

    Args:
        project_root: Project root containing the ``.conventions/`` directory.
            Defaults to the current working directory.

    Returns:
        Threshold expressed as a percentage (``70.0`` rather than ``0.70``).
    """
    root = project_root or Path.cwd()
    index = root / ".conventions" / "index.md"
    if not index.is_file():
        return DEFAULT_THRESHOLD
    try:
        text = index.read_text(encoding="utf-8")
    except OSError:
        return DEFAULT_THRESHOLD
    match = _THRESHOLD_RE.search(text)
    if match is None:
        return DEFAULT_THRESHOLD
    try:
        return float(match.group(1))
    except ValueError:
        return DEFAULT_THRESHOLD


__all__ = [
    "detect_base_branch",
    "detect_current_feature",
    "detect_specs_root",
    "read_threshold_from_conventions",
    "resolve_feature_dir",
]
