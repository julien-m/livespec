"""A spec revision record proves itself against the commit it was opened at (feature 094).

The record names the HEAD commit at opening. A recorded receipt is accepted only while
that commit is an ancestor of HEAD and the reviewed sources at that commit have the
stable identity of the receipt's reviewed context.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..semantic.review_context import PreparedReview

_CONFIG = ".specs/semantic/config.yaml"


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=False, timeout=60
    )


def head_commit(root: Path) -> str | None:
    """The HEAD commit of the repository holding ``root``, or None outside git."""
    try:
        result = _git(root, "rev-parse", "--verify", "HEAD^{commit}")
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.decode().strip() if result.returncode == 0 else None


def is_ancestor(root: Path, commit: str) -> bool:
    """Whether ``commit`` is HEAD or one of its ancestors."""
    if not commit or commit.startswith("-"):
        return False
    try:
        return _git(root, "merge-base", "--is-ancestor", commit, "HEAD").returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _show(root: Path, commit: str, name: str) -> str | None:
    try:
        result = _git(root, "show", f"{commit}:./{name}")
        return result.stdout.decode("utf-8") if result.returncode == 0 else None
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return None


# @spec FR-002: Reviewed sources at the opening commit
#   — .specs/features/094-verified-review-continuity/spec.md#fr-002
def matches_commit(root: Path, commit: str, reviewed: PreparedReview) -> bool:
    """Whether the reviewed sources at ``commit`` have the reviewed stable identity."""
    from ..semantic.review_context import content_hash
    from ..semantic.review_stability import prepare_like, reviewed_snapshot, stable_identity

    texts: dict[str, str] = {}
    for name in reviewed.source_hashes:
        text = _show(root, commit, name)
        if text is None:
            return False
        texts[name] = text
    dependencies = dict(reviewed.dependencies)
    if "semantic_config" in dependencies:
        dependencies["semantic_config"] = content_hash(_show(root, commit, _CONFIG) or "")
    at_commit = reviewed_snapshot(prepare_like(reviewed, texts, dependencies))
    return stable_identity(at_commit) == stable_identity(reviewed)
