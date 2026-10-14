"""A spec revision record proves itself against the commit it was opened at (feature 094).

The record names the HEAD commit at opening. A recorded receipt is accepted only while
that commit is an ancestor of HEAD and the feature review prepared from that commit's
tree, exactly as a real opening would prepare it, has the receipt's sources, roles and
stable identity.
"""

from __future__ import annotations

import io
import os
import re
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..semantic.review_context import PreparedReview

_OBJECT_ID = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
# Replace objects and grafts would let local refs rewrite history (094 audit).
_ENV = {**os.environ, "GIT_NO_REPLACE_OBJECTS": "1"}


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=False, timeout=60, env=_ENV
    )


def _output(root: Path, *args: str) -> str | None:
    try:
        result = _git(root, *args)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.decode().strip() if result.returncode == 0 else None


def head_commit(root: Path) -> str | None:
    """The HEAD commit of the repository holding ``root``, or None outside git."""
    return _output(root, "rev-parse", "--verify", "HEAD^{commit}")


def is_ancestor(root: Path, commit: str) -> bool:
    """Whether ``commit``, a full object id, names HEAD or one of its ancestors."""
    if not _OBJECT_ID.fullmatch(commit):
        return False
    if _output(root, "rev-parse", "--verify", f"{commit}^{{commit}}") != commit:
        return False
    try:
        return _git(root, "merge-base", "--is-ancestor", commit, "HEAD").returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _checkout(root: Path, commit: str, paths: list[str], into: Path) -> Path | None:
    """Extract ``paths`` of ``commit`` with checkout filters; return the project root in it."""
    prefix = _output(root, "rev-parse", "--show-prefix")
    if prefix is None:
        return None
    try:
        archive = _git(root, "archive", "--format=tar", commit, "--", *paths)
        if archive.returncode != 0:
            return None
        with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
            tar.extractall(into, filter="data")
    except (OSError, subprocess.SubprocessError, tarfile.TarError):
        return None
    return into / prefix


def _targets(root: Path, names: dict[str, str]) -> set[str]:
    """Reviewed sources outside ``.specs`` and the in-project targets of symlinked ones."""
    base = root.resolve()
    targets = {name for name in names if not name.startswith(".specs/")}
    for name in names:
        resolved = (root / name).resolve()
        if resolved.is_relative_to(base) and resolved != (base / name):
            targets.add(resolved.relative_to(base).as_posix())
    return targets


# @spec FR-002: Reviewed sources at the opening commit
#   — .specs/features/094-verified-review-continuity/spec.md#fr-002
def matches_commit(root: Path, commit: str, reviewed: PreparedReview) -> bool:
    """Whether the review prepared from ``commit`` is the one the receipt reviewed.

    The project's ``.specs`` and every reviewed source outside it are extracted and the
    feature review is prepared there: same source names and roles, no error but the
    budget, and the same stable identity.
    """
    from ..semantic.review_files import prepare_feature_review
    from ..semantic.review_stability import (
        comparable,
        reviewed_roles,
        reviewed_snapshot,
        stable_identity,
    )

    paths = sorted({".specs", *_targets(root, reviewed.source_hashes)})
    with tempfile.TemporaryDirectory() as tmp:
        project = _checkout(root, commit, paths, Path(tmp))
        if project is None:
            return False
        try:
            at_commit = prepare_feature_review(
                project,
                reviewed.feature,
                reviewed.kind,
                reviewed.reviewer_model,
                reviewed.max_chars,
            )
        except (OSError, ValueError):
            return False
    return (
        comparable(at_commit)
        and set(at_commit.source_hashes) == set(reviewed.source_hashes)
        and reviewed_roles(at_commit) == reviewed_roles(reviewed)
        and stable_identity(reviewed_snapshot(at_commit)) == stable_identity(reviewed)
    )
