"""Scope of one delivery review: the base rule and the identity of each diff path (086 FR-004).

The base must precede everything the feature committed, so no feature change can sit
outside the scope; ``prepare``, ``record`` and ``verify`` all apply the same rule.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from ..bugfix.diff import (
    DiffUnavailableError,
    _git,  # pyright: ignore[reportPrivateUsage]
    base_text,
    collect_diff,
    is_ancestor,
    is_traceability_artifact,
)
from ..normative_identity import normative_hash
from .review_models import DELETED

_LIFECYCLE = ("spec.md", "plan.md")


def _lifecycle_document(relative: str) -> bool:
    parts = Path(relative).parts
    return len(parts) == 4 and parts[:2] == (".specs", "features") and parts[3] in _LIFECYCLE


def _lifecycle_only(root: Path, base_commit: str, relative: str) -> bool:
    """A spec or plan whose normative content equals the base is not a change."""
    path = root / relative
    if not _lifecycle_document(relative) or path.is_symlink() or not path.is_file():
        return False
    before = base_text(root, base_commit, relative)
    current = path.read_text(encoding="utf-8")
    return before is not None and normative_hash(before, lifecycle_document=True) == normative_hash(
        current, lifecycle_document=True
    )


def _gitlink(root: Path, relative: str) -> str:
    """Object id of a submodule entry; any other directory has no reviewable identity."""
    staged = _git(root, "ls-files", "-s", "--", relative).decode().split()
    if len(staged) >= 2 and staged[0] == "160000":
        return "gitlink:" + staged[1]
    raise ValueError(f"{relative} is a directory, not a file or a submodule")


def _identity(root: Path, relative: str) -> str:
    """Hash a path without following links; lifecycle-only spec/plan edits keep their hash."""
    path = root / relative
    if path.is_symlink():
        return "symlink:" + os.readlink(path)
    if not os.path.lexists(path):
        return DELETED
    if path.is_dir():
        return _gitlink(root, relative)
    data = path.read_bytes()
    if _lifecycle_document(relative):
        return "normative:" + normative_hash(data.decode(), lifecycle_document=True)
    return hashlib.sha256(data).hexdigest()


# @spec FR-004: Complete feature diff scope
#   — .specs/features/086-risk-proportional-delivery/spec.md#fr-004
def current_scope(root: Path, base_commit: str) -> dict[str, str]:
    """Hash every counted path of the feature diff against ``base_commit``.

    Raises:
        DiffUnavailableError: The diff or one of its paths cannot be read.
    """
    try:
        return {
            entry.path: _identity(root, entry.path)
            for entry in collect_diff(root, base_commit)
            if not is_traceability_artifact(entry.path)
            and not _lifecycle_only(root, base_commit, entry.path)
        }
    except (OSError, ValueError) as exc:
        raise DiffUnavailableError(f"unreadable diff path: {exc}") from exc


def _feature_only(root: Path, feature: str, commit: str) -> bool:
    """True when ``commit`` changes nothing outside the feature directory."""
    changed = _git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", "--root", commit)
    prefix = f".specs/features/{feature}/"
    paths = changed.decode().split("\n")
    return all(path.startswith(prefix) for path in paths if path)


def base_problem(root: Path, feature: str, commit: str) -> str:
    """Why ``commit`` cannot be the base of the feature diff, or '' when it can.

    The base is the parent of the commit that created the feature spec, or older; the
    creating commit itself is accepted only when it touches the feature directory alone.

    Raises:
        DiffUnavailableError: git cannot answer.
    """
    if not is_ancestor(root, commit, "HEAD"):
        return f"{commit} is not an ancestor of HEAD"
    spec = f".specs/features/{feature}/spec.md"
    created = _git(root, "log", "--format=%H", "--diff-filter=A", "--", spec).decode().split()
    if not created:
        return f"{spec} is not committed: commit it so the start of the feature is known"
    first = created[-1]
    if commit == first and _feature_only(root, feature, first):
        return ""
    parents = _git(root, "rev-list", "--parents", "-n", "1", first).decode().split()[1:]
    if parents and is_ancestor(root, commit, parents[0]):
        return ""
    return f"{commit} is newer than the commit before {spec} was created ({first[:12]})"
