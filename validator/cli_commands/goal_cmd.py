"""``livespec goal`` — render and verify deterministic command goals.

# @spec FR-008, FR-009
#   — .specs/features/052-deterministic-command-goal-contracts/spec.md
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import typer

from ..exceptions import ExpectationsInvalid, ExpectationsMissing, OverrideMalformed
from ..goal_contracts import compile_command_goal, render_goal_task_file
from ..specs_utils import find_specs_root

goal_app = typer.Typer(name="goal", help="Render command goal contracts.")

COMMAND_ARGUMENT = typer.Argument(..., help="Command name or alias.")
FEATURE_OPTION = typer.Option(None, "--feature", help="Resolved feature slug.")
FLAGS_OPTION = typer.Option("", "--flags", help="Space-separated active flags.")
JSON_OPTION = typer.Option(False, "--json", help="Emit JSON.")
SAVE_OPTION = typer.Option(
    False,
    "--save",
    help="Save task file to $TMPDIR/livespec-goals/goal-<cmd>-<hash8>.md and emit hash+path on stdout.",
)


@goal_app.command("render")
def render_cmd(
    command: str = COMMAND_ARGUMENT,
    feature: str | None = FEATURE_OPTION,
    flags: str = FLAGS_OPTION,
    json_out: bool = JSON_OPTION,
    save: bool = SAVE_OPTION,
) -> None:
    """Render a deterministic goal for a command invocation."""
    project_root = _project_root()
    livespec_root = _detect_livespec_root()
    try:
        goal = compile_command_goal(
            command,
            project_root=project_root,
            livespec_root=livespec_root,
            feature=feature,
            flags=flags,
        )
    except (ExpectationsInvalid, ExpectationsMissing, OverrideMalformed) as exc:
        typer.echo(f"goal render blocked: {exc}", err=True)
        raise typer.Exit(2) from exc
    if save:
        goals_dir = Path(tempfile.gettempdir()) / "livespec-goals"
        goals_dir.mkdir(parents=True, exist_ok=True)
        task_file = goals_dir / f"goal-{goal.command}-{goal.goal_hash[:8]}.md"
        tmp = task_file.with_suffix(".tmp")
        tmp.write_text(render_goal_task_file(goal), encoding="utf-8")
        tmp.replace(task_file)
        typer.echo(f"hash:{goal.goal_hash} | task-file:{task_file}")
    elif json_out:
        typer.echo(json.dumps(goal.to_json_envelope(), indent=2))
    else:
        typer.echo(goal.objective)


def _project_root() -> Path:
    try:
        return find_specs_root().parent
    except Exception as exc:
        typer.echo(f"goal blocked: {exc}", err=True)
        raise typer.Exit(2) from exc


def _detect_livespec_root() -> Path:
    """Resolve the LiveSpec checkout root by walking parents of this module."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".agent-sync" / "skills").is_dir() and (
            parent / "validator"
        ).is_dir():
            return parent
    return here.parents[2]


__all__ = ["goal_app"]
