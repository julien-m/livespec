"""Goal proof responsibilities behind the public contract facade."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from . import goal_contracts as _contracts
from .goal_outcome import MAX_ATTEMPTS_PER_TASK


# @spec FR-010: Preserve proof transitions, FR-011: Confine project evidence
#   — .specs/features/076-spec-init-goal-bootstrap/spec.md#fr-010
def prove_goal_task(
    contract: dict[str, Any],
    state: dict[str, Any],
    task_id: str,
    evidence: dict[str, Any],
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Validate evidence for one contract task and return an updated state.

    Args:
        contract: Immutable goal contract mapping.
        state: Read-only mutable-state snapshot.
        task_id: Contract task to prove.
        evidence: Submitted evidence object.
        project_root: Legacy receipt root; bootstrap pairs override it.

    Returns:
        Proof outcome plus an isolated updated state.

    Raises:
        GoalPairError: If a claimed bootstrap pair fails revalidation.
        GoalEvidencePathError: If bootstrap evidence escapes its persisted root.

    Side effects:
        None; the returned state is a copy and persistence remains a CLI concern.
    """
    if _contracts.claims_spec_init(contract, state):
        # Direct API calls bypass the CLI boundary. Preserve the security order:
        # validate pair, select persisted root, confine evidence, then mutate a copy.
        pair = _contracts.validate_goal_pair(contract, state, operation="prove")
        contract = pair.contract
        state = pair.state
        project_root = pair.project_root
        evidence = _contracts.confine_bootstrap_evidence(evidence, pair.project_root)
    return _contracts._prove_validated_goal_task(contract, state, task_id, evidence, project_root)


__all__ = [
    "_ensure_state_task",
    "_goal_proof_result",
    "_goal_tasks_by_id",
    "_prove_validated_goal_task",
    "_record_task_proof",
    "_refresh_state_status",
    "_unknown_task_proof",
    "_validate_task_proof",
    "prove_goal_task",
]


def _prove_validated_goal_task(
    contract: Mapping[str, object],
    state: Mapping[str, object],
    task_id: str,
    evidence: _contracts.JsonObject,
    project_root: Path | None,
) -> _contracts.JsonObject:
    integrity_error = _contracts.current_contract_integrity_error(contract)
    if integrity_error:
        return {
            "task_id": task_id,
            "status": "REJECTED_NEEDS_ACTION",
            "accepted": False,
            "missing_evidence": [integrity_error],
            "invalid_substitutes": [],
            "state": _contracts.copy_json_object(state),
        }
    tasks = _contracts._goal_tasks_by_id(contract)
    task = tasks.get(task_id)
    updated_state = _contracts.copy_json_object(state)
    if updated_state is None:
        raise TypeError("goal state must be a JSON object")
    if task is None:
        return _contracts._unknown_task_proof(task_id, updated_state)
    task_state = _contracts._ensure_state_task(updated_state, task)
    proof = _contracts._validate_task_proof(task, evidence, contract, project_root)
    _contracts._record_task_proof(task_state, evidence, proof)
    _contracts._refresh_state_status(updated_state)
    return _contracts._goal_proof_result(task_id, updated_state, proof)


def _validate_task_proof(
    task: _contracts.JsonObject,
    evidence: _contracts.JsonObject,
    contract: Mapping[str, object],
    project_root: Path | None,
) -> _contracts._TaskEvidenceValidation:
    # Feature 052 evidence-family validators expose dynamic dictionaries. Cast
    # once at that legacy boundary, then consume only this closed proof shape.
    return cast(
        _contracts._TaskEvidenceValidation,
        _contracts._validate_task_evidence(
            cast(dict[str, Any], task),
            cast(dict[str, Any], evidence),
            contract=cast(dict[str, Any], contract),
            project_root=project_root,
        ),
    )


def _record_task_proof(
    task_state: _contracts.JsonObject,
    evidence: _contracts.JsonObject,
    proof: _contracts._TaskEvidenceValidation,
) -> None:
    missing_evidence: list[_contracts.JsonValue] = [value for value in proof["missing_evidence"]]
    invalid_substitutes: list[_contracts.JsonValue] = [
        value for value in proof["invalid_substitutes"]
    ]
    attempt: _contracts.JsonObject = {
        "status": proof["status"],
        "evidence": evidence,
        "missing_evidence": missing_evidence,
        "invalid_substitutes": invalid_substitutes,
    }
    if "observed" in proof:
        attempt["observed"] = cast(_contracts.JsonValue, proof["observed"])
    if "attempts" not in task_state:
        attempts_value: _contracts.JsonValue = []
        task_state["attempts"] = attempts_value
    else:
        attempts_value = task_state["attempts"]
        if not isinstance(attempts_value, list):
            raise TypeError("goal task attempts must be a list")
    attempts = cast(list[_contracts.JsonValue], attempts_value)
    attempts.append(attempt)
    if proof["accepted"]:
        task_state["status"] = "complete"
        task_state["accepted_evidence"] = evidence
        task_state["last_rejection"] = None
        task_state.pop("blocked", None)
    else:
        # @spec FR-007: Bounded retries
        #   — .specs/features/081-lightweight-outcome-goals/spec.md#fr-007
        if _rejected_streak(attempts) >= MAX_ATTEMPTS_PER_TASK:
            task_state["blocked"] = True
        task_state["status"] = "pending"
        rejection: _contracts.JsonObject = {
            "missing_evidence": missing_evidence,
            "invalid_substitutes": invalid_substitutes,
            "required_actions": [value for value in proof["required_actions"]],
        }
        task_state["last_rejection"] = rejection


