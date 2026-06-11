# LiveSpec traceability anchors
# @spec(FR-001)
# @spec(FR-003)
# @spec(FR-005)
# @spec(FR-006)
# @spec(FR-008)
# @spec(FR-009)
# @spec(FR-010)
# @spec(FR-016)

"""``livespec goal`` — render, prove, and archive deterministic command goals.

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
from ..outcome import exit_code_for
from ..run_artifacts import ArchiveResult, archive_goal_run
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
EXIT_CODE_OPTION = typer.Option(None, "--exit-code", help="Wrapped command exit code (0-255).")
STDOUT_FILE_OPTION = typer.Option(None, "--stdout-file", help="Captured stdout file to embed.")
STDERR_FILE_OPTION = typer.Option(None, "--stderr-file", help="Captured stderr file to embed.")

# 10 MiB bounds the embedded transcript (and therefore the artifact) size while
# staying far above any realistic CLI stdout/stderr capture.
MAX_TRANSCRIPT_BYTES = 10 * 1024 * 1024


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


# @spec FR-001: archive CLI surface + exit mapping
#   — .specs/features/039.1-goal-archive-run-artifacts/spec.md#fr-001
@goal_app.command("archive")
def archive_cmd(
    contract_path: Path = CONTRACT_OPTION,
    state_path: Path = STATE_OPTION,
    feature: str | None = FEATURE_OPTION,
    exit_code: int | None = EXIT_CODE_OPTION,
    stdout_file: Path | None = STDOUT_FILE_OPTION,
    stderr_file: Path | None = STDERR_FILE_OPTION,
    json_out: bool = JSON_OPTION,
) -> None:
    """Archive a goal contract+state pair as a durable RunArtifact v2.

    Args:
        contract_path: Path to the immutable goal contract JSON (read-only).
        state_path: Path to the mutable goal state JSON (read-only).
        feature: Optional feature slug; enables receipt feature scoping.
        exit_code: Wrapped command exit code (0-255), or None when not recorded.
        stdout_file: Optional captured stdout file embedded verbatim.
        stderr_file: Optional captured stderr file embedded verbatim.
        json_out: Emit a JSON envelope instead of the human stdout line.

    Side effects:
        Writes ``.specs/.runs/<command>-<ISO-fs>-<hash8>.json``; never mutates
        the ``$TMPDIR`` inputs.

    Raises:
        typer.Exit: 1 on drift/error outcome, 2 on blocked (nothing written).
    """
    if exit_code is not None and not 0 <= exit_code <= 255:
        raise _archive_blocked("--exit-code must be between 0 and 255", json_out=json_out)
    try:
        contract = _read_json_file(contract_path)
        state = _read_json_file(state_path)
        stdout_text = _read_transcript(stdout_file)
        stderr_text = _read_transcript(stderr_file)
    except (OSError, ValueError) as exc:
        raise _archive_blocked(str(exc), json_out=json_out) from exc

    try:
        result = archive_goal_run(
            contract,
            state,
            project_root=_project_root(),
            feature=feature,
            exit_code=exit_code,
            stdout_text=stdout_text,
            stderr_text=stderr_text,
        )
    except (OSError, ValueError) as exc:
        # CLI boundary: malformed domain data or IO failures inside archiving
        # must surface as a formatted blocked outcome, never as a traceback.
        raise _archive_blocked(str(exc), json_out=json_out) from exc
    _emit_archive_result(result, json_out=json_out)


def _archive_blocked(reason: str, *, json_out: bool) -> typer.Exit:
    """Report a blocked archive outcome on both channels and build exit 2.

    Args:
        reason: One-line blocked reason.
        json_out: When true, also emit a machine-readable JSON envelope on
            stdout so ``--json`` callers never have to parse stderr text.

    Returns:
        A ``typer.Exit(2)`` for the caller to raise.
    """
    if json_out:
        typer.echo(json.dumps({"outcome": "blocked", "reason": reason}))
    typer.echo(f"goal archive blocked: {reason}", err=True)
    return typer.Exit(2)


def _read_transcript(path: Path | None) -> str | None:
    """Read an optional transcript file, rejecting oversized inputs.

    Raises:
        ValueError: When the file exceeds ``MAX_TRANSCRIPT_BYTES``.
        OSError: When the file cannot be read.
    """
    if path is None:
        return None
    size = path.stat().st_size
    if size > MAX_TRANSCRIPT_BYTES:
        raise ValueError(
            f"transcript file {path} is {size} bytes; max {MAX_TRANSCRIPT_BYTES} bytes"
        )
    return path.read_text(encoding="utf-8")


def _emit_archive_result(result: ArchiveResult, *, json_out: bool) -> None:
    """Print the archived path + outcome and map the outcome to an exit code.

    Raises:
        typer.Exit: 1 on drift/error outcome, 2 on blocked.
    """
    if result.outcome == "blocked" or result.path is None:
        raise _archive_blocked(result.blocked_reason or "unknown reason", json_out=json_out)
    if json_out:
        typer.echo(json.dumps({"archived": result.path.as_posix(), "outcome": result.outcome}))
    else:
        typer.echo(f"archived: {result.path.as_posix()} | outcome:{result.outcome}")
    final_exit = exit_code_for(result.outcome)
    if final_exit != 0:
        raise typer.Exit(final_exit)


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
