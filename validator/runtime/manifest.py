"""Snapshot manifest I/O, content digest and verification."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Iterator
from pathlib import Path

from .errors import RuntimeSnapshotError
from .home import RuntimeHome
from .models import (
    DIGEST_PREFIX,
    MANIFEST_NAME,
    RuntimeManifest,
    manifest_from_dict,
    require_snapshot_identity,
)

_WRITE_BITS = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH


def _iter_entries(root: Path) -> Iterator[tuple[str, str, str, bytes]]:
    """Yield ``(relpath, kind, exec, payload)`` for every file and symlink under ``root``."""
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        base = Path(dirpath)
        # os.walk lists symlinks to directories under dirnames without descending into them.
        for name in [*dirnames, *filenames]:
            path = base / name
            rel = path.relative_to(root).as_posix()
            if rel == MANIFEST_NAME:
                continue
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                yield rel, "symlink", "0", os.readlink(path).encode("utf-8", "surrogateescape")
            elif stat.S_ISREG(mode):
                executable = "1" if mode & stat.S_IXUSR else "0"
                yield rel, "file", executable, path.read_bytes()


# @spec FR-002: Content digest — .specs/features/083-pinned-runtime-isolation/spec.md#fr-002
def compute_digest(root: Path) -> str:
    """Compute the content digest of a snapshot tree, excluding its manifest.

    Records ``kind\\0exec\\0relpath\\0sha256(payload)\\n`` are hashed in sorted POSIX
    relative-path order; a file payload is its bytes, a symlink payload its target text.

    Args:
        root: Snapshot or staging directory.

    Returns:
        ``sha256:<hex>`` digest.
    """
    records = sorted(_iter_entries(root), key=lambda item: item[0])
    digest = hashlib.sha256()
    for rel, kind, executable, payload in records:
        line = f"{kind}\0{executable}\0{rel}\0{hashlib.sha256(payload).hexdigest()}\n"
        digest.update(line.encode("utf-8", "surrogateescape"))
    return f"{DIGEST_PREFIX}{digest.hexdigest()}"


# @spec FR-002: Read-only verification
#   — .specs/features/083-pinned-runtime-isolation/spec.md#fr-002
def writable_entries(root: Path) -> list[str]:
    """List the root and entries (symlinks excluded) carrying any write permission bit.

    Args:
        root: Snapshot directory.

    Returns:
        Relative POSIX paths (``.`` for the root) that are writable, sorted.
    """
    found: list[str] = []
    candidates = [root, *(Path(d) / n for d, ds, fs in os.walk(root) for n in [*ds, *fs])]
    for path in candidates:
        mode = path.lstat().st_mode
        if not stat.S_ISLNK(mode) and mode & _WRITE_BITS:
            found.append(path.relative_to(root).as_posix())
    return sorted(found)


def manifest_bytes(manifest: RuntimeManifest) -> bytes:
    """Serialize a manifest as sorted, indented JSON with a trailing newline."""
    return (json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n").encode("utf-8")


def read_manifest(snapshot: Path) -> RuntimeManifest:
    """Read and validate ``<snapshot>/.livespec-runtime.json``.

    Args:
        snapshot: Snapshot directory.

    Returns:
        The validated manifest.

    Raises:
        RuntimeSnapshotError: If the manifest is missing, unreadable or invalid.
    """
    path = snapshot / MANIFEST_NAME
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeSnapshotError(f"runtime manifest missing or unreadable: {path}") from exc
    return manifest_from_dict(raw, path)


def verify_snapshot(
    home: RuntimeHome, runtime_id: str, commit: str | None = None
) -> RuntimeManifest:
    """Verify an installed snapshot's manifest identity and recomputed content digest.

    Args:
        home: Runtime home.
        runtime_id: Runtime id to verify.
        commit: Full commit the manifest must record (install ref or lock), when known.

    Returns:
        The verified manifest.

    Raises:
        RuntimeSnapshotError: If the snapshot is missing or a symlink, its manifest does
            not match the runtime id or commit, its content digest differs from the
            manifest, or any directory or file regained a write permission bit.
    """
    snapshot = home.snapshot(runtime_id)
    if snapshot.is_symlink() or not snapshot.is_dir():
        raise RuntimeSnapshotError(
            f"runtime {runtime_id} is not installed under {home.versions}; "
            "run `livespec runtime install --source <livespec repo> --ref <commit>`"
        )
    manifest = read_manifest(snapshot)
    require_snapshot_identity(manifest, runtime_id, snapshot)
    if commit is not None and manifest.commit != commit:
        raise RuntimeSnapshotError(
            f"runtime manifest commit {manifest.commit} differs from {commit}: {snapshot}"
        )
    if compute_digest(snapshot) != manifest.content_digest:
        raise RuntimeSnapshotError(f"runtime snapshot content digest mismatch: {snapshot}")
    writable = writable_entries(snapshot)
    if writable:
        raise RuntimeSnapshotError(
            f"runtime snapshot is no longer read-only ({len(writable)} writable entries, "
            f"first: {writable[0]}): {snapshot}"
        )
    return manifest
