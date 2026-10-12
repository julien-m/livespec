"""Read-only git queries used to snapshot a committed LiveSpec tree.

Every call is a read-only query (``rev-parse``, ``status`` with optional locks
disabled, ``ls-tree``, ``cat-file --batch``); nothing writes the index or the
working tree. ``git archive`` is never used because it applies export attributes.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .errors import RuntimeSourceError
from .models import EXCLUDED_TOP_LEVEL

# Generous bound for local, network-free git queries on a large checkout (plan: 60 s).
GIT_TIMEOUT_SECONDS = 60
SYMLINK_MODE = "120000"
EXECUTABLE_MODE = "100755"
GITLINK_MODE = "160000"


@dataclass(frozen=True)
class TreeEntry:
    """One blob or gitlink of a commit tree as listed by ``git ls-tree``."""

    path: str
    mode: str
    oid: str

    @property
    def is_symlink(self) -> bool:
        """Return whether the entry is a symbolic link blob."""
        return self.mode == SYMLINK_MODE

    @property
    def is_executable(self) -> bool:
        """Return whether the entry is an executable regular file."""
        return self.mode == EXECUTABLE_MODE


def run_git(repo: Path, args: list[str], *, stdin: bytes | None = None) -> bytes:
    """Run one read-only git query and return its stdout bytes.

    Args:
        repo: Repository directory passed with ``git -C``.
        args: Git arguments after the global options.
        stdin: Optional bytes fed to the process.

    Returns:
        Raw stdout of a zero-exit git process.

    Raises:
        RuntimeSourceError: On a missing git binary, a timeout or a non-zero exit.
    """
    # Contract: `git --no-optional-locks -C <repo> <args>` exits 0 on success; any other
    # status means the query failed (unknown ref, not a repository). GIT_OPTIONAL_LOCKS=0
    # also stops implicit index refreshes so the source checkout is never written.
    env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
    command = ["git", "--no-optional-locks", "-C", str(repo), *args]
    # Input is fed from a temporary file, not a pipe: feeding a pipe while draining a
    # large stdout through communicate() was observed to stall on macOS.
    try:
        with tempfile.TemporaryFile() as feed:
            feed.write(stdin or b"")
            feed.seek(0)
            completed = subprocess.run(
                command,
                stdin=feed,
                capture_output=True,
                timeout=GIT_TIMEOUT_SECONDS,
                check=False,
                env=env,
            )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeSourceError(f"git {args[0]} failed in {repo}: {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", "replace").strip()
        raise RuntimeSourceError(f"git {args[0]} failed in {repo}: {detail}")
    return completed.stdout


def require_git_root(source: Path) -> Path:
    """Return ``source`` when it is the top level of a git working tree.

    Args:
        source: Candidate LiveSpec source directory.

    Returns:
        The resolved source path.

    Raises:
        RuntimeSourceError: If ``source`` is not a git working tree top level.
    """
    resolved = source.resolve()
    toplevel = run_git(resolved, ["rev-parse", "--show-toplevel"]).decode().strip()
    if Path(toplevel).resolve() != resolved:
        raise RuntimeSourceError(f"source is not the top level of a git working tree: {source}")
    return resolved


def resolve_commit(source: Path, ref: str) -> str:
    """Resolve a branch, tag or (abbreviated) hash to its full commit hash.

    Args:
        source: Git working tree.
        ref: Revision expression given to ``--ref`` (default ``HEAD``).

    Returns:
        The full commit hash.

    Raises:
        RuntimeSourceError: If ``ref`` resolves to no commit.
    """
    try:
        raw = run_git(source, ["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"])
    except RuntimeSourceError as exc:
        raise RuntimeSourceError(f"ref does not resolve to a commit in {source}: {ref}") from exc
    return raw.decode().strip()


def dirty_paths(repo: Path) -> list[str]:
    """List tracked changes and untracked non-ignored files of a working tree.

    Args:
        repo: Git working tree.

    Returns:
        Repository-relative dirty paths (empty for a clean tree).
    """
    raw = run_git(repo, ["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    records = iter(item for item in raw.decode("utf-8", "replace").split("\0") if item)
    paths: list[str] = []
    # Porcelain v1 -z records are "XY <path>"; a rename or copy (R/C) is followed by a
    # bare record holding its source path, which is consumed and not reported twice.
    for record in records:
        paths.append(record[3:])
        if "R" in record[:2] or "C" in record[:2]:
            next(records, None)
    return paths


def list_snapshot_entries(source: Path, commit: str) -> list[TreeEntry]:
    """List the commit tree minus top-level ``.specs/`` and ``tests/``.

    Args:
        source: Git working tree.
        commit: Full commit hash.

    Returns:
        Entries sorted by path.

    Raises:
        RuntimeSourceError: If the tree contains a gitlink (D-01).
    """
    raw = run_git(source, ["ls-tree", "-r", "-z", "--full-tree", commit])
    entries: list[TreeEntry] = []
    for record in raw.decode("utf-8", "surrogateescape").split("\0"):
        if not record:
            continue
        meta, path = record.split("\t", 1)
        mode, _kind, oid = meta.split(" ")
        if path.split("/", 1)[0] in EXCLUDED_TOP_LEVEL:
            continue
        if mode == GITLINK_MODE:
            raise RuntimeSourceError(f"gitlink (submodule) refused in {commit}: {path}")
        entries.append(TreeEntry(path=path, mode=mode, oid=oid))
    return sorted(entries, key=lambda entry: entry.path)


def read_blobs(source: Path, oids: list[str]) -> dict[str, bytes]:
    """Read blob contents through one ``git cat-file --batch`` process.

    Args:
        source: Git working tree.
        oids: Blob object ids (duplicates allowed).

    Returns:
        Mapping of object id to bytes.

    Raises:
        RuntimeSourceError: If an object is missing.
    """
    unique = sorted(set(oids))
    raw = run_git(source, ["cat-file", "--batch"], stdin="".join(f"{o}\n" for o in unique).encode())
    blobs: dict[str, bytes] = {}
    position = 0
    # Batch output repeats "<oid> <type> <size>\n<content>\n" in input order.
    for oid in unique:
        header_end = raw.index(b"\n", position)
        header = raw[position:header_end].split()
        if len(header) != 3:
            raise RuntimeSourceError(f"git object missing in {source}: {oid}")
        size = int(header[2])
        start = header_end + 1
        blobs[oid] = raw[start : start + size]
        position = start + size + 1
    return blobs
