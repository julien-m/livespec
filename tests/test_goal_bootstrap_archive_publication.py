"""Verify exclusive publication for writers using the cooperative archive lock.

Non-cooperative pathname replacement between identity checks and filesystem
syscalls is excluded by the Feature 076 contract.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

from validator import goal_archive_fd
from validator.goal_archive_fd import ConfinedArchiveError
from validator.goal_archive_file import FileIdentity
from validator.goal_json import JsonValue


def test_cooperative_writer_preserves_preexisting_final_artifact(tmp_path: Path) -> None:
    project = tmp_path / "project"
    runs = project / ".specs" / ".runs"
    runs.mkdir(parents=True)
    final = runs / "run.json"
    final.write_text('{"foreign": true}', encoding="utf-8")

    with pytest.raises(ConfinedArchiveError):
        goal_archive_fd.write_confined_json_artifact(project, runs, "run.json", {})

    assert final.read_text(encoding="utf-8") == '{"foreign": true}'
    assert not list(runs.glob("*.tmp"))


def test_created_runs_swap_before_capture_preserves_both_inodes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    specs = project / ".specs"
    specs.mkdir(parents=True)
    moved_created = specs / "created-moved"
    original_identity = goal_archive_fd._entry_identity
    capture_swapped = False

    def swap_before_capture(parent_fd: int, name: str, *, follow: bool) -> tuple[int, int] | None:
        nonlocal capture_swapped
        if name == ".runs" and not follow and not capture_swapped:
            capture_swapped = True
            (specs / ".runs").rename(moved_created)
            (specs / ".runs").mkdir()
        return original_identity(parent_fd, name, follow=follow)

    def fail_write(*args: object, **kwargs: object) -> None:
        raise PermissionError("deterministic write failure")

    monkeypatch.setattr(goal_archive_fd, "_entry_identity", swap_before_capture)
    monkeypatch.setattr(goal_archive_fd, "_write_temporary", fail_write)
    with pytest.raises(ConfinedArchiveError):
        goal_archive_fd.write_confined_json_artifact(project, specs / ".runs", "run.json", {})

    assert moved_created.is_dir()
    assert (specs / ".runs").is_dir()


def test_archive_lock_wraps_temporary_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    runs = project / ".specs" / ".runs"
    runs.mkdir(parents=True)
    events: list[str] = []
    lock_active = False
    original_publish = goal_archive_fd._publish_temporary

    def acquire(specs_fd: int) -> int:
        nonlocal lock_active
        lock_active = True
        events.append("acquire")
        return specs_fd

    def publish(
        runs_fd: int,
        temporary_name: str,
        filename: str,
        expected_identity: FileIdentity,
    ) -> None:
        assert lock_active
        events.append("publish")
        original_publish(runs_fd, temporary_name, filename, expected_identity)

    def release(lock_fd: int) -> None:
        nonlocal lock_active
        lock_active = False
        events.append("release")

    monkeypatch.setattr(goal_archive_fd, "_acquire_archive_lock", acquire, raising=False)
    monkeypatch.setattr(goal_archive_fd, "_publish_temporary", publish)
    monkeypatch.setattr(goal_archive_fd, "_release_archive_lock", release, raising=False)

    goal_archive_fd.write_confined_json_artifact(project, runs, "run.json", {})

    assert events == ["acquire", "publish", "release"]


def test_unchanged_runs_link_cannot_follow_target_moved_outside(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    specs = project / ".specs"
    contained = specs / "contained"
    contained.mkdir(parents=True)
    (specs / ".runs").symlink_to(contained, target_is_directory=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    moved = outside / "moved"
    original_write = goal_archive_fd._write_temporary

    def move_target_after_write(
        runs_fd: int, temporary_name: str, artifact: Mapping[str, JsonValue]
    ) -> FileIdentity:
        identity = original_write(runs_fd, temporary_name, artifact)
        contained.rename(moved)
        contained.symlink_to(moved, target_is_directory=True)
        return identity

    monkeypatch.setattr(goal_archive_fd, "_write_temporary", move_target_after_write)

    with pytest.raises(ConfinedArchiveError):
        goal_archive_fd.write_confined_json_artifact(project, specs / ".runs", "run.json", {})

    assert not list(outside.rglob("*.json"))
    assert not list(outside.rglob("*.tmp"))
