# @spec(FR-005)

"""Recompile drifted goal contracts while keeping still-valid evidence (feature 081)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, cast

import typer

from .evidence_policy import EVIDENCE_POLICY_VERSION
from .exceptions import ExpectationsInvalid, ExpectationsMissing, OverrideMalformed
from .goal_cli_inputs import ResolvedGoalInputs
from .goal_cli_output import archive_blocked, read_json_object, write_json_text_atomically
from .goal_contracts import (
    GOAL_CONTRACT_VERSION,
    GoalContract,
    compile_command_goal,
    render_goal_contract_file,
    render_goal_state_file,
)
from .goal_json import JsonObject
from .goal_outcome import OUTCOME_TASK_ID
from .goal_proof import _refresh_state_status, _validate_task_proof
from .goal_review_identity import bind_review_model, flag_budget

__all__ = [
    "GoalRecompileError",
    "RefreshedGoal",
    "compile_goal",
    "refresh_for_cli",
    "refresh_goal",
    "refresh_saved_pair",
    "reusable_state",
]


class GoalRecompileError(Exception):
    """Report a current contract whose inputs can no longer be compiled."""


@dataclass(frozen=True)
class RefreshedGoal:
    """Carry the current contract/state pair and an optional recompilation report."""

    contract: JsonObject
    state: JsonObject
    report: JsonObject | None


def compile_goal(
    command: str,
    *,
    project_root: Path,
    livespec_root: Path,
    feature: str | None,
    flags: list[str] | tuple[str, ...] | str | None,
) -> GoalContract:
    """Compile a goal and bind the review identity exactly like ``goal render``.

    Raises:
        ReviewIdentityError: Malformed budget flag or unresolved identity (feature 093).
    """
    flag_budget(flags)  # refuse a malformed budget before the payload parses it
    goal = compile_command_goal(
        command,
        project_root=project_root,
        livespec_root=livespec_root,
        feature=feature,
        flags=flags,
    )
    return bind_review_model(goal, project_root, livespec_root, feature)


# @spec FR-005: Recoverable contracts — .specs/features/081-lightweight-outcome-goals/spec.md#fr-005
def refresh_goal(
    contract: JsonObject,
    state: JsonObject,
    *,
    project_root: Path,
    livespec_root: Path,
) -> RefreshedGoal:
    """Recompile from current inputs; on drift, carry forward evidence that still validates.

    Args:
        contract: Saved contract JSON.
        state: Saved mutable state JSON.
        project_root: Authoritative project root of the pair.
        livespec_root: LiveSpec checkout providing skills and expectations.

    Returns:
        The unchanged pair when inputs did not drift (or the command no longer exists),
        otherwise the recompiled pair plus a report with old/new hashes, carried and reset tasks.

    Raises:
        GoalRecompileError: If current inputs exist but fail to compile; stale obligations
            are never certified.
    """
    if not _recompilable(contract, project_root):
        return RefreshedGoal(contract, state, None)
    feature = contract.get("feature")
    try:
        goal = compile_goal(
            str(contract["command"]),
            project_root=project_root,
            livespec_root=livespec_root,
            feature=feature if isinstance(feature, str) else None,
            flags=[str(flag) for flag in cast(list[object], contract["normalized_flags"])],
        )
    except ExpectationsMissing:
        return RefreshedGoal(contract, state, None)  # command removed: nothing to recompile
    except (ExpectationsInvalid, OverrideMalformed, ValueError, OSError) as exc:
        raise GoalRecompileError(f"recompile failed: {exc}") from exc
    if goal.goal_hash == contract.get("goal_hash"):
        return RefreshedGoal(contract, state, None)
    new_contract = cast(JsonObject, json.loads(render_goal_contract_file(goal)))
    new_state = cast(JsonObject, json.loads(render_goal_state_file(goal)))
    carried, reset = _carry_evidence(new_contract, new_state, state, project_root)
    _refresh_state_status(cast(dict[str, Any], new_state))
    report: JsonObject = {
        "from_hash": str(contract.get("goal_hash")),
        "to_hash": goal.goal_hash,
        "carried": cast(Any, carried),
        "reset": cast(Any, reset),
    }
    new_state["recompiled_from"] = str(contract.get("goal_hash"))
    return RefreshedGoal(new_contract, new_state, report)


def _recompilable(contract: Mapping[str, object], project_root: Path) -> bool:
    """Historical contracts (older schema or evidence policy) keep their obligations untouched."""
    canonical = contract.get("canonical")
    return (
        isinstance(contract.get("command"), str)
        and isinstance(contract.get("normalized_flags"), list)
        and isinstance(canonical, Mapping)
        and canonical.get("schema_version") == GOAL_CONTRACT_VERSION
        and canonical.get("evidence_policy_version") == EVIDENCE_POLICY_VERSION
        and _same_project(contract, project_root)
    )


def _same_project(contract: Mapping[str, object], project_root: Path) -> bool:
    recorded = contract.get("project_root", contract.get("compiled_project_root"))
    return isinstance(recorded, str) and recorded == project_root.resolve().as_posix()


def _carry_evidence(
    contract: JsonObject, state: JsonObject, old_state: Mapping[str, object], project_root: Path
) -> tuple[list[str], list[str]]:
    old_tasks = old_state.get("tasks")
    old_tasks = old_tasks if isinstance(old_tasks, Mapping) else {}
    new_tasks = cast(dict[str, dict[str, Any]], state["tasks"])
    carried: list[str] = []
    reset: list[str] = []
    for task in cast(list[dict[str, Any]], contract["tasks"]):
        old = old_tasks.get(task["id"])
        if not isinstance(old, Mapping) or old.get("status") != "complete":
            continue
        evidence = old.get("accepted_evidence")
        # The outcome is re-verified at proof time; never replay it against new inputs.
        if task["id"] == OUTCOME_TASK_ID or not isinstance(evidence, Mapping):
            reset.append(task["id"])
            continue
        proof = _validate_task_proof(task, dict(evidence), contract, project_root)
        if proof["accepted"]:
            attempt = {
                "status": "ACCEPTED",
                "evidence": dict(evidence),
                "missing_evidence": [],
                "invalid_substitutes": [],
                "carried_over": True,
            }
            new_tasks[task["id"]].update(
                status="complete", accepted_evidence=dict(evidence), attempts=[attempt]
            )
            carried.append(task["id"])
        else:
            reset.append(task["id"])
    return carried, reset


def refresh_saved_pair(
    inputs: ResolvedGoalInputs, *, livespec_root: Path
) -> tuple[ResolvedGoalInputs, JsonObject | None]:
    """Recompile a drifted pair in place so the agent keeps its contract/state paths."""
    refreshed = refresh_goal(
        inputs.contract,
        inputs.state,
        project_root=inputs.project_root,
        livespec_root=livespec_root,
    )
    if refreshed.report is None or inputs.contract_path is None:
        return inputs, None
    write_json_text_atomically(
        inputs.contract_path,
        json.dumps(refreshed.contract, indent=2, sort_keys=True, ensure_ascii=False),
    )
    write_json_text_atomically(
        inputs.state_path,
        json.dumps(refreshed.state, indent=2, sort_keys=True, ensure_ascii=False),
    )
    updated = replace(inputs, contract=refreshed.contract, state=refreshed.state)
    return updated, refreshed.report


def reusable_state(state_file: Path, goal_hash: str) -> bool:
    """Return whether a saved state for this exact goal hash exists (adopting a recompiled one)."""
    if not state_file.is_file():
        # A pair recompiled in place keeps its old file name; adopt its progress.
        for candidate in sorted(state_file.parent.glob("goal-*.state.json")):
            try:
                state = read_json_object(candidate)
            except (OSError, json.JSONDecodeError):
                continue
            if state.get("goal_hash") == goal_hash and isinstance(state.get("tasks"), dict):
                write_json_text_atomically(
                    state_file, json.dumps(state, indent=2, sort_keys=True, ensure_ascii=False)
                )
                return True
        return False
    try:
        state = read_json_object(state_file)
    except (OSError, json.JSONDecodeError):
        return False
    return state.get("goal_hash") == goal_hash and isinstance(state.get("tasks"), dict)


def refresh_for_cli(
    inputs: ResolvedGoalInputs, *, livespec_root: Path, operation: str, json_out: bool = False
) -> tuple[ResolvedGoalInputs, JsonObject | None]:
    """CLI boundary: refresh the pair, block on a failed recompile, announce archive recompiles.

    Raises:
        typer.Exit: With 2 when current inputs fail to compile.
    """
    try:
        updated, report = refresh_saved_pair(inputs, livespec_root=livespec_root)
    except GoalRecompileError as exc:
        if operation == "archive":
            raise archive_blocked(str(exc), json_out=json_out) from exc
        typer.echo(f"goal {operation} blocked: {exc}", err=True)
        raise typer.Exit(2) from exc
    if report is not None and operation == "archive":
        typer.echo(f"goal recompiled: {report['from_hash']} -> {report['to_hash']}", err=True)
    return updated, report
