"""Prove owned temporary descriptor lifetime across the archive failure matrix."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from errno import EBADF
from pathlib import Path
from typing import IO, Literal

import pytest

from validator import goal_archive_fd, goal_archive_file
from validator.goal_archive_fd import ConfinedArchiveError
from validator.goal_archive_file import FileIdentity

FailureStage = Literal["write", "fsync", "pre-publication", "link", "post-publication", "cleanup"]


@dataclass
class DescriptorTrace:
    """Observe actual temporary descriptors without replacing filesystem behavior."""

    opened: list[int] = field(default_factory=list)
    closed: list[int] = field(default_factory=list)
    live_at: list[str] = field(default_factory=list)

    def require_live(self, phase: str) -> None:
        """Assert the observed temporary descriptor remains open at this phase."""
        assert len(self.opened) == 1
        os.fstat(self.opened[0])
        self.live_at.append(phase)


@pytest.fixture
def descriptor_trace(monkeypatch: pytest.MonkeyPatch) -> DescriptorTrace:
    """Record real descriptor opens, closes and publication/cleanup observations."""
    trace = DescriptorTrace()
    original_open, original_close = os.open, os.close

    def observe_open(
        path: str | os.PathLike[str], flags: int, mode: int = 0o777, *, dir_fd: int | None = None
    ) -> int:
        """Delegate creation and record only the invocation temporary descriptor."""
        descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
        if os.fspath(path).endswith(".tmp"):
            trace.opened.append(descriptor)
        return descriptor

    def observe_close(descriptor: int) -> None:
        """Count closes of the owned temporary while preserving real close behavior."""
        if descriptor in trace.opened:
            trace.closed.append(descriptor)
        original_close(descriptor)

    monkeypatch.setattr(os, "open", observe_open)
    monkeypatch.setattr(os, "close", observe_close)
    _observe_owned_operations(monkeypatch, trace)
    return trace


def _observe_owned_operations(monkeypatch: pytest.MonkeyPatch, trace: DescriptorTrace) -> None:
    original_publish = goal_archive_fd._publish_temporary
    original_remove = goal_archive_file._remove_entry_if_owned

    def observe_publish(
        runs_fd: int, temporary_name: str, filename: str, expected_identity: FileIdentity
    ) -> None:
        """Require a live descriptor before invoking real publication."""
        trace.require_live("publication")
        original_publish(runs_fd, temporary_name, filename, expected_identity)

    def observe_remove(
        runs_fd: int, name: str, expected_identity: FileIdentity | None
    ) -> OSError | None:
        """Require pinned ownership during each actual cleanup attempt."""
        if expected_identity is not None:
            trace.require_live("cleanup")
        return original_remove(runs_fd, name, expected_identity)

    monkeypatch.setattr(goal_archive_fd, "_publish_temporary", observe_publish)
    monkeypatch.setattr(goal_archive_file, "_remove_entry_if_owned", observe_remove)


def _closed_descriptor_errno(trace: DescriptorTrace) -> int | None:
    assert len(trace.opened) == 1
    with pytest.raises(OSError) as closed:
        os.fstat(trace.opened[0])
    return closed.value.errno


# @spec AC-006: Publication and cleanup retain the owned inode until one final close.
def test_temporary_descriptor_closes_once_after_success(
    tmp_path: Path, descriptor_trace: DescriptorTrace
) -> None:
    runs = tmp_path / ".specs" / ".runs"
    runs.mkdir(parents=True)

    published = goal_archive_fd.write_confined_json_artifact(tmp_path, runs, "run.json", {})

    assert published.read_text(encoding="utf-8") == "{}"
    assert descriptor_trace.live_at == ["publication", "cleanup"]
    assert descriptor_trace.closed == descriptor_trace.opened
    assert _closed_descriptor_errno(descriptor_trace) == EBADF
    assert not list(runs.glob("*.tmp"))


# @spec AC-006: Every write/publication/cleanup failure closes the owned descriptor.
@pytest.mark.parametrize(
    "stage", ["write", "fsync", "pre-publication", "link", "post-publication", "cleanup"]
)
def test_temporary_descriptor_closes_once_after_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    descriptor_trace: DescriptorTrace,
    stage: FailureStage,
) -> None:
    """Verify every injected failure cleans under ownership and closes once."""
    runs = tmp_path / ".specs" / ".runs"
    runs.mkdir(parents=True)
    _inject_failure(monkeypatch, stage)

    with pytest.raises(ConfinedArchiveError, match=f"injected {stage}") as failure:
        goal_archive_fd.write_confined_json_artifact(tmp_path, runs, "run.json", {})

    assert "cleanup" in descriptor_trace.live_at
    assert descriptor_trace.closed == descriptor_trace.opened
    assert _closed_descriptor_errno(descriptor_trace) == EBADF
    assert not (runs / "run.json").exists()
    if stage == "cleanup":
        assert "artifact cleanup failed: injected cleanup" in str(failure.value)
        assert len(list(runs.glob("*.tmp"))) == 1
    else:
        assert not list(runs.glob("*.tmp"))


def _inject_failure(monkeypatch: pytest.MonkeyPatch, stage: FailureStage) -> None:
    if stage == "write":
        _fail_stream_write(monkeypatch)
    elif stage in {"pre-publication", "post-publication"}:
        _fail_identity_check(monkeypatch, stage)
    elif stage == "cleanup":
        _fail_temporary_unlink(monkeypatch)
    else:

        def fail_syscall(*args: object, **kwargs: object) -> None:
            """Raise the selected filesystem failure at its real call boundary."""
            raise PermissionError(f"injected {stage}")

        monkeypatch.setattr(os, stage, fail_syscall)


def _fail_stream_write(monkeypatch: pytest.MonkeyPatch) -> None:
    original_fdopen = os.fdopen

    def fail_write(text: str) -> int:
        """Inject failure into the actual text stream write operation."""
        raise PermissionError("injected write")

    def open_failing_stream(descriptor: int, mode: str, *, encoding: str, closefd: bool) -> IO[str]:
        """Wrap a real descriptor stream with only its write operation failing."""
        stream = original_fdopen(descriptor, mode, encoding=encoding, closefd=closefd)
        monkeypatch.setattr(stream, "write", fail_write)
        return stream

    monkeypatch.setattr(os, "fdopen", open_failing_stream)


def _fail_identity_check(
    monkeypatch: pytest.MonkeyPatch, stage: Literal["pre-publication", "post-publication"]
) -> None:
    original_require = goal_archive_fd._require_opened_identity
    calls = 0

    def require(opened: goal_archive_fd._OpenedRunsDirectory) -> None:
        """Inject a directory identity failure before or after actual publication."""
        nonlocal calls
        calls += 1
        original_require(opened)
        if calls == (2 if stage == "pre-publication" else 3):
            raise ConfinedArchiveError(f"injected {stage}")

    monkeypatch.setattr(goal_archive_fd, "_require_opened_identity", require)


def _fail_temporary_unlink(monkeypatch: pytest.MonkeyPatch) -> None:
    original_unlink = os.unlink

    def unlink(name: str, *, dir_fd: int | None = None) -> None:
        """Fail temporary cleanup while preserving final artifact removal."""
        if name.endswith(".tmp"):
            raise PermissionError("injected cleanup")
        original_unlink(name, dir_fd=dir_fd)

    monkeypatch.setattr(os, "unlink", unlink)
