"""Descriptor-owned capture storage helpers, shared with timeout publication."""

from __future__ import annotations

import fcntl
import os
import time
import uuid
from contextlib import suppress
from pathlib import Path

from .execution_deadline import BudgetExpired, current_deadline, disarm_deadline_alarm

__all__ = ["_open_storage", "_run_directory", "_write_new", "acquire_capture_lock"]


def _write_new(directory_fd: int, name: str, data: bytes) -> None:
    descriptor = os.open(
        name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd
    )
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
        os.fchmod(stream.fileno(), 0o400)


def _open_storage(root: Path) -> tuple[int, int]:
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    specs_fd = -1
    try:
        # Existing directories must still pass the descriptor no-follow checks.
        with suppress(FileExistsError):
            os.mkdir(".specs", mode=0o700, dir_fd=root_fd)
        specs_fd = os.open(".specs", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
        with suppress(FileExistsError):
            os.mkdir(".execution", mode=0o700, dir_fd=specs_fd)
        storage_fd = os.open(
            ".execution", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=specs_fd
        )
        return specs_fd, storage_fd
    except BaseException:
        if specs_fd >= 0:
            os.close(specs_fd)
        raise
    finally:
        os.close(root_fd)


def _run_directory(root: Path) -> tuple[Path, tuple[int, int]]:
    specs_fd, storage_fd = _open_storage(root)
    try:
        nonce = uuid.uuid4().hex
        os.mkdir(nonce, mode=0o700, dir_fd=storage_fd)
        created = os.stat(nonce, dir_fd=storage_fd, follow_symlinks=False)
        return root / ".specs/.execution" / nonce, (created.st_dev, created.st_ino)
    finally:
        os.close(storage_fd)
        os.close(specs_fd)


def acquire_capture_lock(specs_fd: int) -> int:
    """Serialize publishers within the command deadline (one second without a scope)."""
    scope = current_deadline()
    deadline = scope.end if scope else time.monotonic() + 1.0
    descriptor = os.dup(specs_fd)
    try:
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return descriptor
            except BlockingIOError:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    if scope:
                        scope.timed_out = True
                        disarm_deadline_alarm()
                    raise BudgetExpired(
                        "command budget exhausted waiting for capture publication"
                    ) from None
                time.sleep(min(0.01, remaining))
    except BaseException:
        os.close(descriptor)
        raise
