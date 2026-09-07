"""Resolve the confined run-artifact destination for bootstrap goals."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from json import dumps
from pathlib import Path

from .goal_archive_fd import (
    ConfinedArchiveError,
    resolve_confined_runs_directory,
    write_confined_json_artifact,
)
from .goal_json import JsonObject
from .goal_pairing import GoalPairError, claims_spec_init, validate_goal_pair


class GoalArchivePathError(Exception):
    """Report an unsafe or unavailable bootstrap archive destination."""


@dataclass(frozen=True)
class BootstrapArchiveContext:
    """Carry validated bootstrap inputs and their confined destination.

    The returned JSON objects are isolated copies owned by the caller.
    """

    contract: JsonObject
    state: JsonObject
    project_root: Path
    runs_dir: Path


def resolve_bootstrap_archive_context(
    contract: Mapping[str, object],
    state: Mapping[str, object],
    *,
    feature: str | None,
) -> BootstrapArchiveContext | None:
    """Validate a claimed bootstrap archive and resolve its destination.

    Args:
        contract: Untrusted immutable goal contract.
        state: Untrusted mutable goal state.
        feature: Optional feature identity asserted by the caller.

    Returns:
        An isolated bootstrap context, or None for a non-bootstrap pair.

    Raises:
        GoalArchivePathError: If pair validation or destination confinement fails.

    Side effects:
        None; directory validation and creation are deferred to the single
        descriptor-owned write scope.
    """
    if not claims_spec_init(contract, state):
        return None
    try:
        # Pair identity must be proven before its persisted root is trusted;
        # directory opening stays deferred so mkdir and rename share one fd scope.
        pair = validate_goal_pair(contract, state, operation="archive", feature=feature)
    except GoalPairError as exc:
        raise GoalArchivePathError(str(exc)) from exc
    return BootstrapArchiveContext(
        contract=pair.contract,
        state=pair.state,
        project_root=pair.project_root,
        runs_dir=pair.project_root / ".specs" / ".runs",
    )


# @spec FR-005: Require initialized archive root, FR-011: Confine run destination
#   — .specs/features/076-spec-init-goal-bootstrap/spec.md#fr-005
def resolve_goal_runs_directory(project_root: Path) -> Path:
    """Return a real contained ``.specs/.runs`` directory.

    The function creates only the final ``.runs`` child when ``.specs`` is
    already real. Pinned descriptors and inode checks make concurrent visible
    path replacement fail closed.

    Args:
        project_root: Validated canonical bootstrap root.

    Returns:
        The resolved contained runs directory.

    Raises:
        GoalArchivePathError: If ``.specs`` is missing or either directory is
            broken, unreadable, not a directory, or escapes the project root.
    """
    try:
        return resolve_confined_runs_directory(project_root)
    except ConfinedArchiveError as exc:
        raise GoalArchivePathError(str(exc)) from exc


def write_goal_artifact(
    artifact: JsonObject,
    command: str,
    goal_hash: str,
    timestamp: datetime,
    project_root: Path,
    *,
    runs_dir: Path | None = None,
) -> Path:
    """Atomically write one run artifact to a legacy or confined destination.

    Args:
        artifact: Closed JSON artifact payload.
        command: Canonical command used in the filename.
        goal_hash: Canonical goal hash used in the filename.
        timestamp: Artifact timestamp used in the filename.
        project_root: Authoritative project root.
        runs_dir: Validated bootstrap destination, or None for legacy behavior.

    Returns:
        The final artifact path. The caller owns no open descriptor.

    Raises:
        GoalArchivePathError: If a confined write cannot remain attached to
            the pinned root, ``.specs``, and ``.runs`` directories.

    Side effects:
        Legacy mode renames a sibling temporary. Confined mode publishes by
        exclusive link while holding the archive lock and performs
        identity-aware best-effort residue cleanup for cooperative writers.
        Non-cooperative pathname replacement between checks and syscalls is
        outside the confined publication contract.
    """
    destination = runs_dir or project_root / ".specs" / ".runs"
    if runs_dir is None:
        destination.mkdir(parents=True, exist_ok=True)
    iso_fs = timestamp.astimezone(UTC).strftime("%Y-%m-%dT%H-%M-%S.%f")
    policy_suffix = "-policy2" if artifact.get("evidence_policy_version") == "2" else ""
    filename = f"{command}-{iso_fs}-{goal_hash[:8]}{policy_suffix}.json"
    if runs_dir is None:
        path = destination / filename
        temporary = path.with_suffix(".json.tmp")
        # Legacy compatibility still writes the complete sibling temporary
        # before rename so readers never observe a partial JSON document.
        temporary.write_text(dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")
        temporary.replace(path)
        return path
    try:
        return write_confined_json_artifact(project_root, destination, filename, artifact)
    except ConfinedArchiveError as exc:
        raise GoalArchivePathError(str(exc)) from exc


__all__ = [
    "BootstrapArchiveContext",
    "GoalArchivePathError",
    "resolve_bootstrap_archive_context",
    "resolve_goal_runs_directory",
    "write_goal_artifact",
]
