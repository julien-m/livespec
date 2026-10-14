"""A spec revision record proves itself against the commit it was opened at (feature 094).

The record names the HEAD commit at opening. A recorded receipt is accepted only while
that commit is an ancestor of HEAD and the feature review prepared from that commit's
tree, exactly as a real opening would prepare it, has the receipt's sources, roles and
stable identity. The tree is written from raw git objects: no filter, attribute or
replace object of the local repository changes what the commit holds.
"""

from __future__ import annotations

import os
import posixpath
import re
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..semantic.review_context import PreparedReview

_OBJECT_ID = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
# Replace objects would let local refs rewrite history; pathspecs are plain names.
_CONFIG = ".specs/semantic/config.yaml"
_ENV = {**os.environ, "GIT_NO_REPLACE_OBJECTS": "1", "GIT_LITERAL_PATHSPECS": "1"}


def _git(root: Path, *args: str, stdin: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        input=stdin,
        capture_output=True,
        check=False,
        timeout=60,
        env=_ENV,
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


def _blobs(top: Path, commit: str, paths: list[str]) -> dict[str, tuple[str, bytes]] | None:
    """Mode and raw content of every blob under ``paths`` (relative to the top) at ``commit``."""
    listing = _git(top, "ls-tree", "-r", "-z", "--full-tree", commit, "--", *paths)
    if listing.returncode != 0:
        return None
    entries = []
    for record in listing.stdout.split(b"\0"):
        if record:
            meta, _, raw_name = record.partition(b"\t")
            mode, kind, sha = meta.decode().split()
            if kind == "blob":
                entries.append((raw_name.decode("utf-8"), mode, sha))
    batch = _git(top, "cat-file", "--batch", stdin="".join(f"{e[2]}\n" for e in entries).encode())
    if batch.returncode != 0:
        return None
    blobs: dict[str, tuple[str, bytes]] = {}
    data = batch.stdout
    for name, mode, _ in entries:
        header, _, data = data.partition(b"\n")
        size = int(header.split()[2])
        blobs[name], data = (mode, data[:size]), data[size + 1 :]
    return blobs


def _write(into: Path, blobs: dict[str, tuple[str, bytes]]) -> None:
    """Write blobs under ``into``; a symlink is kept only when it stays inside ``into``."""
    for name, (mode, content) in blobs.items():
        if name.startswith("/") or ".." in name.split("/"):
            continue
        path = into / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if mode == "120000":
            target = posixpath.normpath(posixpath.join(posixpath.dirname(name), content.decode()))
            if not target.startswith("../") and target != ".." and not target.startswith("/"):
                path.symlink_to(content.decode())
        else:
            path.write_bytes(content)


def _checkout(root: Path, commit: str, paths: list[str], into: Path) -> Path | None:
    """Write ``paths`` of the project at ``commit`` and the in-repository targets of its
    symlinks; return the project root inside ``into``."""
    top, prefix = (
        _output(root, "rev-parse", "--show-toplevel"),
        _output(root, "rev-parse", "--show-prefix"),
    )
    if top is None or prefix is None:
        return None
    try:
        blobs = _blobs(Path(top), commit, [prefix + p for p in paths])
        if blobs is None:
            return None
        links = {
            posixpath.normpath(posixpath.join(posixpath.dirname(n), c.decode()))
            for n, (m, c) in blobs.items()
            if m == "120000"
        }
        missing = sorted(t for t in links if t not in blobs and not t.startswith(("../", "/")))
        extra = _blobs(Path(top), commit, missing) if missing else {}
        _write(into, {**(extra or {}), **blobs})
    except (OSError, subprocess.SubprocessError, UnicodeError, ValueError, IndexError):
        return None
    return into / prefix


def _same_configuration(
    project: Path, at_commit: PreparedReview, reviewed: PreparedReview
) -> PreparedReview:
    """Take the reviewed configuration hash when the committed one differs only in line
    endings (a CRLF checkout of an LF blob)."""
    from ..semantic.review_context import content_hash

    config = project / _CONFIG
    text = config.read_bytes().decode("utf-8") if config.is_file() else ""
    lf = text.replace("\r\n", "\n")
    expected = reviewed.dependencies.get("semantic_config")
    if expected in {content_hash(lf), content_hash(lf.replace("\n", "\r\n"))}:
        dependencies = {**at_commit.dependencies, "semantic_config": expected}
        return at_commit.model_copy(update={"dependencies": dependencies})
    return at_commit


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

    paths = sorted({".specs", *(n for n in reviewed.source_hashes if not n.startswith(".specs/"))})
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
            at_commit = _same_configuration(project, at_commit, reviewed)
        except (OSError, ValueError, RuntimeError):  # RuntimeError: a symlink loop.
            return False
    return (
        comparable(at_commit)
        and set(at_commit.source_hashes) == set(reviewed.source_hashes)
        and reviewed_roles(at_commit) == reviewed_roles(reviewed)
        and stable_identity(reviewed_snapshot(at_commit)) == stable_identity(reviewed)
    )
