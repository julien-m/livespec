"""Validate immutable ``spec-init`` goal contract/state identity."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Never

from .goal_bootstrap import SPEC_INIT_COMMAND
from .goal_json import JsonObject, copy_json_object

GoalOperation = Literal["prove", "archive"]
_MIRROR_FIELDS = (
    "schema_version",
    "command",
    "feature",
    "project_root",
    "normalized_flags",
    "tasks",
)
_CONTRACT_FIELDS = (*_MIRROR_FIELDS, "goal_hash", "canonical", "canonical_json")
_STATE_FIELDS = ("schema_version", "goal_hash", "command", "status", "tasks")


class GoalPairError(Exception):
    """Report an invalid ``spec-init`` contract/state pair."""


@dataclass(frozen=True)
class ValidatedGoalPair:
    """Carry a fully validated bootstrap identity and isolated JSON copies."""

    command: str
    feature: str | None
    project_root: Path
    canonical_tasks: tuple[JsonObject, ...]
    contract: JsonObject
    state: JsonObject


def claims_spec_init(contract: Mapping[str, object], state: Mapping[str, object]) -> bool:
    """Return whether any immutable command identity claims ``spec-init``.

    Args:
        contract: Untrusted immutable contract mapping.
        state: Untrusted mutable state mapping.

    Returns:
        True when canonical, mirrored, or state command equals ``spec-init``.
    """
    canonical = contract.get("canonical")
    canonical_command = canonical.get("command") if isinstance(canonical, Mapping) else None
    return any(
        value == SPEC_INIT_COMMAND
        for value in (canonical_command, contract.get("command"), state.get("command"))
    )


# @spec FR-004: Validate proof pair before access, FR-005: Validate archive pair
# @spec FR-010: Enforce identity and statuses, FR-012: Reject legacy roots
#   — .specs/features/076-spec-init-goal-bootstrap/spec.md#fr-004
def validate_goal_pair(
    contract: Mapping[str, object],
    state: Mapping[str, object],
    *,
    operation: GoalOperation,
    feature: str | None = None,
) -> ValidatedGoalPair:
    """Validate a claimed spec-init pair before project access.

    Args:
        contract: Explicit immutable contract JSON.
        state: Explicit mutable state JSON.
        operation: Operation selecting the diagnostic context.
        feature: Optional archive feature assertion.

    Returns:
        A validated identity with deep-copied contract and state.

    Raises:
        GoalPairError: If identity, hashing, task mirrors, or statuses differ.
    """
    # Close both graphs first because direct API callers bypass the CLI JSON parser.
    closed_contract = _json_object(contract, "contract", operation)
    closed_state = _json_object(state, "state", operation)
    canonical = _mapping(closed_contract.get("canonical"), "contract canonical", operation)
    _validate_contract_identity(closed_contract, canonical, operation)
    tasks = _canonical_tasks(canonical.get("tasks"), operation)
    _validate_state_identity(closed_contract, closed_state, canonical, tasks, operation)
    canonical_feature = _optional_string(canonical.get("feature"), "canonical feature", operation)
    if feature is not None and feature != canonical_feature:
        _fail(operation, "explicit feature differs from canonical feature")
    project_root = _resolve_project_root(canonical.get("project_root"), operation)
    return ValidatedGoalPair(
        command=SPEC_INIT_COMMAND,
        feature=canonical_feature,
        project_root=project_root,
        canonical_tasks=tuple(_json_object(task, "canonical task", operation) for task in tasks),
        contract=closed_contract,
        state=closed_state,
    )


def _validate_contract_identity(
    contract: Mapping[str, object],
    canonical: Mapping[str, object],
    operation: GoalOperation,
) -> None:
    _require_fields(contract, _CONTRACT_FIELDS, "contract", operation)
    _require_fields(canonical, _MIRROR_FIELDS, "canonical", operation)
    if canonical.get("schema_version") != "2.0":
        _fail(operation, "canonical schema_version is invalid")
    if canonical.get("command") != SPEC_INIT_COMMAND:
        _fail(operation, "canonical command is not spec-init")
    _optional_string(canonical.get("feature"), "canonical feature", operation)
    _string_list(canonical.get("normalized_flags"), "canonical normalized_flags", operation)
    for field in _MIRROR_FIELDS:
        if field not in contract or field not in canonical or contract[field] != canonical[field]:
            _fail(operation, f"contract mirror mismatch: {field}")
    canonical_json = contract.get("canonical_json")
    if not isinstance(canonical_json, str):
        _fail(operation, "canonical_json is missing or invalid")
    try:
        parsed: object = json.loads(canonical_json)
    except json.JSONDecodeError:
        _fail(operation, "canonical_json is malformed")
    if parsed != canonical:
        _fail(operation, "canonical_json differs from canonical")
    goal_hash = contract.get("goal_hash")
    expected_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    if goal_hash != expected_hash:
        _fail(operation, "goal hash differs from canonical_json")


def _validate_state_identity(
    contract: Mapping[str, object],
    state: Mapping[str, object],
    canonical: Mapping[str, object],
    tasks: list[JsonObject],
    operation: GoalOperation,
) -> None:
    _require_fields(state, _STATE_FIELDS, "state", operation)
    for field in ("schema_version", "command", "goal_hash"):
        expected = contract.get(field)
        if field == "command":
            expected = canonical.get(field)
        if state.get(field) != expected:
            _fail(operation, f"state identity mismatch: {field}")
    task_states = _mapping(state.get("tasks"), "state tasks", operation)
    expected_by_id: dict[str, JsonObject] = {}
    for task in tasks:
        task_id = task.get("id")
        if not isinstance(task_id, str):
            _fail(operation, "canonical task id is invalid")
        expected_by_id[task_id] = task
    if set(task_states) != set(expected_by_id):
        _fail(operation, "state task keys differ from canonical tasks")
    statuses: list[str] = []
    for task_id, task in expected_by_id.items():
        task_state = _mapping(task_states[task_id], f"state task {task_id}", operation)
        _require_fields(
            task_state,
            ("ordinal", "description", "status", "attempts", "accepted_evidence", "last_rejection"),
            f"state task {task_id}",
            operation,
        )
        state_ordinal = task_state.get("ordinal")
        if type(state_ordinal) is not int or state_ordinal != task["ordinal"]:
            _fail(operation, f"state task ordinal mismatch: {task_id}")
        if task_state.get("description") != task["description"]:
            _fail(operation, f"state task description mismatch: {task_id}")
        status = task_state.get("status")
        if not isinstance(status, str) or status not in {"pending", "complete"}:
            _fail(operation, f"invalid task status: {task_id}")
        statuses.append(status)
        if not isinstance(task_state.get("attempts"), list):
            _fail(operation, f"state task attempts are invalid: {task_id}")
        for field in ("accepted_evidence", "last_rejection"):
            value = task_state.get(field)
            if value is not None and not isinstance(value, Mapping):
                _fail(operation, f"state task {field} is invalid: {task_id}")
    expected_status = "complete" if all(status == "complete" for status in statuses) else "active"
    if state.get("status") != expected_status:
        _fail(operation, "goal status contradicts task statuses")


def _canonical_tasks(value: object, operation: GoalOperation) -> list[JsonObject]:
    if not isinstance(value, list):
        _fail(operation, "canonical tasks must be a list")
    tasks: list[JsonObject] = []
    seen_ids: set[str] = set()
    for expected_ordinal, raw_task in enumerate(value, start=1):
        task = _mapping(raw_task, "canonical task", operation)
        _require_fields(
            task,
            (
                "id",
                "ordinal",
                "description",
                "category",
                "completion_actor",
                "required_evidence",
                "invalid_substitutes",
                "repair_if_missing",
                "expected_evidence",
            ),
            "canonical task",
            operation,
        )
        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id or task_id in seen_ids:
            _fail(operation, "canonical task id is invalid")
        seen_ids.add(task_id)
        if type(task.get("ordinal")) is not int or task.get("ordinal") != expected_ordinal:
            _fail(operation, "canonical task ordinal is invalid")
        if not isinstance(task.get("description"), str) or not task.get("description"):
            _fail(operation, "canonical task description is invalid")
        for field in ("category", "completion_actor"):
            if not isinstance(task.get(field), str) or not task.get(field):
                _fail(operation, f"canonical task {field} is invalid")
        for field in ("required_evidence", "invalid_substitutes", "repair_if_missing"):
            _string_list(task.get(field), f"canonical task {field}", operation)
        if not isinstance(task.get("expected_evidence"), Mapping):
            _fail(operation, "canonical task expected_evidence is invalid")
        tasks.append(_json_object(task, "canonical task", operation))
    return tasks


def _resolve_project_root(value: object, operation: GoalOperation) -> Path:
    if not isinstance(value, str) or not value or not Path(value).is_absolute():
        _fail(operation, "canonical project_root is missing or invalid")
    candidate = Path(value)
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        reason = (
            f"canonical project_root is unreadable: {exc}; rerender the goal before {operation}"
        )
        raise GoalPairError(reason) from exc
    if resolved.as_posix() != candidate.as_posix() or not resolved.is_dir():
        _fail(operation, "canonical project_root is not a real directory")
    if not os.access(resolved, os.R_OK):
        _fail(operation, "canonical project_root is not readable")
    return resolved


def _mapping(value: object, label: str, operation: GoalOperation) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        _fail(operation, f"{label} must be an object")
    if any(not isinstance(key, str) for key in value):
        _fail(operation, f"{label} keys must be strings")
    return {str(key): item for key, item in value.items()}


def _optional_string(value: object, label: str, operation: GoalOperation) -> str | None:
    if value is not None and not isinstance(value, str):
        _fail(operation, f"{label} must be a string or null")
    return value


def _require_fields(
    value: Mapping[str, object], fields: tuple[str, ...], label: str, operation: GoalOperation
) -> None:
    missing = [field for field in fields if field not in value]
    if missing:
        _fail(operation, f"{label} missing required field: {missing[0]}")


def _string_list(value: object, label: str, operation: GoalOperation) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        _fail(operation, f"{label} must be a list of strings")
    strings = [item for item in value if isinstance(item, str)]
    if len(strings) != len(set(strings)):
        _fail(operation, f"{label} must not contain duplicates")
    return strings


def _json_object(value: object, label: str, operation: GoalOperation) -> JsonObject:
    copied = copy_json_object(dict(value) if isinstance(value, Mapping) else value)
    if copied is None:
        _fail(operation, f"{label} contains a non-JSON value")
    return copied


def _fail(operation: GoalOperation, reason: str) -> Never:
    raise GoalPairError(f"{reason}; rerender the goal before {operation}")


__all__ = [
    "GoalPairError",
    "ValidatedGoalPair",
    "claims_spec_init",
    "validate_goal_pair",
]