def _goal_proof_result(
    task_id: str,
    updated_state: _contracts.JsonObject,
    proof: _contracts._TaskEvidenceValidation,
) -> _contracts.JsonObject:
    task_state = cast(_contracts.JsonObject, cast(dict[str, Any], updated_state["tasks"])[task_id])
    blocked = not proof["accepted"] and task_state.get("blocked") is True
    result: _contracts.JsonObject = {
        "task_id": task_id,
        "status": "BLOCKED" if blocked else proof["status"],
        "accepted": proof["accepted"],
        "missing_evidence": [value for value in proof["missing_evidence"]],
        "invalid_substitutes": [value for value in proof["invalid_substitutes"]],
        "required_actions": [value for value in proof["required_actions"]],
        "state": updated_state,
    }
    if "observed" in proof:
        result["observed"] = cast(_contracts.JsonValue, proof["observed"])
    if blocked:
        result["handback"] = _handback(task_id, task_state, proof)
    return result


def _rejected_streak(attempts: list[_contracts.JsonValue]) -> int:
    streak = 0
    for attempt in reversed(attempts):
        if not isinstance(attempt, dict) or attempt.get("status") == "ACCEPTED":
            break
        streak += 1
    return streak


def _handback(
    task_id: str,
    task_state: _contracts.JsonObject,
    proof: _contracts._TaskEvidenceValidation,
) -> _contracts.JsonObject:
    """Summarize what was tried and what is still missing before handing control back."""
    attempts = cast(list[dict[str, Any]], task_state.get("attempts") or [])
    tried: list[_contracts.JsonValue] = [
        {"attempt": index, "missing_evidence": attempt.get("missing_evidence") or []}
        for index, attempt in enumerate(attempts, 1)
    ]
    return {
        "task_id": task_id,
        "attempts": len(attempts),
        "tried": tried,
        "missing_evidence": [value for value in proof["missing_evidence"]],
        "required_actions": [value for value in proof["required_actions"]],
        "report": (
            f"BLOCKED at step {task_state.get('ordinal')} - verification_failed - "
            f"{task_id} rejected {len(attempts)} times; missing: "
            f"{', '.join(proof['missing_evidence']) or 'none'}"
        )[:200],
    }


def _goal_tasks_by_id(contract: Mapping[str, object]) -> dict[str, _contracts.JsonObject]:
    tasks: dict[str, _contracts.JsonObject] = {}
    if "tasks" not in contract:
        return tasks
    contract_tasks = contract["tasks"]
    if not isinstance(contract_tasks, list):
        # Non-init callers historically classify malformed task collections as
        # an unknown task. Bootstrap pairs are rejected earlier at validation.
        return tasks
    for task_item in contract_tasks:
        task_dict = _contracts.copy_json_object(task_item)
        if task_dict is None:
            continue
        task_id_value = task_dict.get("id")
        if not isinstance(task_id_value, str):
            continue
        tasks[task_id_value] = task_dict
    return tasks


def _unknown_task_proof(task_id: str, state: _contracts.JsonObject) -> _contracts.JsonObject:
    return {
        "task_id": task_id,
        "status": "REJECTED_UNKNOWN_TASK",
        "accepted": False,
        "missing_evidence": ["known_task_id"],
        "invalid_substitutes": [],
        "required_actions": ["Use a task id listed in contract.tasks."],
        "state": state,
    }


def _ensure_state_task(
    state: _contracts.JsonObject,
    task: _contracts.JsonObject,
) -> _contracts.JsonObject:
    if "tasks" not in state:
        tasks_value: _contracts.JsonValue = {}
        state["tasks"] = tasks_value
    else:
        tasks_value = state["tasks"]
        if not isinstance(tasks_value, dict):
            raise TypeError("goal state tasks must be an object")
    tasks = cast(_contracts.JsonObject, tasks_value)
    task_id = task.get("id")
    if not isinstance(task_id, str):
        raise TypeError("goal task id must be a string")
    # Legacy setdefault evaluated this default eagerly, including when state
    # already contained the task; preserve that non-init exception ordering.
    task_ordinal = task["ordinal"]
    task_description = task["description"]
    if task_id in tasks:
        existing = tasks[task_id]
        if not isinstance(existing, dict):
            raise TypeError("goal state task must be an object")
        return cast(_contracts.JsonObject, existing)
    task_state: _contracts.JsonObject = {
        "ordinal": task_ordinal,
        "description": task_description,
        "status": "pending",
        "attempts": [],
        "accepted_evidence": None,
        "last_rejection": None,
    }
    tasks[task_id] = task_state
    return task_state


def _refresh_state_status(state: dict[str, Any]) -> None:
    tasks = dict(state.get("tasks") or {})
    if tasks and all(task.get("status") == "complete" for task in tasks.values()):
        state["status"] = "complete"
    else:
        state["status"] = "active"
