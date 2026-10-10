"""Bounded recovery of current approval authority after a failed pipeline write."""

from collections.abc import Callable
from pathlib import Path

from .locks import atomic_write
from .penflow_approval_files import BASELINE, JsonObject, PenflowApprovalError, bounded, json_bytes

# The pipeline facade is the sole caller; dependencies preserve its existing I/O seam.
__all__ = ["_publish_phase_update"]


def _restore_bytes(path: Path, raw: bytes) -> None:
    """Restore UTF-8 bytes atomically and reject unreadable or mismatched readback."""
    atomic_write(path, raw.decode("utf-8"))
    if path.read_bytes() != raw:
        raise PenflowApprovalError(f"pipeline_rollback_readback_mismatch: {path}")


def _restore_failed_approval(
    root: Path,
    baseline: Path,
    previous: bytes | None,
    published: bytes,
    pipeline: Path,
    old_phase: bytes,
    new_phase: bytes,
) -> None:
    """Restore only this transition's current files while the caller holds the lock.

    baseline/previous identify the prior authority (None means absent), and
    published binds this invocation's new authority. pipeline plus old/new_phase
    distinguish failure before commit from failure after rename. Reject foreign
    bytes or a changed target with PenflowApprovalError; propagate I/O failures.
    Immutable archives are never removed. Noncooperating writes are not atomic
    with these checks: an observed conflict stops recovery rather than overwriting.
    """
    if bounded(root, BASELINE) != baseline or baseline.read_bytes() != published:
        raise PenflowApprovalError("pipeline_rollback_conflict: authority changed")
    actual_phase = pipeline.read_bytes()
    if actual_phase not in (old_phase, new_phase):
        raise PenflowApprovalError("pipeline_rollback_conflict: phase changed")
    # A writer may raise after rename; restore its Done row before reverting authority.
    if actual_phase != old_phase:
        _restore_bytes(pipeline, old_phase)
    if bounded(root, BASELINE) != baseline or baseline.read_bytes() != published:
        raise PenflowApprovalError("pipeline_rollback_conflict: authority changed")
    if previous is None:
        baseline.unlink()
    else:
        _restore_bytes(baseline, previous)


# @spec FR-007: Fail-closed interrupted approval replay
# .specs/features/077-penflow-cumulative-verdict-consumer/spec.md#fr-007
def _publish_phase_update(
    root: Path,
    feature: str,
    review: Path | None,
    pipeline: Path,
    new_content: str | None,
    *,
    approve: Callable[[Path, str, Path], JsonObject],
    write: Callable[[Path, str], str],
) -> None:
    """Publish approval then phase, recovering handled phase-write failures.

    root/feature/review select current approval; pipeline/new_content select its
    phase edit (None is an unchanged row). approve/write are facade I/O callbacks.
    Caller holds the project lock. Return None after success; propagate approval
    or write errors. Failed restoration raises an explicit PenflowApprovalError.
    Archives remain immutable; process death and noncooperating races are not a
    multi-file transaction. Calls without review retain ordinary writer behavior.
    """
    if review is None:
        if new_content is not None:
            write(pipeline, new_content)
        return
    baseline = bounded(root, BASELINE)
    previous = baseline.read_bytes() if baseline.exists() else None
    old_phase = pipeline.read_bytes()
    published = json_bytes(approve(root, feature, review))
    if new_content is None:
        return
    try:
        write(pipeline, new_content)
    except OSError as exc:
        try:
            _restore_failed_approval(
                root, baseline, previous, published, pipeline, old_phase, new_content.encode()
            )
        except (OSError, ValueError) as rollback:
            raise PenflowApprovalError(
                f"pipeline_approval_rollback_failed: {rollback}; original write: {exc}"
            ) from rollback
        raise
