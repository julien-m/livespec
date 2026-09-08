"""Pin bootstrap archive directories across creation and atomic writes."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from errno import ELOOP, ENOTDIR
from pathlib import Path

from .goal_archive_file import OwnedTemporary
from .goal_archive_file import acquire_archive_lock as _acquire_archive_lock
from .goal_archive_file import entry_identity as _entry_identity
from .goal_archive_file import publish_owned_temporary as _publish_temporary
from .goal_archive_file import release_archive_lock as _release_archive_lock
from .goal_archive_file import remove_owned_residue as _remove_artifact_residue
from .goal_archive_file import same_inode_at as _same_inode_at
from .goal_archive_file import write_owned_temporary as _write_temporary
from .goal_json import JsonObject


class ConfinedArchiveError(Exception):
    """Report a descriptor or containment failure during archive I/O."""


@dataclass(frozen=True)
class _OpenedRunsDirectory:
    """Own pinned directory descriptors until archive cleanup completes."""

    root: Path
    runs_path: Path
    root_fd: int
    specs_fd: int
    runs_fd: int
    lock_fd: int
    follows_runs_symlink: bool
    runs_link_identity: tuple[int, int] | None


def resolve_confined_runs_directory(project_root: Path) -> Path:
    """Create or resolve a contained ``.specs/.runs`` through pinned descriptors.

    Args:
        project_root: Canonical readable and writable bootstrap root.

    Returns:
        The real contained runs directory.

    Raises:
        ConfinedArchiveError: If a component is missing, unsafe, or swapped.

    Side effects:
        May create only the missing ``.runs`` child of an existing ``.specs``.
    """
    opened = _open_runs_directory(project_root)
    try:
        return opened.runs_path
    finally:
        _close_runs_directory(opened)


def write_confined_json_artifact(
    project_root: Path,
    destination: Path,
    filename: str,
    artifact: JsonObject,
) -> Path:
    """Write JSON through a pinned descriptor and exclusive publication.

    Args:
        project_root: Canonical bootstrap root.
        destination: Previously validated runs directory.
        filename: Safe final artifact filename.
        artifact: Closed JSON artifact payload.

    Returns:
        The final artifact path.

    Raises:
        ConfinedArchiveError: If directory identity changes or I/O fails.

    Side effects:
        Creates, fsyncs, and publishes one temporary; cleans owned residue.
    """
    return _write_confined_artifact(project_root, destination, filename, artifact)


def _write_confined_artifact(
    project_root: Path,
    destination: Path,
    filename: str,
    artifact: JsonObject,
) -> Path:
    temporary_name = _temporary_name(filename)
    opened: _OpenedRunsDirectory | None = None
    temporary: OwnedTemporary | None = None
    final_written = False
    try:
        opened = _open_runs_directory(project_root)
        if opened.runs_path != destination.resolve(strict=True):
            raise ConfinedArchiveError("run destination changed after validation")
        temporary = _write_temporary(opened.runs_fd, temporary_name, artifact)
        # Identity checks bracket publication because reordering would permit a
        # visible component swap to survive as an apparently valid archive.
        _require_opened_identity(opened)
        _publish_temporary(opened.runs_fd, temporary_name, filename, temporary.identity)
        final_written = True
        _require_opened_identity(opened)
        return opened.runs_path / filename
    except (ConfinedArchiveError, OSError) as exc:
        cleanup_error = _remove_artifact_residue(
            opened.runs_fd if opened is not None else -1,
            temporary_name,
            filename,
            expected_identity=temporary.identity if temporary is not None else None,
            final_written=final_written,
        )
        detail = f"; artifact cleanup failed: {cleanup_error}" if cleanup_error else ""
        raise ConfinedArchiveError(f"cannot write confined run artifact: {exc}{detail}") from exc
    finally:
        # @spec FR-005: Retain ownership through all publication and cleanup paths.
        try:
            if temporary is not None:
                os.close(temporary.descriptor)
        finally:
            if opened is not None:
                _close_runs_directory(opened)


def _temporary_name(filename: str) -> str:
    return f".{filename}.{secrets.token_hex(16)}.tmp"


def _open_runs_directory(project_root: Path) -> _OpenedRunsDirectory:
    root = _resolve_directory(project_root, "project_root")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    root_fd = os.open(root, flags)
    specs_fd = -1
    runs_fd = -1
    lock_fd = -1
    try:
        specs_fd = os.open(".specs", flags, dir_fd=root_fd)
        # Every cooperative writer holds the stable .specs lock from child
        # creation through publication and cleanup; partial locking would
        # preserve the same name races the descriptor checks are closing.
        lock_fd = _acquire_archive_lock(specs_fd)
        runs_fd, runs_path, follows_symlink, link_identity = _open_runs_child(
            root, root_fd, specs_fd, flags
        )
        opened = _OpenedRunsDirectory(
            root,
            runs_path,
            root_fd,
            specs_fd,
            runs_fd,
            lock_fd,
            follows_symlink,
            link_identity,
        )
        _require_opened_identity(opened)
        return opened
    except (ConfinedArchiveError, OSError) as exc:
        _close_failed_open(root_fd, specs_fd, runs_fd, lock_fd)
        if isinstance(exc, ConfinedArchiveError):
            raise
        raise ConfinedArchiveError(f"cannot open confined .specs/.runs: {exc}") from exc


def _open_runs_child(
    root: Path, root_fd: int, specs_fd: int, flags: int
) -> tuple[int, Path, bool, tuple[int, int] | None]:
    try:
        runs_fd = os.open(".runs", flags, dir_fd=specs_fd)
        return runs_fd, root / ".specs" / ".runs", False, None
    except FileNotFoundError:
        # Creation is relative to the pinned .specs inode so swapping the
        # visible path cannot redirect mkdir to an attacker-controlled target.
        os.mkdir(".runs", dir_fd=specs_fd)
        created_identity = _entry_identity(specs_fd, ".runs", follow=False)
        if created_identity is None:
            raise ConfinedArchiveError("cannot capture created .specs/.runs identity") from None
        try:
            runs_fd = os.open(".runs", flags, dir_fd=specs_fd)
        except OSError:
            raise
        if _fd_identity(runs_fd) != created_identity:
            os.close(runs_fd)
            raise ConfinedArchiveError("created .specs/.runs changed before reopen") from None
        return runs_fd, root / ".specs" / ".runs", False, None
    except OSError as exc:
        if exc.errno not in {ELOOP, ENOTDIR}:
            raise
    link_identity = _entry_identity(specs_fd, ".runs", follow=False)
    if link_identity is None:
        raise ConfinedArchiveError("cannot pin .specs/.runs symlink identity")
    runs_path = _resolve_directory(root / ".specs" / ".runs", ".specs/.runs")
    if not runs_path.is_relative_to(root):
        raise ConfinedArchiveError(".specs/.runs resolves outside canonical project_root")
    return (
        _open_confined_directory(root_fd, root, runs_path),
        runs_path,
        True,
        link_identity,
    )


def _require_opened_identity(opened: _OpenedRunsDirectory) -> None:
    current_runs_path = _resolve_directory(opened.root / ".specs" / ".runs", ".specs/.runs")
    path_matches = current_runs_path.is_relative_to(opened.root) and (
        current_runs_path == opened.runs_path
    )
    specs_matches = _same_inode_at(opened.root_fd, ".specs", opened.specs_fd, follow=False)
    runs_matches = _same_inode_at(
        opened.specs_fd,
        ".runs",
        opened.runs_fd,
        follow=opened.follows_runs_symlink,
    )
    link_matches = opened.runs_link_identity is None or (
        _entry_identity(opened.specs_fd, ".runs", follow=False) == opened.runs_link_identity
    )
    if not path_matches or not specs_matches or not runs_matches or not link_matches:
        raise ConfinedArchiveError("archive directory changed during confined write")


def _open_confined_directory(root_fd: int, project_root: Path, destination: Path) -> int:
    try:
        relative = destination.relative_to(project_root)
    except ValueError as exc:
        raise ConfinedArchiveError("run destination escapes canonical project_root") from exc
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    # Traverse from the already pinned root inode: reopening project_root here
    # would let a concurrent pathname replacement redirect an absolute symlink.
    current_fd = os.dup(root_fd)
    try:
        for part in relative.parts:
            next_fd = os.open(part, flags, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except OSError:
        os.close(current_fd)
        raise


def _resolve_directory(path: Path, label: str) -> Path:
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ConfinedArchiveError(f"{label} is missing, broken, or unreadable: {exc}") from exc
    if not resolved.is_dir() or not os.access(resolved, os.R_OK | os.W_OK):
        raise ConfinedArchiveError(f"{label} must be a readable and writable directory")
    return resolved


def _close_failed_open(
    root_fd: int,
    specs_fd: int,
    runs_fd: int,
    lock_fd: int,
) -> None:
    if runs_fd >= 0:
        os.close(runs_fd)
    if lock_fd >= 0:
        _release_archive_lock(lock_fd)
    if specs_fd >= 0:
        os.close(specs_fd)
    os.close(root_fd)


def _close_runs_directory(opened: _OpenedRunsDirectory) -> None:
    os.close(opened.runs_fd)
    _release_archive_lock(opened.lock_fd)
    os.close(opened.specs_fd)
    os.close(opened.root_fd)


def _fd_identity(fd: int) -> tuple[int, int] | None:
    try:
        opened = os.fstat(fd)
    except OSError:
        return None
    return opened.st_dev, opened.st_ino


__all__ = [
    "ConfinedArchiveError",
    "resolve_confined_runs_directory",
    "write_confined_json_artifact",
]
