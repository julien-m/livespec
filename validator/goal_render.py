"""Goal render responsibilities behind the public contract facade."""

from __future__ import annotations

import json
from typing import Any

from . import goal_contracts as _contracts


# @spec FR-003: Mirror the canonical project root in saved contracts
#   — .specs/features/076-spec-init-goal-bootstrap/spec.md#fr-003
def render_goal_contract_file(goal: _contracts.GoalContract) -> str:
    """Render the JSON contract consumed by ``livespec goal prove``.

    Args:
        goal: Compiled deterministic goal contract.

    Returns:
        Pretty-printed JSON contract text. The function has no filesystem
        side effects; callers decide where to persist it.
    """
    payload = goal.payload
    contract = {
        "schema_version": _contracts.GOAL_CONTRACT_VERSION,
        "evidence_policy_version": payload.get("evidence_policy_version"),
        "goal_hash": goal.goal_hash,
        "command": goal.command,
        "feature": payload.get("feature"),
        "normalized_flags": list(payload.get("normalized_flags") or []),
        "mode": payload["mode"],
        "goal_requirement": payload["goal_requirement"],
        "stop_condition": payload["stop_condition"],
        "worker_may_mark_tasks_complete": False,
        "rules": payload["rules"],
        "tasks": payload["tasks"],
        "checklist": [*payload["execution_tasks"], *payload["definition_of_done"]],
        "runtime_context": payload["runtime_context"],
        "hooks": payload["hooks"],
        **({"qe_analysis": payload["qe_analysis"]} if "qe_analysis" in payload else {}),
        "canonical": payload,
        "canonical_json": goal.canonical_json,
    }
    if goal.command == "spec-init":
        contract["project_root"] = payload["project_root"]
    elif goal.project_root is not None:
        # Not hashed: lets prove/archive recompile the goal against the same project.
        contract["compiled_project_root"] = goal.project_root
    return json.dumps(contract, indent=2, sort_keys=True, ensure_ascii=False)


__all__ = [
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
        pending count; blocked tasks are appended when present.
    """
    tasks = dict(state.get("tasks") or {})
    total = len(tasks)
    complete = sum(1 for task in tasks.values() if task.get("status") == "complete")
    pending = total - complete
    status = state.get("status") or "unknown"
    line = (
        f"goal_hash:{state.get('goal_hash', 'unknown')} | "
        f"status:{status} | complete:{complete}/{total} | pending:{pending}"
    )
    blocked = [
        task_id
        for task_id, task in tasks.items()
        if task.get("status") != "complete" and task.get("blocked")
    ]
    if blocked:
        line += f" | blocked:{len(blocked)} ({', '.join(blocked)})"
    return line


def render_goal_objective(goal: _contracts.GoalContract) -> str:
    """Render stable human text from the canonical payload."""
    payload = goal.payload
    stop = payload["stop_condition"]
    lines = [
        f"Goal hash: {goal.goal_hash}",
        f"Command: {payload['command']}",
        f"Feature: {payload['feature'] or 'none'}",
        f"Flags: {', '.join(payload['normalized_flags']) or 'none'}",
        f"Goal: {payload['goal_requirement']}",
        f"Stop condition: {stop['display']}",
        "",
        "Required proofs (in order):",
    ]
    lines.extend(f"  {task['ordinal']:>2}. {task['id']}" for task in payload["tasks"])
    checklist = [*payload["execution_tasks"], *payload["definition_of_done"]]
    if checklist:
        lines.append("")
        lines.append("Checklist (indicative, not proven task by task):")
        lines.extend(f"- {item}" for item in checklist)
    hooks = payload.get("hooks")
    before_hook = hooks.get("before") if isinstance(hooks, dict) else None
    if isinstance(before_hook, dict) and before_hook.get("non_empty"):
        lines.append("")
        lines.append(f"Hook context to apply: {before_hook.get('command')}")
    # @spec FR-002: Surface native QE context in rendered objective
    #   — .specs/features/071-qe-analysis-native-module/spec.md#fr-002
    qe_analysis = payload.get("qe_analysis")
    if isinstance(qe_analysis, dict) and qe_analysis.get("native") is True:
        lines.append("")
        lines.append(
            f"Native QE Analysis: {qe_analysis.get('source_path')} (user hooks: extension_only)"
        )
    return "\n".join(lines)
