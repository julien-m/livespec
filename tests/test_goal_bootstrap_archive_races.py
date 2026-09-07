"""Deterministic archive race regressions for Feature 076."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

import pytest

from tests.goal_bootstrap_support import archive_valid_pair
from validator import goal_archive_fd
from validator import run_artifacts as run_artifacts_module
from validator.goal_archive_fd import ConfinedArchiveError
from validator.goal_archive_file import FileIdentity
from validator.goal_json import JsonObject, JsonValue
from validator.goal_run_builder import RunArtifactBuildInput
from validator.outcome import Outcome
from validator.run_artifacts import archive_goal_run


def test_archive_defers_runs_creation_to_atomic_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    (project / ".specs").mkdir(parents=True)
    contract, state = archive_valid_pair(project)
    original_build = run_artifacts_module.build_run_artifact
    creation_was_deferred = False

    def observe_build(inputs: RunArtifactBuildInput) -> tuple[JsonObject, Outcome]:
        nonlocal creation_was_deferred
        creation_was_deferred = not (project / ".specs" / ".runs").exists()
        return original_build(inputs)

    monkeypatch.setattr(run_artifacts_module, "build_run_artifact", observe_build)
    result = archive_goal_run(contract, state, project_root=project, exit_code=0)

    assert creation_was_deferred
    assert result.outcome == "success"


def test_real_specs_swap_during_write_is_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    specs = project / ".specs"
    specs.mkdir(parents=True)
    contract, state = archive_valid_pair(project)
    original_write = goal_archive_fd._write_temporary

    def write_then_swap(
        runs_fd: int, temporary_name: str, artifact: Mapping[str, JsonValue]
    ) -> FileIdentity:
        identity = original_write(runs_fd, temporary_name, artifact)
        specs.rename(tmp_path / "old-specs")
        (specs / ".runs").mkdir(parents=True)
        return identity

    monkeypatch.setattr(goal_archive_fd, "_write_temporary", write_then_swap)
    result = archive_goal_run(contract, state, project_root=project, exit_code=0)

    assert result.outcome == "blocked"
    assert not list(tmp_path.rglob("*.json"))
    assert not list(tmp_path.rglob("*.tmp"))


def test_contained_runs_symlink_swap_during_write_is_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    specs = project / ".specs"
    contained = specs / "contained"
    contained.mkdir(parents=True)
    link = specs / ".runs"
    link.symlink_to(contained, target_is_directory=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    contract, state = archive_valid_pair(project)
    original_write = goal_archive_fd._write_temporary

    def write_then_swap(
        runs_fd: int, temporary_name: str, artifact: Mapping[str, JsonValue]
    ) -> FileIdentity:
        identity = original_write(runs_fd, temporary_name, artifact)
        contained.rename(outside / "moved")
        link.unlink()
        link.symlink_to(outside / "moved", target_is_directory=True)
        return identity

    monkeypatch.setattr(goal_archive_fd, "_write_temporary", write_then_swap)
    result = archive_goal_run(contract, state, project_root=project, exit_code=0)

    assert result.outcome == "blocked"
    assert not list(outside.rglob("*.json"))
    assert not list(outside.rglob("*.tmp"))


def test_contained_absolute_symlink_cannot_follow_replaced_project_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    specs = project / ".specs"
    contained = specs / "contained"
    contained.mkdir(parents=True)
    (specs / ".runs").symlink_to(contained, target_is_directory=True)
    contract, state = archive_valid_pair(project)
    original_open = goal_archive_fd._open_confined_directory
    replacement_contained = project / ".specs" / "contained"

    def replace_root_before_target_open(root_fd: int, project_root: Path, destination: Path) -> int:
        project.rename(tmp_path / "original-project")
        replacement_contained.mkdir(parents=True)
        (project / ".specs" / ".runs").symlink_to(replacement_contained, target_is_directory=True)
        return original_open(root_fd, project_root, destination)

    monkeypatch.setattr(
        goal_archive_fd, "_open_confined_directory", replace_root_before_target_open
    )
    result = archive_goal_run(contract, state, project_root=project, exit_code=0)

    assert result.outcome == "blocked"
    assert not list(replacement_contained.glob("*.json"))
    assert not list(replacement_contained.glob("*.tmp"))


def test_cooperative_writer_preserves_preexisting_temporary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    runs = project / ".specs" / ".runs"
    runs.mkdir(parents=True)
    temporary = runs / ".run.json.tmp"
    temporary.write_text("owned elsewhere", encoding="utf-8")
    monkeypatch.setattr(goal_archive_fd, "_temporary_name", lambda filename: f".{filename}.tmp")

    with pytest.raises(ConfinedArchiveError):
        goal_archive_fd.write_confined_json_artifact(project, runs, "run.json", {})

    assert temporary.read_text(encoding="utf-8") == "owned elsewhere"


def _archive_after_temporary_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    fail_after_replacement: bool,
) -> tuple[bool, Path, Path]:
    project = tmp_path / "project"
    runs = project / ".specs" / ".runs"
    runs.mkdir(parents=True)
    original_check = goal_archive_fd._require_opened_identity
    check_count = 0
    temporary = runs / ".run.json.tmp"
    monkeypatch.setattr(goal_archive_fd, "_temporary_name", lambda filename: f".{filename}.tmp")

    def replace_on_pre_publication_check(
        opened: goal_archive_fd._OpenedRunsDirectory,
    ) -> None:
        nonlocal check_count
        check_count += 1
        if check_count == 2:
            temporary.unlink()
            temporary.write_text('{"foreign": true}', encoding="utf-8")
            if fail_after_replacement:
                raise ConfinedArchiveError("deterministic post-write failure")
        original_check(opened)

    monkeypatch.setattr(
        goal_archive_fd, "_require_opened_identity", replace_on_pre_publication_check
    )
    blocked = False
    try:
        goal_archive_fd.write_confined_json_artifact(project, runs, "run.json", {})
    except ConfinedArchiveError:
        blocked = True
    return blocked, temporary, runs / "run.json"


def test_replaced_temporary_is_not_renamed_as_owned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blocked, temporary, final = _archive_after_temporary_replacement(
        tmp_path, monkeypatch, fail_after_replacement=False
    )

    assert blocked
    assert temporary.read_text(encoding="utf-8") == '{"foreign": true}'
    assert not final.exists()


def test_cleanup_preserves_temporary_replaced_before_identity_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blocked, temporary, final = _archive_after_temporary_replacement(
        tmp_path, monkeypatch, fail_after_replacement=True
    )

    assert blocked
    assert temporary.read_text(encoding="utf-8") == '{"foreign": true}'
    assert not final.exists()


def test_replaced_final_is_not_accepted_or_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    runs = project / ".specs" / ".runs"
    runs.mkdir(parents=True)
    original_link = os.link
    final = runs / "run.json"
    monkeypatch.setattr(goal_archive_fd, "_temporary_name", lambda filename: f".{filename}.tmp")

    def link_then_substitute(
        src: str,
        dst: str,
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> None:
        original_link(
            src,
            dst,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )
        final.unlink()
        final.write_text('{"foreign": true}', encoding="utf-8")

    monkeypatch.setattr(goal_archive_fd.os, "link", link_then_substitute)
    with pytest.raises(ConfinedArchiveError):
        goal_archive_fd.write_confined_json_artifact(project, runs, "run.json", {})

    assert final.read_text(encoding="utf-8") == '{"foreign": true}'
    assert not (runs / ".run.json.tmp").exists()


def test_failed_reopen_leaves_created_runs_for_safe_reuse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    specs = project / ".specs"
    specs.mkdir(parents=True)
    original_open = os.open
    runs_open_count = 0

    def fail_second_runs_open(
        path: str | bytes, flags: int, mode: int = 0o777, *, dir_fd: int | None = None
    ) -> int:
        nonlocal runs_open_count
        if path == ".runs":
            runs_open_count += 1
            if runs_open_count == 2:
                raise PermissionError("deterministic reopen failure")
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(goal_archive_fd.os, "open", fail_second_runs_open)
    with pytest.raises(ConfinedArchiveError):
        goal_archive_fd.resolve_confined_runs_directory(project)

    assert (specs / ".runs").is_dir()


def test_failed_identity_capture_preserves_unidentified_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    specs = project / ".specs"
    specs.mkdir(parents=True)
    original_open = os.open
    original_identity = goal_archive_fd._entry_identity
    runs_open_count = 0

    def lose_created_identity(parent_fd: int, name: str, *, follow: bool) -> tuple[int, int] | None:
        if name == ".runs" and not follow:
            return None
        return original_identity(parent_fd, name, follow=follow)

    def fail_second_runs_open(
        path: str | bytes, flags: int, mode: int = 0o777, *, dir_fd: int | None = None
    ) -> int:
        nonlocal runs_open_count
        if path == ".runs":
            runs_open_count += 1
            if runs_open_count == 2:
                raise PermissionError("deterministic reopen failure")
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(goal_archive_fd, "_entry_identity", lose_created_identity)
    monkeypatch.setattr(goal_archive_fd.os, "open", fail_second_runs_open)
    with pytest.raises(ConfinedArchiveError):
        goal_archive_fd.resolve_confined_runs_directory(project)

    assert (specs / ".runs").is_dir()
