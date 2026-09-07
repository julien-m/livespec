# @spec(FR-003)
# @spec(FR-005)
# @spec(FR-006)
# @spec(AC-001)
# @spec(AC-003)
# @spec(AC-004)
# @spec(AC-006)

"""Build and load durable RunArtifact v2 JSON without mutating goal inputs."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from json import JSONDecodeError, loads
from pathlib import Path

from .exceptions import ArtifactMalformed
from .goal_archive_paths import (
    GoalArchivePathError,
    resolve_bootstrap_archive_context,
    write_goal_artifact,
)
from .goal_json import JsonObject, copy_json_object
from .goal_run_builder import (
    ARCHIVE_RUN_TASK_ID,
    RunArtifactBuildInput,
    build_run_artifact,
    goal_tasks_incomplete,
)
from .outcome import Outcome
from .run_receipts import ReceiptCheck, recheck_receipts

RUN_ARTIFACT_SCHEMA_VERSION = "2.0"
# @spec FR-001: archive.run task id shared by compiler injection and classifier
#   — .specs/features/059-pipeline-verify-phase/spec.md#fr-001
_COMMAND_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_GOAL_HASH_RE = re.compile(r"^[a-f0-9]{64}$")


@dataclass(frozen=True)
class ArchiveResult:
    """Outcome of one ``archive_goal_run`` invocation.

    Attributes:
        outcome: Stable success, drift, error, or blocked classification.
        path: Final artifact path when publication succeeds.
        artifact: Owned JSON copy when an artifact was built.
        blocked_reason: Actionable reason when publication is blocked.
    """

    outcome: Outcome
    path: Path | None
    artifact: JsonObject | None
    blocked_reason: str | None = None


# @spec FR-002: v2 schema + atomic timestamp-led writer
#   — .specs/features/039.1-goal-archive-run-artifacts/spec.md#fr-002
# @spec FR-003: optional transcript embedding
#   — .specs/features/039.1-goal-archive-run-artifacts/spec.md#fr-003
# @spec FR-005: Validate bootstrap archive before project access
#   — .specs/features/076-spec-init-goal-bootstrap/spec.md#fr-005
def archive_goal_run(
    contract: Mapping[str, object],
    state: Mapping[str, object],
    *,
    project_root: Path,
    feature: str | None = None,
    exit_code: int | None = None,
    stdout_text: str | None = None,
    stderr_text: str | None = None,
    now: datetime | None = None,
) -> ArchiveResult:
    """Atomically write RunArtifact v2 unless blocked, without mutating the goal pair.
    Args:
        contract: External immutable contract mapping.
        state: Read-only mutable-state snapshot.
        project_root: Legacy root; bootstrap pairs replace it canonically.
        feature: Optional feature identity and receipt scope.
        exit_code: Optional wrapped-command exit code.
        stdout_text: Optional stdout capture.
        stderr_text: Optional stderr capture.
        now: Optional deterministic UTC timestamp.
    Returns:
        Outcome, final path, owned artifact, and optional blocked reason.
    Raises:
        ValueError: Artifact construction rejects non-JSON input values.
        OSError: Legacy archive directory creation, temporary writing or rename fails.
    """
    runs_dir: Path | None = None
    try:
        # Direct API callers bypass CLI validation, so pair validation must
        # precede persisted-root selection and every filesystem mutation.
        bootstrap = resolve_bootstrap_archive_context(contract, state, feature=feature)
    except GoalArchivePathError as exc:
        return _blocked_archive(str(exc))
    if bootstrap is not None:
        contract = bootstrap.contract
        state = bootstrap.state
        project_root = bootstrap.project_root
        runs_dir = bootstrap.runs_dir
    return _archive_validated_pair(
        contract,
        state,
        project_root=project_root,
        runs_dir=runs_dir,
        feature=feature,
        exit_code=exit_code,
        stdout_text=stdout_text,
        stderr_text=stderr_text,
        now=now,
    )


def _archive_validated_pair(
    contract: Mapping[str, object],
    state: Mapping[str, object],
    *,
    project_root: Path,
    runs_dir: Path | None,
    feature: str | None,
    exit_code: int | None,
    stdout_text: str | None,
    stderr_text: str | None,
    now: datetime | None,
) -> ArchiveResult:
    if integrity_error := _current_archive_integrity_error(contract, feature):
        return _blocked_archive(integrity_error)
    contract_hash = str(contract.get("goal_hash", ""))
    state_hash = str(state.get("goal_hash", ""))
    if not contract_hash or contract_hash != state_hash:
        # EC-001: the state belongs to a different goal — refuse to archive.
        return _blocked_archive(
            f"goal_hash mismatch between contract ({contract_hash[:8] or 'missing'}) "
            f"and state ({state_hash[:8] or 'missing'})"
        )
    command = str(contract.get("command", "unknown"))
    if (invalid_reason := _validate_archive_identity(command, contract_hash)) is not None:
        return _blocked_archive(invalid_reason)
    resolved_feature = feature or _optional_str(contract.get("feature"))
    timestamp = now or datetime.now(UTC)
    artifact, outcome = build_run_artifact(
        RunArtifactBuildInput(
            contract=contract,
            state=state,
            command=command,
            contract_hash=contract_hash,
            project_root=project_root,
            feature=feature,
            resolved_feature=resolved_feature,
            exit_code=exit_code,
            stdout_text=stdout_text,
            stderr_text=stderr_text,
            timestamp=timestamp,
            schema_version=RUN_ARTIFACT_SCHEMA_VERSION,
        )
    )
    try:
        path = write_goal_artifact(
            artifact, command, contract_hash, timestamp, project_root, runs_dir=runs_dir
        )
    except GoalArchivePathError as exc:
        return _blocked_archive(str(exc))
    return ArchiveResult(outcome=outcome, path=path, artifact=artifact)


def find_latest_artifact(command: str, runs_dir: Path) -> Path | None:
    """Find the latest timestamp-led artifact for one command by reading the directory only.

    Args:
        command: Canonical command filename prefix.
        runs_dir: Directory containing run artifacts.

    Returns:
        Latest matching path, or None when the directory or match is absent.
    """
    if not runs_dir.is_dir():
        return None
    candidates = sorted(runs_dir.glob(f"{command}-*.json"))
    return candidates[-1] if candidates else None


def load_run_artifact(path: Path) -> JsonObject:
    """Read and minimally validate one RunArtifact v2 JSON object without writing files.

    Args:
        path: Explicit artifact file.

    Returns:
        An isolated closed JSON object owned by the caller.

    Raises:
        ArtifactMalformed: If the file is unreadable, malformed, non-object,
            or fails the minimum RunArtifact v2 schema.
    """
    try:
        raw: object = loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, JSONDecodeError) as exc:
        raise ArtifactMalformed(path.as_posix(), str(exc)) from exc
    if not isinstance(raw, dict):
        raise ArtifactMalformed(path.as_posix(), "artifact root must be a JSON object")
    artifact = copy_json_object(raw)
    if artifact is None:
        raise ArtifactMalformed(path.as_posix(), "artifact contains a non-JSON value")
    _validate_artifact_schema(artifact, path)
    return artifact


# @spec FR-004: Classifier excludes archive.run
#   — .specs/features/059-pipeline-verify-phase/spec.md#fr-004
# @spec FR-005: Pre-059 artifact tolerance (no schema change, exclusion never matches)
#   — .specs/features/059-pipeline-verify-phase/spec.md#fr-005
def _blocked_archive(reason: str) -> ArchiveResult:
    """Build a non-writing blocked archive result."""
    return ArchiveResult(outcome="blocked", path=None, artifact=None, blocked_reason=reason)


def _validate_archive_identity(command: str, goal_hash: str) -> str | None:
    """Validate external contract fields before using them in filenames."""
    if not _COMMAND_RE.fullmatch(command):
        return f"invalid command for run artifact filename: {command!r}"
    if not _GOAL_HASH_RE.fullmatch(goal_hash):
        return "invalid goal_hash for run artifact filename"
    return None


def _validate_artifact_schema(artifact: Mapping[str, object], path: Path) -> None:
    """Validate the minimum RunArtifact v2 shape required by verify-output."""
    from .acceptance_evidence import archived_policy2_path_error

    error = archived_policy2_path_error(artifact, path)
    if error:
        raise ArtifactMalformed(path.as_posix(), error)
    if artifact.get("evidence_policy_version") not in (None, "legacy", "1", "2"):
        raise ArtifactMalformed(path.as_posix(), "unsupported evidence_policy_version")
    checks: tuple[tuple[str, type[object]], ...] = (
        ("goal_hash", str),
        ("command", str),
        ("flags", list),
        ("timestamp", str),
        ("goal", dict),
        ("receipts", list),
        ("verify_rules", dict),
        ("verify_result", dict),
    )
    if artifact.get("schema_version") != RUN_ARTIFACT_SCHEMA_VERSION:
        raise ArtifactMalformed(path.as_posix(), "schema_version must be 2.0")
    for key, expected_type in checks:
        if not isinstance(artifact.get(key), expected_type):
            raise ArtifactMalformed(path.as_posix(), f"{key} has invalid or missing type")
    exit_code = artifact.get("exit_code")
    if exit_code is not None and not isinstance(exit_code, int):
        raise ArtifactMalformed(path.as_posix(), "exit_code must be integer or null")
    invalid_reason = _validate_archive_identity(
        str(artifact["command"]),
        str(artifact["goal_hash"]),
    )
    if invalid_reason is not None:
        raise ArtifactMalformed(path.as_posix(), invalid_reason)


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


__all__ = [
    "ARCHIVE_RUN_TASK_ID",
    "RUN_ARTIFACT_SCHEMA_VERSION",
    "ArchiveResult",
    "ReceiptCheck",
    "archive_goal_run",
    "find_latest_artifact",
    "goal_tasks_incomplete",
    "load_run_artifact",
    "recheck_receipts",
]


def _current_archive_integrity_error(
    contract: Mapping[str, object],
    feature: str | None,
) -> str | None:
    from .evidence_policy import contract_evidence_policy, current_contract_integrity_error

    integrity_error = current_contract_integrity_error(contract)
    if integrity_error:
        return integrity_error
    if (
        contract_evidence_policy(contract) is not None
        and feature is not None
        and feature != contract.get("feature")
    ):
        return "current_contract_archive_feature_mismatch"
    return None
