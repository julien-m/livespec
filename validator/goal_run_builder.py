"""Build typed RunArtifact payloads from validated goal snapshots."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .evidence_policy import contract_evidence_policy, typed_evidence_missing
from .goal_json import JsonObject, JsonValue, copy_json_object, is_json_value
from .outcome import Outcome
from .run_receipts import ReceiptCheck, verify_evidence_receipts
from .verify_output import evaluate_rules

ARCHIVE_RUN_TASK_ID = "archive.run"


@dataclass(frozen=True)
class RunArtifactBuildInput:
    """Carry validated inputs needed to assemble one run artifact."""

    contract: Mapping[str, object]
    state: Mapping[str, object]
    command: str
    contract_hash: str
    project_root: Path
    feature: str | None
    resolved_feature: str | None
    exit_code: int | None
    stdout_text: str | None
    stderr_text: str | None
    timestamp: datetime
    schema_version: str


def build_run_artifact(inputs: RunArtifactBuildInput) -> tuple[JsonObject, Outcome]:
    """Build and evaluate one typed artifact.

    Args:
        inputs: Validated immutable build inputs.

    Returns:
        The closed JSON artifact and evaluated outcome.

    Raises:
        ValueError: If direct API input contains a non-JSON business value.
    """
    flags = [str(flag) for flag in _list_of(inputs.contract.get("normalized_flags"))]
    goal_snapshot = _goal_snapshot(inputs.state)
    task_objects = _task_objects(goal_snapshot)
    receipts, declarations = _task_receipts(inputs, flags, task_objects)
    evidence_errors = _archived_task_evidence_errors(inputs, task_objects, declarations)
    artifact = _artifact_envelope(inputs, flags, goal_snapshot)
    if evidence_errors:
        artifact["evidence_errors"] = evidence_errors
    artifact["receipts"] = [
        _require_json_object(receipt.to_dict(), "receipt") for receipt in receipts
    ]
    if contract_evidence_policy(inputs.contract) == "2":
        from .acceptance_evidence import archived_policy2_evidence_errors

        errors = archived_policy2_evidence_errors(artifact, inputs.project_root)
        if errors:
            evidence_errors["policy2"] = list(errors)
            artifact["evidence_errors"] = evidence_errors
    verify_rules = _contract_verify_rules(inputs.contract)
    artifact["verify_rules"] = verify_rules
    report = evaluate_rules(
        verify_rules,
        artifact=artifact,
        active_flags=flags,
        feature=inputs.resolved_feature,
        project_root=inputs.project_root,
        goal_incomplete=goal_tasks_incomplete(task_objects),
        receipt_error=bool(evidence_errors) or any(not receipt.verified for receipt in receipts),
    )
    artifact["verify_result"] = _require_json_object(report.to_dict(), "verify result")
    return artifact, report.outcome


def _archived_task_evidence_errors(
    inputs: RunArtifactBuildInput,
    task_objects: list[JsonObject],
    declarations: Mapping[str, JsonObject],
) -> JsonObject:
    """Revalidate completed typed obligations rather than trust editable completion flags."""
    evidence_errors: JsonObject = {}
    if contract_evidence_policy(inputs.contract) is not None:
        for task in task_objects:
            task_id = str(task.get("id"))
            if task_id == ARCHIVE_RUN_TASK_ID or task.get("status") != "complete":
                continue
            declaration = declarations.get(task_id)
            accepted = task.get("accepted_evidence")
            missing = typed_evidence_missing(
                declaration if isinstance(declaration, dict) else {},
                accepted if isinstance(accepted, dict) else {},
                contract=inputs.contract,
                project_root=inputs.project_root,
            )
            if missing:
                evidence_errors[task_id] = list(missing)
    return evidence_errors


def _artifact_envelope(
    inputs: RunArtifactBuildInput,
    flags: list[str],
    goal_snapshot: JsonObject,
) -> JsonObject:
    flag_values: list[JsonValue] = []
    flag_values.extend(flags)
    artifact: JsonObject = {
        "schema_version": inputs.schema_version,
        "evidence_policy_version": str(contract_evidence_policy(inputs.contract) or "legacy"),
        "goal_hash": inputs.contract_hash,
        "command": inputs.command,
        "feature": inputs.resolved_feature,
        "flags": flag_values,
        "exit_code": inputs.exit_code,
        "timestamp": inputs.timestamp.isoformat(),
        "goal": goal_snapshot,
    }
    if contract_evidence_policy(inputs.contract) == "2":
        artifact["evidence_contract"] = copy_json_object(inputs.contract)
    if inputs.stdout_text is not None:
        artifact["stdout"] = inputs.stdout_text
    if inputs.stderr_text is not None:
        artifact["stderr"] = inputs.stderr_text
    return artifact


def _task_objects(goal_snapshot: JsonObject) -> list[JsonObject]:
    raw_tasks = goal_snapshot["tasks"]
    return (
        [task for task in raw_tasks if isinstance(task, dict)]
        if isinstance(raw_tasks, list)
        else []
    )


def goal_tasks_incomplete(tasks: Sequence[Mapping[str, object]]) -> bool:
    """Return whether a required goal task other than ``archive.run`` is pending.

    Args:
        tasks: Goal task snapshots containing ``id`` and ``status``.

    Returns:
        True when at least one non-archive task is not complete.
    """
    return any(
        task.get("status") != "complete" for task in tasks if task.get("id") != ARCHIVE_RUN_TASK_ID
    )


def _goal_snapshot(state: Mapping[str, object]) -> JsonObject:
    tasks_raw = state.get("tasks")
    tasks_map: Mapping[str, object] = tasks_raw if isinstance(tasks_raw, Mapping) else {}
    tasks: list[JsonObject] = []
    for task_id, task_obj in tasks_map.items():
        task: Mapping[str, object] = task_obj if isinstance(task_obj, Mapping) else {}
        ordinal_raw = task.get("ordinal")
        tasks.append(
            {
                "id": str(task_id),
                "ordinal": ordinal_raw if isinstance(ordinal_raw, int) else 0,
                "status": str(task.get("status", "pending")),
                "accepted_evidence": _require_json_value(
                    task.get("accepted_evidence"), "accepted evidence"
                ),
            }
        )
    tasks.sort(key=_task_sort_key)
    task_values: list[JsonValue] = []
    task_values.extend(tasks)
    return {"status": str(state.get("status", "unknown")), "tasks": task_values}


def _task_sort_key(task: JsonObject) -> tuple[int, str]:
    ordinal = task.get("ordinal")
    task_id = task.get("id")
    return ordinal if isinstance(ordinal, int) else 0, str(task_id)


def _contract_verify_rules(contract: Mapping[str, object]) -> JsonObject:
    canonical = contract.get("canonical")
    if isinstance(canonical, dict):
        rules = canonical.get("verify_rules")
        if isinstance(rules, dict):
            return _require_json_object(rules, "canonical verify rules")
    rules = contract.get("verify_rules")
    if isinstance(rules, dict):
        return _require_json_object(rules, "verify rules")
    return {"must": [], "may": [], "must_not": [], "when": []}


def _list_of(value: object) -> list[object]:
    return list(value) if isinstance(value, list) else []


def _require_json_object(value: object, label: str) -> JsonObject:
    document = copy_json_object(value)
    if document is None:
        raise ValueError(f"{label} is not a JSON object")
    return document


def _require_json_value(value: object, label: str) -> JsonValue:
    if not is_json_value(value):
        raise ValueError(f"{label} is not JSON-compatible")
    return value


__all__ = [
    "ARCHIVE_RUN_TASK_ID",
    "RunArtifactBuildInput",
    "build_run_artifact",
    "goal_tasks_incomplete",
]


def _task_receipts(
    inputs: RunArtifactBuildInput,
    flags: list[str],
    task_objects: list[JsonObject],
) -> tuple[list[ReceiptCheck], dict[str, JsonObject]]:
    review_budget = next(
        (flag.split("=", 1)[1] for flag in flags if flag.startswith("--review-max-chars=")), None
    )
    declarations = {
        str(task.get("id")): task
        for task in _list_of(inputs.contract.get("tasks"))
        if isinstance(task, dict)
    }
    receipt_tasks = [
        {
            **task,
            "expected_evidence": declarations.get(str(task.get("id")), {}).get(
                "expected_evidence", {}
            ),
            "evidence_expected_outcome": declarations.get(str(task.get("id")), {}).get(
                "evidence_expected_outcome", ""
            ),
        }
        for task in task_objects
    ]
    receipts = verify_evidence_receipts(
        receipt_tasks,
        project_root=inputs.project_root,
        feature=inputs.feature,
        requirement_feature=inputs.resolved_feature,
        evidence_policy="2" if contract_evidence_policy(inputs.contract) == "2" else "1",
        review_max_chars=int(review_budget) if review_budget else None,
        reviewer_model=next(
            (flag.split("=", 1)[1] for flag in flags if flag.startswith("--model=")), ""
        ),
    )
    return receipts, declarations
