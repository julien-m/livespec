"""Bind resolved native review identity before saving a command goal (078 FR-009)."""

from __future__ import annotations

from pathlib import Path

import typer

from .goal_contracts import GoalContract, compile_command_goal


def bind_review_model(
    goal: GoalContract, project_root: Path, livespec_root: Path, feature: str | None
) -> GoalContract:
    """Resolve review identity before locking a goal, never from a later receipt."""
    if not any(
        task.get("evidence_kind") == "review"
        or "acceptance_review_receipt_path" in task.get("required_evidence", [])
        or "spec_review_receipt_path" in task.get("required_evidence", [])
        for task in goal.payload["tasks"]
    ):
        return goal
    from .semantic.review_files import current_review_model

    flags = list(goal.payload.get("normalized_flags") or [])
    supplied = next((flag.split("=", 1)[1] for flag in flags if flag.startswith("--model=")), "")
    model = current_review_model(project_root, supplied)
    if model in {"", "default", "unknown"}:
        typer.echo(
            "goal render blocked: reviewer_model_unresolved — resolve the active runtime model "
            "and forward it internally with --flags '--model=<actual-model>' before goal lock",
            err=True,
        )
        raise typer.Exit(2)
    if supplied:
        return goal
    return compile_command_goal(
        goal.command,
        project_root=project_root,
        livespec_root=livespec_root,
        feature=feature,
        flags=[*flags, f"--model={model}"],
    )
