# LiveSpec traceability anchors
# @spec(FR-003)
# @spec(FR-005)
# @spec(FR-006)
# @spec(FR-008)
# @spec(FR-009)
# @spec(FR-010)
# @spec(FR-016)

"""``livespec goal`` — render and prove deterministic command goals.

# @spec FR-008, FR-009, FR-016, FR-017, FR-018
#   — .specs/features/052-deterministic-command-goal-contracts/spec.md
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, cast

import typer

from ..exceptions import ExpectationsInvalid, ExpectationsMissing, OverrideMalformed
from ..goal_contracts import (
    compile_command_goal,
    prove_goal_task,
    render_goal_contract_file,
    render_goal_state_file,
    render_goal_status,
)
from ..specs_utils import find_specs_root

goal_app = typer.Typer(name="goal", help="Render and prove command goal contracts.")

COMMAND_ARGUMENT = typer.Argument(..., help="Command name or alias.")
FEATURE_OPTION = typer.Option(None, "--feature", help="Resolved feature slug.")
FLAGS_OPTION = typer.Option("", "--flags", help="Space-separated active flags.")
JSON_OPTION = typer.Option(False, "--json", help="Emit JSON.")
SAVE_OPTION = typer.Option(
    False,
    "--save",
    help="Save contract/state JSON files to $TMPDIR/livespec-goals and emit hash+paths on stdout.",
)
CONTRACT_OPTION = typer.Option(..., "--contract", help="Path to goal contract JSON.")
STATE_OPTION = typer.Option(..., "--state", help="Path to mutable goal state JSON.")
TASK_OPTION = typer.Option(..., "--task", help="Task id to prove.")
EVIDENCE_OPTION = typer.Option(..., "--evidence", help="Evidence JSON string or file path.")


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
        contract_file = goals_dir / f"goal-{goal.command}-{goal.goal_hash[:8]}.contract.json"
        state_file = goals_dir / f"goal-{goal.command}-{goal.goal_hash[:8]}.state.json"
        _atomic_write_json_text(contract_file, render_goal_contract_file(goal))
        _atomic_write_json_text(state_file, render_goal_state_file(goal))
        typer.echo(
            f"hash:{goal.goal_hash} | contract-file:{contract_file} | state-file:{state_file}"
        )
    elif json_out:
        typer.echo(json.dumps(goal.to_json_envelope(), indent=2))
    else:
        typer.echo(goal.objective)


@goal_app.command("prove")
def prove_cmd(
    contract_path: Path = CONTRACT_OPTION,
    state_path: Path = STATE_OPTION,
    task_id: str = TASK_OPTION,
    evidence_input: str = EVIDENCE_OPTION,
) -> None:
    """Submit task evidence and update the mutable state file.

    ``--evidence`` accepts either an inline JSON object string or a path to a
    JSON object file. Only this command may mark a task complete; every call
    rewrites ``--state`` with the accepted attempt or rejection details.
    """
    try:
        contract = _read_json_file(contract_path)
        state = _read_json_file(state_path)
        evidence = _read_evidence(evidence_input)
    except (OSError, json.JSONDecodeError) as exc:
        typer.echo(f"goal prove blocked: {exc}", err=True)
        raise typer.Exit(2) from exc

    result = prove_goal_task(
        contract,
        state,
        task_id,
        evidence,
        project_root=_project_root(),
    )
    _atomic_write_json_text(
        state_path,
        json.dumps(result["state"], indent=2, sort_keys=True, ensure_ascii=False),
    )
    typer.echo(json.dumps({k: v for k, v in result.items() if k != "state"}, indent=2))
    if result["status"] == "ACCEPTED":
        return
    raise typer.Exit(1)


@goal_app.command("status")
def status_cmd(state_path: Path = STATE_OPTION) -> None:
    """Print mutable goal state status."""
    try:
        state = _read_json_file(state_path)
    except (OSError, json.JSONDecodeError) as exc:
        typer.echo(f"goal status blocked: {exc}", err=True)
        raise typer.Exit(2) from exc
    typer.echo(render_goal_status(state))


def _atomic_write_json_text(path: Path, text: str) -> None:
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _read_json_file(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise json.JSONDecodeError("JSON root must be an object", path.as_posix(), 0)
    return cast(dict[str, Any], parsed)


def _read_evidence(evidence_input: str) -> dict[str, Any]:
    path = Path(evidence_input)
    if path.exists():
        return _read_json_file(path)
    parsed = json.loads(evidence_input)
    if not isinstance(parsed, dict):
        raise json.JSONDecodeError("evidence must be a JSON object", evidence_input, 0)
    return cast(dict[str, Any], parsed)


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
        if (parent / ".agent-sync" / "skills").is_dir() and (parent / "validator").is_dir():
            return parent
    return here.parents[2]


__all__ = ["goal_app"]
