"""Project runtime selection: ``pin``, ``upgrade`` and ``dev`` (lock, path, links)."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import replace
from pathlib import Path

from validator.locks import LockAcquisitionError, acquire_lock

from .errors import RuntimeLockError, RuntimeSelectionError
from .home import RuntimeHome, is_livespec_root, read_project_version, require_project_root
from .links import LinkUpdate, apply_link_updates, plan_link_updates, replace_symlink
from .manifest import read_manifest, verify_snapshot
from .models import (
    LIVESPEC_PATH_RELPATH,
    LOCK_RELPATH,
    SCHEMA_VERSION,
    JsonObject,
    JsonValue,
    LinkReport,
    RuntimeManifest,
    SelectionResult,
)
from .shim_core import RUNTIME_ID_RE, LockData, ShimResolutionError, parse_lock

# Previous lock/.livespec-path bytes (None = absent) and previous link texts.
SavedState = tuple[dict[Path, bytes | None], dict[Path, str]]
# `git check-ignore -q` exit status meaning "the path is not ignored".
_NOT_IGNORED = 1
_GIT_TIMEOUT_SECONDS = 60


def read_lock(project: Path) -> tuple[LockData | None, JsonValue]:
    """Read the project lock for reporting.

    Args:
        project: Project root.

    Returns:
        ``(lock, previous)``: the parsed lock (None if absent or invalid) and its
        report form (lock mapping, ``"invalid"`` or None when absent).
    """
    path = project / LOCK_RELPATH
    if not path.exists():
        return None, None
    try:
        lock = parse_lock(path.read_text(encoding="utf-8"), path)
    except (OSError, ShimResolutionError):
        return None, "invalid"
    return lock, dict(lock)


def lock_bytes(lock: LockData) -> bytes:
    """Serialize a lock with sorted keys, two-space indent and a trailing newline."""
    return (json.dumps(lock, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write_if_changed(path: Path, data: bytes) -> bool:
    if path.is_file() and path.read_bytes() == data:
        return False
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    # Write a sibling then rename: the committed lock is never observed half-written.
    temporary.write_bytes(data)
    os.replace(temporary, path)
    return True


def _ignore_warnings(project: Path) -> tuple[str, ...]:
    # Contract: `git check-ignore -q <path>` exits 0 when ignored, 1 when not ignored and
    # 128 outside a repository (no warning then). Read-only; the project's own git only.
    try:
        completed = subprocess.run(
            ["git", "-C", str(project), "check-ignore", "-q", str(LIVESPEC_PATH_RELPATH)],
            capture_output=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return (f"could not check whether {LIVESPEC_PATH_RELPATH} is git-ignored: {exc}",)
    if completed.returncode != _NOT_IGNORED:
        return ()
    return (f"{LIVESPEC_PATH_RELPATH} is machine-local but not git-ignored; add it to .gitignore",)


def _target_runtime_id(home: RuntimeHome, runtime: str) -> str:
    if runtime != "current":
        if not RUNTIME_ID_RE.match(runtime):
            raise RuntimeSelectionError(f"invalid runtime id: {runtime}")
        return runtime
    if not home.current.is_dir():
        raise RuntimeSelectionError(
            f"no current runtime under {home.root}; run `livespec runtime install` first"
        )
    return read_manifest(home.current.resolve()).runtime_id


def _verified_target(home: RuntimeHome, runtime: str, project: Path) -> RuntimeManifest:
    manifest = verify_snapshot(home, _target_runtime_id(home, runtime))
    project_version = read_project_version(project)
    if project_version > manifest.livespec_version:
        raise RuntimeSelectionError(
            f"project livespec-version {project_version} is newer than runtime "
            f"{manifest.runtime_id} (VERSION {manifest.livespec_version}); install a newer runtime"
        )
    return manifest


def _pinned_lock(manifest: RuntimeManifest) -> LockData:
    return {
        "schema": SCHEMA_VERSION,
        "mode": "pinned",
        "runtime_id": manifest.runtime_id,
        "livespec_version": manifest.livespec_version,
        "commit": manifest.commit,
    }


def _saved_state(project: Path, updates: list[LinkUpdate]) -> SavedState:
    paths = _selection_files(project)
    files = {path: path.read_bytes() if path.is_file() else None for path in paths}
    links = {u.link.path: u.link.text for u in updates if u.action == "retarget"}
    return files, links


def _selection_files(project: Path) -> tuple[Path, Path]:
    return project / LOCK_RELPATH, project / LIVESPEC_PATH_RELPATH


def _restore_state(saved: SavedState) -> None:
    """Put back the previous lock, ``.livespec-path`` and link texts after a failure."""
    files, links = saved
    for path, data in files.items():
        if data is None:
            path.unlink(missing_ok=True)
        else:
            _write_if_changed(path, data)
    for link, text in links.items():
        replace_symlink(link, text)


def _publish(project: Path, lock: LockData, runtime_root: Path) -> tuple[bool, LinkReport]:
    """Validate links, then write ``.livespec-path``, links and the lock (D-14), all-or-nothing.

    Order matters: the lock is the generation marker read by the shim and status, so it
    is replaced last; a reader that sees the new lock already sees the new references.

    Raises:
        RuntimeSelectionError: If the publication failed and the rollback could not
            restore the previous selection (the original error is chained).
    """
    updates = plan_link_updates(project, runtime_root)
    saved = _saved_state(project, updates)
    lock_path, path_file = _selection_files(project)
    try:
        changed = _write_if_changed(path_file, f"{runtime_root}\n".encode())
        links = apply_link_updates(project, updates)
        changed = _write_if_changed(lock_path, lock_bytes(lock)) or changed
    except BaseException as failure:
        # Any failure (including an interrupt) restores the previous selection, then re-raises.
        try:
            _restore_state(saved)
        except OSError as rollback_error:
            raise RuntimeSelectionError(
                f"selection failed; rollback incomplete: {rollback_error} (after: {failure})"
            ) from failure
        raise
    return changed or bool(links.retargeted), links


# @spec FR-005: Locked atomic selection, FR-006: Link rollback
#   — .specs/features/083-pinned-runtime-isolation/spec.md#fr-005
def _select(
    project: Path, lock: LockData, runtime_root: Path, previous: JsonValue
) -> SelectionResult:
    """Publish a selection while holding the project's ``.specs/.LOCK``."""
    try:
        with acquire_lock(project / ".specs"):
            changed, links = _publish(project, lock, runtime_root)
    except LockAcquisitionError as exc:
        raise RuntimeSelectionError(f"project lock busy, nothing written: {exc}") from exc
    except OSError as exc:
        raise RuntimeSelectionError(f"selection failed and was rolled back: {exc}") from exc
    lock_json: JsonObject = dict(lock)
    return SelectionResult(
        project=project,
        mode=str(lock["mode"]),
        lock=lock_json,
        previous_lock=previous,
        runtime_root=runtime_root,
        changed=changed,
        links=links,
        warnings=_ignore_warnings(project),
    )


