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
    # A file-backed feed avoids a macOS duplex pipe stall that can block inside
    # communicate()'s write and prevent its timeout from being checked.
    with tempfile.TemporaryFile() as feed:
        feed.write(stdin or b"")
        feed.seek(0)
        return subprocess.run(
            ["git", "-C", str(root), *args],
            stdin=feed,
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
    data, start = batch.stdout, 0
    for name, mode, _ in entries:
        end = data.index(b"\n", start)
        size = int(data[start:end].split()[2])
        blobs[name], start = (mode, data[end + 1 : end + 1 + size]), end + 2 + size
    return blobs


def _under_links(into: Path, name: str) -> bool:
    """Whether a directory on the way to ``name`` under ``into`` is a symlink."""
    current = into
    for part in name.split("/")[:-1]:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _escaping(into: Path, links: list[Path]) -> list[Path]:
    """The links that physically resolve outside ``into`` (a loop stays inside)."""
    inside = into.resolve()
    escaping = []
    for link in links:
        try:
            if not link.resolve().is_relative_to(inside):
                escaping.append(link)
        except (OSError, RuntimeError):  # A loop: reading it fails later, inside.
            continue
    return escaping


def _write(into: Path, blobs: dict[str, tuple[str, bytes]]) -> None:
    """Write blobs under ``into``; nothing is ever written or read outside it.

    Regular blobs come first and nothing is written under a symlink, so no write
    follows a link of the commit. A link that resolves outside ``into``, alone or
    through another link, is removed; a name both a link and a directory fails.
    """
    links: list[Path] = []
    for name, (mode, content) in sorted(blobs.items(), key=lambda item: item[1][0] == "120000"):
        if name.startswith("/") or {"", ".", ".."} & set(name.split("/")):
            continue
        if _under_links(into, name):
            raise ValueError(f"commit_path_under_symlink:{name}")
        path = into / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if mode == "120000":
            path.symlink_to(content.decode())
            links.append(path)
        else:
            path.write_bytes(content)
    while escaping := _escaping(into, links):
        for link in escaping:
            link.unlink()
            links.remove(link)


def _with_link_targets(
    top: Path, commit: str, blobs: dict[str, tuple[str, bytes]]
) -> dict[str, tuple[str, bytes]] | None:
    """Add the in-repository targets of the commit's symlinks, chained links included."""
    asked: set[str] = set()
    for _ in range(40):  # Bounded like the kernel's own symlink chain limit.
        targets = {
            posixpath.normpath(posixpath.join(posixpath.dirname(n), c.decode()))
            for n, (m, c) in blobs.items()
            if m == "120000"
        }
        missing = sorted(
            t for t in targets - asked - set(blobs) if t != "." and not t.startswith(("../", "/"))
        )
        if not missing:
            return blobs
        asked.update(missing)
        extra = _blobs(top, commit, missing)
        if extra is None:
            return None
        blobs = {**extra, **blobs}
    return None


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
        blobs = _with_link_targets(Path(top), commit, blobs)
        if blobs is None:
            return None
        _write(into, blobs)
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
