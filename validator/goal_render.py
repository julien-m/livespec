"""Goal render responsibilities behind the public contract facade."""

from __future__ import annotations

import json
from typing import Any, cast

from . import goal_contracts as _contracts


# @spec FR-003: Mirror the canonical project root in saved contracts
#   — .specs/features/076-spec-init-goal-bootstrap/spec.md#fr-003
def render_goal_contract_file(goal: _contracts.GoalContract) -> str:
    """Render the immutable JSON contract consumed by ``livespec goal prove``.

    Args:
        goal: Compiled deterministic goal contract.

    Returns:
        Pretty-printed JSON contract text. The function has no filesystem
        side effects; callers decide where to persist it.
    """
    contract = {
        "schema_version": _contracts.GOAL_CONTRACT_VERSION,
        "evidence_policy_version": goal.payload.get("evidence_policy_version"),
        "goal_hash": goal.goal_hash,
        "command": goal.command,
        "feature": goal.payload.get("feature"),
        "normalized_flags": list(goal.payload.get("normalized_flags") or []),
        "mode": goal.payload["mode"],
        "worker_may_mark_tasks_complete": False,
        "rules": goal.payload["rules"],
        "tasks": goal.payload["tasks"],
        "definition_of_done": goal.payload["definition_of_done"],
        "runtime_context": goal.payload["runtime_context"],
        "hooks": goal.payload["hooks"],
        **({"qe_analysis": goal.payload["qe_analysis"]} if "qe_analysis" in goal.payload else {}),
        "canonical": goal.payload,
        "canonical_json": goal.canonical_json,
    }
    if goal.command == "spec-init":
        contract["project_root"] = goal.payload["project_root"]
    return json.dumps(contract, indent=2, sort_keys=True, ensure_ascii=False)


__all__ = [
    "_goal_objective_context",
    "render_goal_contract_file",
    "render_goal_objective",
    "render_goal_state_file",
    "render_goal_status",
]


def render_goal_state_file(goal: _contracts.GoalContract) -> str:
    """Render the mutable JSON state file; only ``goal prove`` updates it.

    Args:
        goal: Compiled deterministic goal contract.

    Returns:
        Pretty-printed JSON state initialized with every task pending. The
        function has no filesystem side effects; callers persist the text.
    """
    state: dict[str, Any] = {
        "schema_version": _contracts.GOAL_CONTRACT_VERSION,
        "goal_hash": goal.goal_hash,
        "command": goal.command,
        "status": "active",
        "tasks": {
            task["id"]: {
                "ordinal": task["ordinal"],
                "description": task["description"],
                "status": "pending",
                "attempts": [],
                "accepted_evidence": None,
                "last_rejection": None,
            }
            for task in goal.payload["tasks"]
        },
    }
    return json.dumps(state, indent=2, sort_keys=True, ensure_ascii=False)


def render_goal_status(state: dict[str, Any]) -> str:
    """Render a compact status summary for a goal state JSON object.

    Args:
        state: Mutable goal state JSON object.

    Returns:
        One-line status summary with goal hash, status, completed count, and
        pending count.
    """
    tasks = dict(state.get("tasks") or {})
    total = len(tasks)
    complete = sum(1 for task in tasks.values() if task.get("status") == "complete")
    pending = total - complete
    status = state.get("status") or "unknown"
    return (
        f"goal_hash:{state.get('goal_hash', 'unknown')} | "
        f"status:{status} | complete:{complete}/{total} | pending:{pending}"
    )


def render_goal_objective(goal: _contracts.GoalContract) -> str:
    """Render stable human text from the canonical payload."""
    payload = goal.payload
    lines = [
        f"Goal hash: {goal.goal_hash}",
        f"Command: {payload['command']}",
        f"Feature: {payload['feature'] or 'none'}",
        f"Flags: {', '.join(payload['normalized_flags']) or 'none'}",
    ]
    lines.extend(_contracts._goal_objective_context(payload))
    lines.append("Definition of Done:")
    definition_of_done = list(payload["definition_of_done"])
    if definition_of_done:
        lines.extend(f"- {item}" for item in definition_of_done)
    else:
        lines.append("- No Definition of Done found in command skill; use expectations only.")
    conventions = payload.get("conventions", {})
    selected_domains = list(conventions.get("selected_domains") or [])
    if selected_domains:
        lines.append("")
        lines.append("Conventions to apply:")
        for domain in selected_domains:
            lines.append(f"- {domain['name']}: {', '.join(domain['paths'])}")
    sections = payload["expectation_sections"]
    for label, key in (
        ("Preconditions", "preconditions"),
        ("Filesystem effects", "filesystem_effects"),
        ("Produced artifacts", "produced_artifacts"),
        ("Post-run checks", "post_run_checks"),
    ):
        values = list(sections[key])
        if not values:
            continue
        lines.append("")
        lines.append(f"{label}:")
        lines.extend(f"- {value}" for value in values)
    lines.append("")
    lines.append("Verification rules:")
    for rule in payload["verify_rules"]["must"]:
        lines.append(f"- must {rule['kind']}: {rule['payload']}")
    for rule in payload["verify_rules"]["must_not"]:
        lines.append(f"- must_not {rule['kind']}: {rule['payload']}")
    return "\n".join(lines)


def _goal_objective_context(payload: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    execution_tasks = list(payload.get("execution_tasks") or [])
    if execution_tasks:
        lines.append("")
        lines.append("Execution tasks (in order):")
        for i, task in enumerate(execution_tasks, 1):
            lines.append(f"  {i:>2}. {task}")
    tasks = list(payload.get("tasks") or [])
    hooks = payload.get("hooks")
    if isinstance(hooks, dict):
        before_hook = hooks.get("before")
        if isinstance(before_hook, dict) and before_hook.get("non_empty"):
            lines.append("")
            lines.append("Hook context to apply:")
            lines.append(f"- before: {before_hook.get('command')}")
            lines.append(f"- sha256: {before_hook.get('context_sha256')}")
    # @spec FR-002: Surface native QE context in rendered objective
    #   — .specs/features/071-qe-analysis-native-module/spec.md#fr-002
    qe_analysis = payload.get("qe_analysis")
    if isinstance(qe_analysis, dict) and qe_analysis.get("native") is True:
        lines.append("")
        lines.append("Native QE Analysis:")
        lines.append(f"- source: {qe_analysis.get('source_path')}")
        lines.append("- user hooks: extension_only")
    # @spec FR-005: Render task-level convention replay
    #   — .specs/features/053-goal-tasks-replay-required-conventions-per-step/spec.md#fr-005
    convention_tasks = [
        task for task in tasks if isinstance(task, dict) and task.get("required_conventions")
    ]
    if convention_tasks:
        lines.append("")
        lines.append("Task-level convention replay:")
        for task in convention_tasks:
            required = cast(dict[str, Any], task["required_conventions"])
            domains = ", ".join(cast(list[str], required.get("domains") or []))
            sources = ", ".join(cast(list[str], required.get("source_paths") or []))
            lines.append(f"- {task['id']}: read_apply domains [{domains}] from {sources}")
    lines.append("")
    return lines