# @spec FR-005: Pin writes — .specs/features/083-pinned-runtime-isolation/spec.md#fr-005
def pin_project(start: Path, runtime: str, home: RuntimeHome) -> SelectionResult:
    """Pin a project to a verified installed runtime (``livespec runtime pin``).

    Args:
        start: ``--project`` value or working directory.
        runtime: Runtime id or ``current``.
        home: Runtime home.

    Returns:
        The selection outcome, reporting the previous lock.

    Raises:
        RuntimeSelectionError: No runtime, unverified runtime or newer project version.
        RuntimeSnapshotError: The target snapshot does not verify.
    """
    project = require_project_root(start)
    _lock, previous = read_lock(project)
    manifest = _verified_target(home, runtime, project)
    snapshot = home.snapshot(manifest.runtime_id)
    return _select(project, _pinned_lock(manifest), snapshot, previous)


# @spec FR-007: Upgrade — .specs/features/083-pinned-runtime-isolation/spec.md#fr-007
def upgrade_project(start: Path, target: str, home: RuntimeHome) -> SelectionResult:
    """Move a pinned project to another verified runtime (``livespec runtime upgrade``).

    Args:
        start: ``--project`` value or working directory.
        target: Runtime id or ``current``.
        home: Runtime home.

    Returns:
        The selection outcome with old/new ids and ``migration_required``.

    Raises:
        RuntimeLockError: The project has no valid pinned lock.
        RuntimeSelectionError: Target unverified or older than the project version.
    """
    project = require_project_root(start)
    lock, previous = read_lock(project)
    if lock is None or lock["mode"] != "pinned":
        raise RuntimeLockError(
            f"upgrade requires a pinned {LOCK_RELPATH}; run `livespec runtime pin` first"
        )
    manifest = _verified_target(home, target, project)
    old_id = str(lock["runtime_id"])
    migration = read_project_version(project) < manifest.livespec_version
    snapshot = home.snapshot(manifest.runtime_id)
    if manifest.runtime_id == old_id:
        lock_json: JsonObject = dict(lock)
        return SelectionResult(
            project=project,
            mode="pinned",
            lock=lock_json,
            previous_lock=previous,
            runtime_root=snapshot,
            changed=False,
            old_runtime_id=old_id,
            migration_required=migration,
        )
    result = _select(project, _pinned_lock(manifest), snapshot, previous)
    return replace(result, old_runtime_id=old_id, migration_required=migration)


def _dev_lock_source(project: Path, source: Path) -> str:
    if source == project:
        return "."
    if source.is_relative_to(project):
        return source.relative_to(project).as_posix()
    return str(source)


# @spec FR-008: Dev lock — .specs/features/083-pinned-runtime-isolation/spec.md#fr-008
def dev_project(start: Path, source: Path) -> SelectionResult:
    """Declare dev mode on a project (``livespec runtime dev``).

    Args:
        start: ``--project`` value or working directory.
        source: LiveSpec checkout to execute.

    Returns:
        The selection outcome.

    Raises:
        RuntimeSelectionError: The source is not a LiveSpec root.
    """
    project = require_project_root(start)
    _lock, previous = read_lock(project)
    checkout = source.expanduser().resolve()
    if not is_livespec_root(checkout):
        raise RuntimeSelectionError(f"dev source is not a LiveSpec root: {checkout}")
    lock: LockData = {
        "schema": SCHEMA_VERSION,
        "mode": "dev",
        "source": _dev_lock_source(project, checkout),
    }
    return _select(project, lock, checkout, previous)
