# @spec(FR-001)
# @spec(FR-003)
# @spec(FR-006)
# @spec(FR-007)

"""Outcome-based goal scope, stop condition and bounded-retry policy (feature 081)."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

__all__ = [
    "CONVENTIONS_GATE_TASK_ID",
    "MAX_ATTEMPTS_PER_TASK",
    "OUTCOME_TASK_ID",
    "STOP_CONDITION_TIMEOUT_SECONDS",
    "conventions_gate_task",
    "goal_requirement",
    "outcome_task",
    "run_stop_condition",
    "stop_condition",
    "validate_outcome_evidence",
]

OUTCOME_TASK_ID = "outcome.verified"
CONVENTIONS_GATE_TASK_ID = "conventions.gate"
MAX_ATTEMPTS_PER_TASK = 3
# Bounds one structural validation; it never applies once the condition has passed.
STOP_CONDITION_TIMEOUT_SECONDS = 300.0
# Commands whose auto mode is a long autonomous run (spec-ship and spec-implement are handled
# separately); short commands such as spec-propose --auto stay optional.
_AUTO_FLAGS: dict[str, frozenset[str]] = {
    "spec-feature": frozenset({"--auto", "-a"}),
    "spec-init": frozenset({"--auto", "-a"}),
    "spec-specify": frozenset({"--auto"}),
    "spec-plan": frozenset({"--auto"}),
    "spec-test": frozenset({"--auto"}),
    "spec-fix": frozenset({"--auto"}),
}
_INTERACTIVE_IMPLEMENT_FLAGS = frozenset({"--step", "-s", "--dry-run", "-d"})


def _flag_names(flags: list[str] | tuple[str, ...]) -> set[str]:
    return {token.split("=", 1)[0] for token in flags if token.startswith("-")}


# @spec FR-003: Goal scope
#   — .specs/features/081-lightweight-outcome-goals/spec.md#fr-003
def goal_requirement(command: str, flags: list[str] | tuple[str, ...]) -> str:
    """Return ``required`` only for autonomous long runs, otherwise ``optional``.

    Args:
        command: Canonical command name.
        flags: Normalized active flags.

    Returns:
        ``required`` or ``optional``.
    """
    names = _flag_names(flags)
    if command == "spec-ship":
        return "required"
    if command == "spec-init" and names & {"--dry-run", "-d"}:
        return "optional"  # preview runs write nothing
    if command == "spec-implement":
        return "optional" if names & _INTERACTIVE_IMPLEMENT_FLAGS else "required"
    if names & _AUTO_FLAGS.get(command, frozenset()):
        return "required"
    return "optional"


# @spec FR-001: One executable stop condition
#   — .specs/features/081-lightweight-outcome-goals/spec.md#fr-001
def stop_condition(
    command: str, feature: str | None, flags: list[str] | tuple[str, ...], project_root: Path
) -> dict[str, Any]:
    """Derive the single executable completion check for one command invocation.

    Args:
        command: Canonical command name.
        feature: Resolved feature slug, when the command is feature-scoped.
        flags: Normalized active flags.
        project_root: Project whose state the condition verifies.

    Returns:
        JSON mapping with ``argv`` (starting with ``livespec``), ``display`` and ``scope``.
    """
    names = _flag_names(flags)
    if command == "spec-init" and "--from-code" in names and names & {"--auto", "-a"}:
        argv = ["livespec", "init-from-code", "--verify-only"]
        scope = "project"
    elif feature:
        # Never weaken a supplied feature to project scope: a missing feature fails the check.
        argv = ["livespec", "validate", f".specs/features/{feature}"]
        scope = "feature"
    else:
        argv = ["livespec", "validate"]
        scope = "project"
    return {"argv": argv, "display": " ".join(argv) + " exits 0", "scope": scope}


def outcome_task(*, command: str, ordinal: int, condition: Mapping[str, Any]) -> dict[str, Any]:
    """Build the final outcome task proven by the goal running the stop condition."""
    return {
        "id": OUTCOME_TASK_ID,
        "ordinal": ordinal,
        "category": "injected",
        "description": f"Verify the outcome: `{condition['display']}`",
        "required_evidence": ["stop_condition_exit_zero", "observable_output_or_artifact"],
        "invalid_substitutes": ["agent_declared_exit_code", "prose_completion_claim"],
        "repair_if_missing": [
            "fix what the stop condition reports, then prove outcome.verified again",
            "after three failed attempts, report BLOCKED with what was tried and what is missing",
        ],
        "completion_actor": "goal",
        "expected_evidence": {"command": command, "stop_condition": dict(condition)},
    }


def conventions_gate_task(*, command: str, ordinal: int) -> dict[str, Any]:
    """Build the single feature-scope conventions receipt task (replaces per-task proofs)."""
    return {
        "id": CONVENTIONS_GATE_TASK_ID,
        "ordinal": ordinal,
        "category": "injected",
        "description": (
            "Run `livespec conventions verify --json --feature <slug>` once at feature scope "
            "and submit the PASS receipt"
        ),
        "required_evidence": ["conventions_receipt_path"],
        "invalid_substitutes": ["per_task_convention_claims"],
        "repair_if_missing": [
            "run `livespec conventions verify --json --feature <slug>` and submit "
            "`conventions_receipt_path`",
        ],
        "completion_actor": "goal",
        "expected_evidence": {"command": command, "feature_slug": None},
    }


def run_stop_condition(argv: list[str], project_root: Path) -> tuple[int, str]:
    """Execute a compiled ``livespec`` stop condition with the current interpreter.

    Args:
        argv: Compiled argv whose first token is ``livespec``.
        project_root: Working directory for the check.

    Returns:
        Exit code and combined output; launch failures return exit 127.
    """
    # -P excludes the consumer cwd from module lookup without changing its file context.
    if argv[:2] == ["livespec", "init-from-code"]:
        command = [sys.executable, "-P", "-B", "-m", "validator.init_from_code", ".", *argv[2:]]
    else:
        command = [sys.executable, "-P", "-m", "validator.cli", *argv[1:]]
    # Run the same validator package as the caller, not whichever copy the cwd would import.
    package_root = str(Path(__file__).resolve().parents[1])
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(
            [package_root, *filter(None, [os.environ.get("PYTHONPATH")])]
        ),
    }
    try:
        completed = subprocess.run(
            command,
            cwd=project_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=STOP_CONDITION_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, f"stop condition could not complete: {exc}"
    return completed.returncode, (completed.stdout + completed.stderr).strip()


def validate_outcome_evidence(
    task: Mapping[str, Any], evidence: Mapping[str, Any], project_root: Path | None
) -> dict[str, Any]:
    """Verify the outcome independently; the agent's declared result is never trusted."""
    expected = task.get("expected_evidence")
    condition = expected.get("stop_condition") if isinstance(expected, Mapping) else None
    argv = condition.get("argv") if isinstance(condition, Mapping) else None
    missing: list[str] = []
    record: dict[str, Any] = {}
    if (
        not isinstance(argv, list)
        or not argv
        or argv[0] != "livespec"
        or not all(isinstance(token, str) for token in argv)
    ):
        missing.append("compiled_stop_condition")
    elif project_root is None:
        missing.append("project_root_for_stop_condition")
    else:
        exit_code, output = run_stop_condition(list(argv), project_root)
        record = {"exit_code": exit_code, "output_tail": output[-2000:]}
        if exit_code != 0:
            missing.append("stop_condition_exit_zero")
        if not output and not _existing_artifact(evidence, project_root):
            missing.append("observable_output_or_artifact")
    return {
        "status": "REJECTED_NEEDS_ACTION" if missing else "ACCEPTED",
        "accepted": not missing,
        "missing_evidence": missing,
        "invalid_substitutes": [],
        "required_actions": list(task.get("repair_if_missing") or []),
        "observed": record,
    }


def _existing_artifact(evidence: Mapping[str, Any], project_root: Path) -> bool:
    """Accept only an existing in-project artifact when the check prints nothing."""
    for key in ("artifact", "path", "paths", "files"):
        values = evidence.get(key)
        for value in values if isinstance(values, list) else [values]:
            if not isinstance(value, str) or not value:
                continue
            candidate = (project_root / value).resolve()
            if candidate.is_relative_to(project_root.resolve()) and candidate.is_file():
                return True
    return False
