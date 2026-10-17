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
# @spec FR-002: Include bootstrap and later identities
#   — .specs/features/097-root-feature-delivery-review/spec.md#fr-002
def current_scope(root: Path, base_commit: str, feature: str | None = None) -> dict[str, str]:
    """Hash every counted path against the base, including a root-created feature tree.

    ``feature`` binds the logical pre-root baseline; absent it, use the ordinary diff.

    Raises:
        DiffUnavailableError: The diff or one of its paths cannot be read.
    """
    try:
        paths = {entry.path for entry in collect_diff(root, base_commit)}
        root_baseline = feature is not None and _root_feature_base(root, feature, base_commit)
        if root_baseline:
            # The logical state before the root is empty. Keep root paths as well
            # as later changes, including deletions, without creating Git objects.
            paths.update(
                raw.decode()
                for raw in _git(root, "ls-tree", "-r", "--name-only", "-z", base_commit).split(
                    b"\0"
                )
                if raw
            )
        return {
            path: _identity(root, path)
            for path in sorted(paths)
            if not is_traceability_artifact(path)
            and (root_baseline or not _lifecycle_only(root, base_commit, path))
        }
    except (OSError, ValueError) as exc:
        raise DiffUnavailableError(f"unreadable diff path: {exc}") from exc


# @spec FR-001: Preserve exact root baseline eligibility
#   — .specs/features/097-root-feature-delivery-review/spec.md#fr-001
# @spec FR-004: Preserve Git storage and original SHA
#   — .specs/features/097-root-feature-delivery-review/spec.md#fr-004
def _root_feature_base(root: Path, feature: str, commit: str) -> bool:
    """True only for a parentless commit containing this feature's original spec."""
    parents = _git(root, "rev-list", "--parents", "-n", "1", commit).decode().split()[1:]
    if parents:
        return False
    spec = f".specs/features/{feature}/spec.md"
    return bool(_git(root, "ls-tree", "--name-only", commit, "--", spec).strip())


def _feature_only(root: Path, feature: str, commit: str) -> bool:
    """True when ``commit`` changes nothing outside the feature directory."""
    changed = _git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", "--root", commit)
    prefix = f".specs/features/{feature}/"
    paths = changed.decode().split("\n")
    return all(path.startswith(prefix) for path in paths if path)


def base_problem(root: Path, feature: str, commit: str) -> str:
    """Why ``commit`` cannot be the base of the feature diff, or '' when it can.

    The base is the parent of the commit that created the feature spec, or older; the
    creating commit itself is accepted when feature-only, or when it is the root;
    a root baseline includes its entire tree in the review scope.

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
    if commit == first and (
        _root_feature_base(root, feature, first) or _feature_only(root, feature, first)
    ):
        return ""
    parents = _git(root, "rev-list", "--parents", "-n", "1", first).decode().split()[1:]
    if parents and is_ancestor(root, commit, parents[0]):
        return ""
    return f"{commit} is newer than the commit before {spec} was created ({first[:12]})"
