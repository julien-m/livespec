"""Immutable runtime snapshot installation: validate, stage, seal and publish atomically."""

from __future__ import annotations

import os
import posixpath
import re
import shutil
import stat
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from .errors import LiveSpecRuntimeError, RuntimeSourceError
from .git_tree import (
    TreeEntry,
    dirty_paths,
    list_snapshot_entries,
    read_blobs,
    require_git_root,
    resolve_commit,
)
from .home import RuntimeHome, executing_root, is_livespec_root, is_snapshot_root
from .manifest import compute_digest, manifest_bytes, read_manifest, verify_snapshot
from .models import MANIFEST_NAME, InstallResult, RuntimeManifest
from .shim import check_shim_paths, write_shim

STAGING_PREFIX = ".staging-"
# Leftover staging directory ".staging-<runtime id>-<pid>-<random>" (pid of its writer).
_STAGING_RE = re.compile(r"\A\.staging-[0-9]+-[0-9a-f]{12}-(?P<pid>[0-9]+)-")
# Dirty-path listing is capped in error messages to keep them single-screen.
_MAX_REPORTED_DIRTY = 20
_WRITE_BITS = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH


@dataclass(frozen=True)
class InstallRequest:
    """Inputs of ``livespec runtime install`` after CLI parsing."""

    home: RuntimeHome
    python: str
    clock: Callable[[], datetime]
    source: Path | None = None
    ref: str | None = None
    activate: bool = True


def make_read_only(root: Path) -> None:
    """Remove every write permission bit below and on ``root`` (symlinks untouched)."""
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        for name in [*filenames, *dirnames]:
            path = Path(dirpath) / name
            mode = path.lstat().st_mode
            if not stat.S_ISLNK(mode):
                path.chmod(stat.S_IMODE(mode) & ~_WRITE_BITS)
    root.chmod(stat.S_IMODE(root.stat().st_mode) & ~_WRITE_BITS)


def restore_write_bits(root: Path) -> None:
    """Give the owner write permission again on ``root`` and everything below it."""
    root.chmod(stat.S_IMODE(root.stat().st_mode) | stat.S_IWUSR)
    for dirpath, dirnames, filenames in os.walk(root):
        for name in [*dirnames, *filenames]:
            path = Path(dirpath) / name
            mode = path.lstat().st_mode
            if not stat.S_ISLNK(mode):
                path.chmod(stat.S_IMODE(mode) | stat.S_IWUSR)


def remove_tree(root: Path, container: Path) -> None:
    """Delete a possibly read-only directory tree after restoring write bits.

    Args:
        root: Real directory to delete (never a symlink).
        container: Directory that ``root`` must resolve to a direct child of.

    Raises:
        LiveSpecRuntimeError: If ``root`` is a symlink or escapes ``container``.
    """
    if root.is_symlink():
        raise LiveSpecRuntimeError(f"refusing to delete through a symlink: {root}")
    if not root.is_dir():
        raise LiveSpecRuntimeError(f"refusing to delete a non-directory: {root}")
    if root.resolve().parent != container.resolve():
        raise LiveSpecRuntimeError(f"refusing to delete outside {container}: {root}")
    restore_write_bits(root)
    shutil.rmtree(root)


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # The process exists but belongs to another user: treat it as alive.
        return True
    return True


def remove_stale_staging(home: RuntimeHome) -> list[Path]:
    """Remove staging directories left by dead install processes.

    Args:
        home: Runtime home.

    Returns:
        Removed staging directories.
    """
    removed: list[Path] = []
    for child in sorted(home.versions.iterdir()):
        match = _STAGING_RE.match(child.name)
        if match is None:
            continue
        # A staging-named symlink is never followed: only the link itself is removed,
        # so no chmod or deletion can reach outside the runtime home.
        if child.is_symlink():
            child.unlink()
            removed.append(child)
            continue
        # Live writers keep their staging directory; only dead pids are reclaimed.
        if not child.is_dir() or _pid_alive(int(match.group("pid"))):
            continue
        remove_tree(child, home.versions)
        removed.append(child)
    return removed


def _resolve_source(option: Path | None) -> Path:
    candidate = option.expanduser().resolve() if option is not None else executing_root()
    if option is None and is_snapshot_root(candidate):
        # A snapshot CLI installs from the checkout recorded in its own manifest.
        candidate = Path(read_manifest(candidate).source)
    if not is_livespec_root(candidate):
        raise RuntimeSourceError(f"source is not a LiveSpec root: {candidate}")
    return require_git_root(candidate)


def _committed_version(entries: list[TreeEntry], blobs: dict[str, bytes], commit: str) -> int:
    entry = next((item for item in entries if item.path == "VERSION"), None)
    raw = blobs[entry.oid].decode("utf-8", "replace").strip() if entry is not None else ""
    if entry is None or entry.is_symlink or not raw.isdigit():
        raise RuntimeSourceError(f"committed VERSION missing or not an integer in {commit}")
    return int(raw)


def _check_symlinks(entries: list[TreeEntry], blobs: dict[str, bytes], commit: str) -> None:
    """Refuse absolute or snapshot-escaping symlinks (D-01)."""
    for entry in entries:
        if not entry.is_symlink:
            continue
        target = blobs[entry.oid].decode("utf-8", "surrogateescape")
        joined = posixpath.normpath(posixpath.join(posixpath.dirname(entry.path), target))
        if posixpath.isabs(target) or joined == ".." or joined.startswith("../"):
            raise RuntimeSourceError(f"symlink escapes the snapshot in {commit}: {entry.path}")


