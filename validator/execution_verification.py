"""Commit captures only after their API or CLI boundary finishes inside the original deadline."""

from __future__ import annotations

import json
import os
from collections.abc import Generator
from contextlib import contextmanager, suppress
from contextvars import ContextVar
from pathlib import Path

from . import execution_capture_storage as storage
from .execution_deadline import BudgetExpired, current_deadline, disarm_deadline_alarm
from .execution_scope import read_regular

_ACTIVE: ContextVar[str | None] = ContextVar("provisional_capture_verification", default=None)


@contextmanager
def provisional_verification(receipt: Path, root: Path) -> Generator[None, None, None]:
    """Allow only this live CLI check to inspect its provisional, hash-bound capture."""
    token = _ACTIVE.set(json.loads(read_regular(receipt, root))["capture_sha256"])
    try:
        yield
    finally:
        _ACTIVE.reset(token)


def require_completion(directory: Path, root: Path, expected: str) -> None:
    """Public consumption rejects absent, malformed or foreign completion evidence."""
    if _ACTIVE.get() == expected:
        return
    marker = json.loads(read_regular(directory / "verification-accepted.json", root))
    if not isinstance(marker, dict) or marker.get("capture_sha256") != expected:
        raise ValueError("Missing or foreign final verification completion")
    budget = marker.get("budget")
    if not isinstance(budget, dict) or budget.get("timed_out") is not False:
        raise ValueError("Invalid final verification completion budget")


def complete_verification(receipt: Path, root: Path) -> None:
    """Append fresh completion; any write failure leaves the capture nonqualifying."""
    scope = current_deadline()
    if scope is None or scope.timed_out or scope.remaining() <= 0:
        raise BudgetExpired("Final verification exceeded the original command deadline")
    reference = json.loads(read_regular(receipt, root))
    capture = json.loads(read_regular(receipt.parent / "capture.json", root))
    specs_fd, storage_fd = storage._open_storage(root)
    directory_fd = -1
    try:
        directory_fd = os.open(
            reference["invocation"], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=storage_fd
        )
        actual = os.fstat(directory_fd)
        if list(capture["directory_identity"]) != [actual.st_dev, actual.st_ino]:
            raise ValueError("Runner directory replaced before final verification")
        payload = json.dumps(
            {"capture_sha256": reference["capture_sha256"], "budget": scope.evidence()}
        ).encode()
        try:
            storage._write_new(directory_fd, "verification-complete.json", payload)
            if scope.timed_out or scope.remaining() <= 0:
                raise BudgetExpired("Final verification publication exceeded the original deadline")
            os.link(
                "verification-complete.json",
                "verification-accepted.json",
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
                follow_symlinks=False,
            )
            disarm_deadline_alarm()
            if scope.timed_out or scope.remaining() <= 0:
                raise BudgetExpired("Final completion exceeded the original command deadline")
        except FileExistsError:
            raise
        except BaseException:
            disarm_deadline_alarm()
            for name in ("verification-accepted.json", "verification-complete.json"):
                with suppress(FileNotFoundError):
                    os.unlink(name, dir_fd=directory_fd)
            raise
    finally:
        if directory_fd >= 0:
            os.close(directory_fd)
        os.close(storage_fd)
        os.close(specs_fd)
