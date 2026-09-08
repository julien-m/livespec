"""Coordinate confined goal archives among lock-cooperating writers."""

from __future__ import annotations

import fcntl
import os
from collections.abc import Mapping
from dataclasses import dataclass
from json import dumps
from typing import TypeAlias

from .goal_json import JsonValue

FileIdentity: TypeAlias = tuple[int, int]


# @spec FR-005: Pin temporary ownership until publication and cleanup finish.
@dataclass(frozen=True)
class OwnedTemporary:
    """Transfer an open temporary descriptor and its pinned inode to the caller."""

    descriptor: int
    identity: FileIdentity


def acquire_archive_lock(specs_fd: int) -> int:
    """Acquire the directory lock shared by cooperative archive writers.

    Args:
        specs_fd: Pinned ``.specs`` directory descriptor.

    Returns:
        The locked file descriptor, which the caller must release.

    Raises:
        OSError: If the duplicated descriptor cannot be locked.

    Side effects:
        Blocks until the duplicated directory descriptor owns the lock.
    """
    lock_fd = os.dup(specs_fd)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
    except BaseException:
        os.close(lock_fd)
        raise
    return lock_fd


def release_archive_lock(lock_fd: int) -> None:
    """Release and close a cooperative archive lock descriptor.

    Args:
        lock_fd: Descriptor returned by ``acquire_archive_lock``.

    Returns:
        None.

    Raises:
        OSError: If unlocking or closing fails.

    Side effects:
        Releases the cooperative lock and closes its descriptor.
    """
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
    finally:
        os.close(lock_fd)


def entry_identity(parent_fd: int, name: str, *, follow: bool) -> FileIdentity | None:
    """Return a descriptor-relative entry identity.

    Args:
        parent_fd: Pinned parent directory descriptor.
        name: Child entry name.
        follow: Whether to follow a symbolic link child.

    Returns:
        The device and inode pair, or None when stat fails.
    """
    try:
        entry = os.stat(name, dir_fd=parent_fd, follow_symlinks=follow)
    except OSError:
        return None
    return entry.st_dev, entry.st_ino


def same_inode_at(parent_fd: int, name: str, target_fd: int, *, follow: bool) -> bool:
    """Return whether a visible entry still names an opened descriptor inode.

    Args:
        parent_fd: Pinned parent directory descriptor.
        name: Child entry name.
        target_fd: Previously opened child descriptor.
        follow: Whether to follow a symbolic link child.

    Returns:
        True only when both identities are available and match.
    """
    visible = entry_identity(parent_fd, name, follow=follow)
    try:
        opened = os.fstat(target_fd)
    except OSError:
        return False
    return visible == (opened.st_dev, opened.st_ino)


def write_owned_temporary(
    runs_fd: int,
    temporary_name: str,
    artifact: Mapping[str, JsonValue],
) -> OwnedTemporary:
    """Create and fully sync one descriptor-relative temporary.

    Args:
        runs_fd: Pinned destination directory descriptor.
        temporary_name: Exclusive sibling temporary name.
        artifact: Closed JSON artifact payload.

    Raises:
        OSError: If exclusive creation, writing, or syncing fails.

    Returns:
        An open descriptor and its identity; the caller must close it once.

    Side effects:
        Removes the temporary only after this invocation created it.
    """
    file_fd = os.open(
        temporary_name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
        dir_fd=runs_fd,
    )
    owned_identity: FileIdentity | None = None
    try:
        opened = os.fstat(file_fd)
        owned_identity = opened.st_dev, opened.st_ino
        # Pin the inode beyond stream closure; otherwise Linux may reuse it for
        # an unlinked temporary's foreign replacement before publication.
        with os.fdopen(file_fd, "w", encoding="utf-8", closefd=False) as stream:
            stream.write(dumps(artifact, indent=2, ensure_ascii=False))
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        try:
            _remove_entry_if_owned(runs_fd, temporary_name, owned_identity)
        finally:
            os.close(file_fd)
        raise
    return OwnedTemporary(file_fd, owned_identity)