def _write_entries(staging: Path, entries: list[TreeEntry], blobs: dict[str, bytes]) -> None:
    for entry in entries:
        target = staging / entry.path
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = blobs[entry.oid]
        if entry.is_symlink:
            os.symlink(payload.decode("utf-8", "surrogateescape"), target)
            continue
        target.write_bytes(payload)
        target.chmod(0o755 if entry.is_executable else 0o644)


def _seal_and_publish(home: RuntimeHome, staging: Path, base: RuntimeManifest) -> str:
    """Write the manifest, seal read-only, then rename; return created or reused."""
    manifest = replace(base, content_digest=compute_digest(staging))
    (staging / MANIFEST_NAME).write_bytes(manifest_bytes(manifest))
    # Seal before rename (D-15): the final path never exposes a writable snapshot.
    make_read_only(staging)
    try:
        os.rename(staging, home.snapshot(base.runtime_id))
    except OSError:
        if not home.snapshot(base.runtime_id).is_dir():
            raise
        # A concurrent install won the rename; reuse its snapshot once verified.
        remove_tree(staging, home.versions)
        verify_snapshot(home, base.runtime_id, base.commit)
        return "reused"
    return "created"


def _build_snapshot(
    home: RuntimeHome, base: RuntimeManifest, entries: list[TreeEntry], blobs: dict[str, bytes]
) -> str:
    home.versions.mkdir(parents=True, exist_ok=True)
    remove_stale_staging(home)
    prefix = f"{STAGING_PREFIX}{base.runtime_id}-{os.getpid()}-"
    staging = Path(tempfile.mkdtemp(prefix=prefix, dir=home.versions))
    try:
        _write_entries(staging, entries, blobs)
        return _seal_and_publish(home, staging, base)
    except BaseException:
        # Interrupted or failed install: never leave a partial tree behind, then re-raise.
        if staging.exists():
            remove_tree(staging, home.versions)
        raise


def activate(home: RuntimeHome, runtime_id: str) -> None:
    """Point ``<home>/current`` at a snapshot with one atomic replacement.

    Args:
        home: Runtime home.
        runtime_id: Installed runtime id.

    Raises:
        LiveSpecRuntimeError: If ``current`` exists and is not a symlink.
    """
    if home.current.exists() and not home.current.is_symlink():
        raise LiveSpecRuntimeError(f"{home.current} exists and is not a symlink (refused)")
    temporary = home.root / f".current.{os.getpid()}.tmp"
    if temporary.is_symlink():
        temporary.unlink()
    # Relative target keeps the home relocatable; replace() swaps the link atomically.
    os.symlink(Path("versions") / runtime_id, temporary)
    os.replace(temporary, home.current)


def _validated_tree(source: Path, ref: str | None) -> tuple[str, list[TreeEntry], dict[str, bytes]]:
    commit = resolve_commit(source, ref or "HEAD")
    if ref is None:
        dirty = dirty_paths(source)
        if dirty:
            shown = ", ".join(dirty[:_MAX_REPORTED_DIRTY])
            raise RuntimeSourceError(
                f"source working tree is dirty ({len(dirty)} paths: {shown}); "
                "commit the changes or pass --ref <commit>"
            )
    entries = list_snapshot_entries(source, commit)
    blobs = read_blobs(source, [entry.oid for entry in entries])
    _check_symlinks(entries, blobs, commit)
    return commit, entries, blobs


# @spec FR-001: Committed snapshot build, FR-003: Reuse and activation
#   — .specs/features/083-pinned-runtime-isolation/spec.md#fr-001
def install_runtime(request: InstallRequest) -> InstallResult:
    """Install (or reuse) the snapshot of a committed LiveSpec tree.

    Every input is validated before the first write under the home. Side effects:
    creates ``<home>/versions/<id>``, rewrites ``<home>/bin/livespec`` and, unless
    ``activate`` is false, repoints ``<home>/current``.

    Args:
        request: Parsed install inputs.

    Returns:
        The install outcome.

    Raises:
        RuntimeSourceError: For an invalid source, ref, dirty tree or committed tree.
        RuntimeSnapshotError: If an existing snapshot for the runtime id is corrupted.
        LiveSpecRuntimeError: For refused interpreter, home or ``current`` paths.
    """
    home = request.home
    check_shim_paths(home, request.python)
    source = _resolve_source(request.source)
    commit, entries, blobs = _validated_tree(source, request.ref)
    version = _committed_version(entries, blobs, commit)
    runtime_id = f"{version}-{commit[:12]}"
    snapshot = home.snapshot(runtime_id)
    if snapshot.exists() or snapshot.is_symlink():
        verify_snapshot(home, runtime_id, commit)
        status = "reused"
    else:
        created_at = request.clock().astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        base = RuntimeManifest(runtime_id, version, commit, str(source), created_at, "")
        status = _build_snapshot(home, base, entries, blobs)
    shim = write_shim(home, request.python)
    if request.activate:
        activate(home, runtime_id)
    return InstallResult(runtime_id, snapshot, status, request.activate, shim, home.current)
