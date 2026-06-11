# LiveSpec traceability anchors
# @spec(AC-001)
# @spec(AC-003)
# @spec(AC-004)
# @spec(AC-006)

"""RunArtifact v2 data layer: schema, builder, atomic writer, and loader.

A RunArtifact is the durable, self-contained JSON record of one goal-locked
run, archived under ``.specs/.runs/`` by ``livespec goal archive``. The
``$TMPDIR`` contract/state inputs are read-only — this module never writes
back to them (AC-001).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from json import JSONDecodeError, dumps, loads
from pathlib import Path
from typing import Any, cast

from .exceptions import ArtifactMalformed
from .outcome import Outcome
from .run_receipts import ReceiptCheck, recheck_receipts, verify_evidence_receipts
from .verify_output import evaluate_rules

RUN_ARTIFACT_SCHEMA_VERSION = "2.0"
# @spec FR-001: archive.run task id shared by compiler injection and classifier
#   — .specs/features/059-pipeline-verify-phase/spec.md#fr-001
ARCHIVE_RUN_TASK_ID = "archive.run"
_COMMAND_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_GOAL_HASH_RE = re.compile(r"^[a-f0-9]{64}$")


@dataclass(frozen=True)
class ArchiveResult:
    """Outcome of one ``archive_goal_run`` invocation."""

    outcome: Outcome
    path: Path | None
    artifact: dict[str, Any] | None
    blocked_reason: str | None = None


# @spec FR-002: v2 schema + atomic timestamp-led writer
#   — .specs/features/039.1-goal-archive-run-artifacts/spec.md#fr-002
# @spec FR-003: optional transcript embedding
#   — .specs/features/039.1-goal-archive-run-artifacts/spec.md#fr-003
def archive_goal_run(
    contract: dict[str, Any],
    state: dict[str, Any],
    *,
    project_root: Path,
    feature: str | None = None,
    exit_code: int | None = None,
    stdout_text: str | None = None,
    stderr_text: str | None = None,
    now: datetime | None = None,
) -> ArchiveResult:
    """Archive a goal contract+state pair as a RunArtifact v2.

    Args:
        contract: Immutable goal contract JSON object (read-only).
        state: Mutable goal state JSON object (read-only).
        project_root: Project root containing ``.specs/``.
        feature: Optional feature slug; enables receipt feature scoping.
        exit_code: Wrapped command exit code, or None when not recorded.
        stdout_text: Captured stdout to embed, or None.
        stderr_text: Captured stderr to embed, or None.
        now: Timestamp override for deterministic tests; defaults to UTC now.

    Returns:
        An :class:`ArchiveResult`; ``blocked`` results carry no path and write
        nothing under ``.specs/.runs/`` (AC-002, EC-001).
    """
    contract_hash = str(contract.get("goal_hash", ""))
    state_hash = str(state.get("goal_hash", ""))
    if not contract_hash or contract_hash != state_hash:
        # EC-001: the state belongs to a different goal — refuse to archive.
        return ArchiveResult(
            outcome="blocked",
            path=None,
            artifact=None,
            blocked_reason=(
                f"goal_hash mismatch between contract ({contract_hash[:8] or 'missing'}) "
                f"and state ({state_hash[:8] or 'missing'})"
            ),
        )
    command = str(contract.get("command", "unknown"))
    invalid_reason = _validate_archive_identity(command, contract_hash)
    if invalid_reason is not None:
        return ArchiveResult(
            outcome="blocked",
            path=None,
            artifact=None,
            blocked_reason=invalid_reason,
        )
    resolved_feature = feature or _optional_str(contract.get("feature"))
    flags = [str(flag) for flag in _list_of(contract.get("normalized_flags"))]
    timestamp = now or datetime.now(UTC)
    goal_snapshot = _goal_snapshot(state)
    receipts = verify_evidence_receipts(
        goal_snapshot["tasks"],
        project_root=project_root,
        feature=feature,
    )
    verify_rules = _contract_verify_rules(contract)
    artifact: dict[str, Any] = {
        "schema_version": RUN_ARTIFACT_SCHEMA_VERSION,
        "goal_hash": contract_hash,
        "command": command,
        "feature": resolved_feature,
        "flags": flags,
        "exit_code": exit_code,
        "timestamp": timestamp.isoformat(),
    }
    if stdout_text is not None:
        artifact["stdout"] = stdout_text
    if stderr_text is not None:
        artifact["stderr"] = stderr_text
    artifact["goal"] = goal_snapshot
    artifact["receipts"] = [receipt.to_dict() for receipt in receipts]
    artifact["verify_rules"] = verify_rules
    report = evaluate_rules(
        verify_rules,
        artifact=artifact,
        active_flags=flags,
        feature=resolved_feature,
        project_root=project_root,
        goal_incomplete=_goal_incomplete(goal_snapshot),
        receipt_error=any(not receipt.verified for receipt in receipts),
    )
    artifact["verify_result"] = report.to_dict()
    path = _write_artifact(artifact, command, contract_hash, timestamp, project_root)
    return ArchiveResult(outcome=report.outcome, path=path, artifact=artifact)


def find_latest_artifact(command: str, runs_dir: Path) -> Path | None:
    """Return the lexicographically greatest ``<command>-*.json`` artifact.

    The timestamp leads the filename (AC-003), so lexicographic order equals
    chronological order; no lock or index file is needed.
    """
    if not runs_dir.is_dir():
        return None
    candidates = sorted(runs_dir.glob(f"{command}-*.json"))
    return candidates[-1] if candidates else None


def load_run_artifact(path: Path) -> dict[str, Any]:
    """Load and minimally validate a RunArtifact v2 JSON file.

    Raises:
        ArtifactMalformed: When the file is unreadable, not valid JSON, or
            not a JSON object — the message names the offending path (EC-007).
    """
    try:
        raw: object = loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, JSONDecodeError) as exc:
        raise ArtifactMalformed(path.as_posix(), str(exc)) from exc
    if not isinstance(raw, dict):
        raise ArtifactMalformed(path.as_posix(), "artifact root must be a JSON object")
    artifact = cast(dict[str, Any], raw)
    _validate_artifact_schema(artifact, path)
    return artifact


# ---------- helpers ----------


def _goal_snapshot(state: dict[str, Any]) -> dict[str, Any]:
    """Extract the embedded goal snapshot from the mutable state (read-only)."""
    tasks_raw = state.get("tasks")
    tasks_map = cast(dict[str, Any], tasks_raw) if isinstance(tasks_raw, dict) else {}
    tasks: list[dict[str, Any]] = []
    for task_id, task_obj in tasks_map.items():
        task = cast(dict[str, Any], task_obj) if isinstance(task_obj, dict) else {}
        ordinal_raw = task.get("ordinal")
        tasks.append(
            {
                "id": str(task_id),
                "ordinal": ordinal_raw if isinstance(ordinal_raw, int) else 0,
                "status": str(task.get("status", "pending")),
                "accepted_evidence": task.get("accepted_evidence"),
            }
        )
    tasks.sort(key=lambda task: (cast(int, task["ordinal"]), cast(str, task["id"])))
    return {"status": str(state.get("status", "unknown")), "tasks": tasks}


def _goal_incomplete(goal_snapshot: dict[str, Any]) -> bool:
    tasks = cast(list[dict[str, Any]], goal_snapshot["tasks"])
    return goal_tasks_incomplete(tasks)


# @spec FR-004: Classifier excludes archive.run
#   — .specs/features/059-pipeline-verify-phase/spec.md#fr-004
# @spec FR-005: Pre-059 artifact tolerance (no schema change, exclusion never matches)
#   — .specs/features/059-pipeline-verify-phase/spec.md#fr-005
def goal_tasks_incomplete(tasks: list[dict[str, Any]]) -> bool:
    """Return True when at least one required goal task is pending.

    Tasks whose id is ``archive.run`` are excluded: the artifact snapshot is
    taken before the archive proof is accepted, so ``archive.run`` pending is
    the expected shape of every enforced artifact (059 AC-006/EC-001).
    Pre-059 snapshots contain no ``archive.run`` id, so the exclusion never
    matches and their classification is unchanged (AC-007).

    Args:
        tasks: Goal snapshot task dicts (``id``/``status`` keys).

    Returns:
        True when a non-archive task is not ``complete``.
    """
    return any(
        task.get("status") != "complete" for task in tasks if task.get("id") != ARCHIVE_RUN_TASK_ID
    )


def _contract_verify_rules(contract: dict[str, Any]) -> dict[str, Any]:
    """Copy the verify rules verbatim so the artifact is self-contained."""
    canonical = contract.get("canonical")
    if isinstance(canonical, dict):
        rules = cast(dict[str, Any], canonical).get("verify_rules")
        if isinstance(rules, dict):
            return cast(dict[str, Any], rules)
    rules = contract.get("verify_rules")
    if isinstance(rules, dict):
        return cast(dict[str, Any], rules)
    return {"must": [], "may": [], "must_not": [], "when": []}


def _write_artifact(
    artifact: dict[str, Any],
    command: str,
    goal_hash: str,
    timestamp: datetime,
    project_root: Path,
) -> Path:
    """Atomically write the artifact (tmp + rename, AC-003)."""
    runs_dir = project_root / ".specs" / ".runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    # Filename grammar: timestamp leads (lexicographic == chronological) and
    # the hash8 suffix guarantees uniqueness without any lock (EC-003/EC-010).
    iso_fs = timestamp.astimezone(UTC).strftime("%Y-%m-%dT%H-%M-%S.%f")
    path = runs_dir / f"{command}-{iso_fs}-{goal_hash[:8]}.json"
    tmp = path.with_suffix(".json.tmp")
    # Write-then-rename keeps readers from ever observing a partial artifact.
    tmp.write_text(dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)
    return path


def _validate_archive_identity(command: str, goal_hash: str) -> str | None:
    """Validate external contract fields before using them in filenames."""
    if not _COMMAND_RE.fullmatch(command):
        return f"invalid command for run artifact filename: {command!r}"
    if not _GOAL_HASH_RE.fullmatch(goal_hash):
        return "invalid goal_hash for run artifact filename"
    return None


def _validate_artifact_schema(artifact: dict[str, Any], path: Path) -> None:
    """Validate the minimum RunArtifact v2 shape required by verify-output."""
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


def _list_of(value: object) -> list[object]:
    return cast(list[object], value) if isinstance(value, list) else []


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