def entry_matches_identity(
    runs_fd: int,
    name: str,
    expected_identity: FileIdentity,
) -> bool:
    """Return whether a descriptor-relative entry currently matches an inode.

    Args:
        runs_fd: Pinned destination directory descriptor.
        name: Child entry name.
        expected_identity: Device and inode pair expected for the child.

    Returns:
        True only when the visible entry retains the expected identity.
    """
    try:
        visible = os.stat(name, dir_fd=runs_fd, follow_symlinks=False)
    except OSError:
        return False
    return (visible.st_dev, visible.st_ino) == expected_identity


def publish_owned_temporary(
    runs_fd: int,
    temporary_name: str,
    filename: str,
    expected_identity: FileIdentity,
) -> None:
    """Publish an owned temporary without replacing an existing final name.

    The exclusive link is the portable macOS/POSIX no-replace publication
    primitive. The caller supplies an unpredictable per-invocation temp name
    and holds the cooperative archive lock for the entire sequence.
    Non-cooperative pathname replacement between identity checks and syscalls
    is outside this API's documented coordination model.

    Args:
        runs_fd: Pinned destination directory descriptor.
        temporary_name: Invocation-unique temporary entry name.
        filename: Exclusive final artifact name.
        expected_identity: Device and inode pair owned by this invocation.

    Returns:
        None.

    Raises:
        OSError: If identity validation, exclusive linking, or cleanup fails.

    Side effects:
        Links the owned temporary to the final name and removes the temporary.
    """
    try:
        if not entry_matches_identity(runs_fd, temporary_name, expected_identity):
            raise OSError("temporary identity changed before publication")
        os.link(
            temporary_name,
            filename,
            src_dir_fd=runs_fd,
            dst_dir_fd=runs_fd,
            follow_symlinks=False,
        )
        if not entry_matches_identity(runs_fd, filename, expected_identity):
            raise OSError("final identity changed after publication")
        if not entry_matches_identity(runs_fd, temporary_name, expected_identity):
            raise OSError("temporary identity changed during publication")
        cleanup_error = _remove_entry_if_owned(runs_fd, temporary_name, expected_identity)
        if cleanup_error is not None:
            raise cleanup_error
    except BaseException:
        _remove_entry_if_owned(runs_fd, filename, expected_identity)
        _remove_entry_if_owned(runs_fd, temporary_name, expected_identity)
        raise


def remove_owned_residue(
    runs_fd: int,
    temporary_name: str,
    filename: str,
    *,
    expected_identity: FileIdentity | None,
    final_written: bool,
) -> OSError | None:
    """Best-effort remove matching residue for a cooperative invocation.

    Args:
        runs_fd: Pinned destination directory descriptor.
        temporary_name: Invocation-specific temporary name.
        filename: Final artifact name.
        expected_identity: Owned temporary inode, or None without proof.
        final_written: Whether this invocation completed publication.

    Returns:
        A cleanup error, or None when cleanup succeeded or was unnecessary.

    Side effects:
        Under the cooperative archive lock, unlinks residue whose visible
        identity matches the invocation-owned inode at the pre-unlink check.
        Non-cooperative replacement between that check and unlink is outside
        the coordination model.
    """
    residue = filename if final_written else temporary_name
    if expected_identity is None:
        return None
    return _remove_entry_if_owned(runs_fd, residue, expected_identity)


def _remove_entry_if_owned(
    runs_fd: int,
    name: str,
    expected_identity: FileIdentity | None,
) -> OSError | None:
    # Cooperative cleanup cannot rely on creation alone; it also checks the
    # visible identity. Path replacement between this check and unlink is an
    # explicitly unsupported non-cooperative mutation.
    if expected_identity is None or not entry_matches_identity(runs_fd, name, expected_identity):
        return None
    try:
        os.unlink(name, dir_fd=runs_fd)
    except FileNotFoundError:
        return None
    except OSError as exc:
        return exc
    return None


__all__ = [
    "FileIdentity",
    "OwnedTemporary",
    "acquire_archive_lock",
    "entry_identity",
    "entry_matches_identity",
    "publish_owned_temporary",
    "release_archive_lock",
    "remove_owned_residue",
    "same_inode_at",
    "write_owned_temporary",
]
