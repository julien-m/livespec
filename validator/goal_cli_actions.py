"""Execute goal CLI actions behind the thin Typer command façade."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import typer

from .command_registry import normalize_command_name
from .exceptions import (
    ExpectationsInvalid,
    ExpectationsMissing,
    OverrideMalformed,
    SpecsRootNotFoundError,
)
from .goal_bootstrap import GoalBootstrapError, select_goal_render_context
from .goal_cli_inputs import (
    MAX_TRANSCRIPT_BYTES,
    GoalInputError,
    ResolvedGoalInputs,
    read_evidence_input,
    read_transcript,
    resolve_goal_pair_inputs,
)
from .goal_cli_output import (
    archive_blocked,
    emit_archive_result,
    read_json_object,
    write_json_text_atomically,
)
from .goal_contracts import (
    GoalContract,
    compile_command_goal,
    prove_goal_task,
    render_goal_contract_file,
    render_goal_state_file,
    render_goal_status,
)
from .goal_evidence_paths import GoalEvidencePathError
from .goal_json import JsonObject
from .goal_pairing import GoalPairError
from .goal_review_identity import bind_review_model
from .run_artifacts import archive_goal_run


def render_goal_command(
    command: str,
    feature: str | None,
    flags: str,
    json_out: bool,
    save: bool,
) -> None:
    """Execute the render CLI action with stable diagnostics.

    Args:
        command: Command name or alias to compile.
        feature: Optional feature slug.
        flags: Raw command flags used for root selection.
        json_out: Whether to emit the goal envelope as JSON.
        save: Whether to persist contract and state files.

    Returns:
        None.

    Raises:
        typer.Exit: If root selection or goal compilation is blocked.

    Side effects:
        Reads configuration, emits CLI output, and optionally writes goal files.
    """
    livespec_root = _detect_livespec_root()
    try:
        context = select_goal_render_context(normalize_command_name(command), flags, Path.cwd())
    except (GoalBootstrapError, SpecsRootNotFoundError) as exc:
        typer.echo(f"goal blocked: {exc}", err=True)
        raise typer.Exit(2) from exc
    try:
        goal = compile_command_goal(
            command,
            project_root=context.project_root,
            livespec_root=livespec_root,
            feature=feature,
            flags=context.normalized_flags,
        )
    except (ExpectationsInvalid, ExpectationsMissing, OverrideMalformed) as exc:
        typer.echo(f"goal render blocked: {exc}", err=True)
        raise typer.Exit(2) from exc
    goal = bind_review_model(goal, context.project_root, livespec_root, feature)
    _emit_rendered_goal(goal, json_out=json_out, save=save)


def _emit_rendered_goal(goal: GoalContract, *, json_out: bool, save: bool) -> None:
    if save:
        goals_dir = Path(tempfile.gettempdir()) / "livespec-goals"
        goals_dir.mkdir(parents=True, exist_ok=True)
        contract_file = goals_dir / f"goal-{goal.command}-{goal.goal_hash[:8]}.contract.json"
        state_file = goals_dir / f"goal-{goal.command}-{goal.goal_hash[:8]}.state.json"
        write_json_text_atomically(contract_file, render_goal_contract_file(goal))
        write_json_text_atomically(state_file, render_goal_state_file(goal))
        typer.echo(
            f"hash:{goal.goal_hash} | contract-file:{contract_file} | state-file:{state_file}"
        )
    elif json_out:
        typer.echo(json.dumps(goal.to_json_envelope(), indent=2))
    else:
        typer.echo(goal.objective)


def prove_goal_command(
    contract_path: str | None,
    state_path: str | None,
    task_id: str,
    evidence_input: str,
) -> None:
    """Execute proof submission and persist the returned state.

    Args:
        contract_path: Raw immutable-contract path token.
        state_path: Raw mutable-state path token.
        task_id: Task receiving the submitted evidence.
        evidence_input: Inline evidence JSON or evidence-file token.

    Returns:
        None.

    Raises:
        typer.Exit: If validation is blocked or proof is rejected.
        OSError: If the accepted state cannot be persisted.

    Side effects:
        Reads control files, may replace the state file, and emits CLI output.
    """
    try:
        inputs = resolve_goal_pair_inputs(contract_path, state_path, operation="prove")
        evidence = read_evidence_input(evidence_input)
    except (GoalInputError, GoalPairError, OSError, SpecsRootNotFoundError) as exc:
        typer.echo(f"goal prove blocked: {exc}", err=True)
        raise typer.Exit(2) from exc
    try:
        result = prove_goal_task(
            inputs.contract,
            inputs.state,
            task_id,
            evidence,
            project_root=inputs.project_root,
        )
    except (GoalEvidencePathError, GoalPairError) as exc:
        typer.echo(f"goal prove blocked: {exc}", err=True)
        raise typer.Exit(2) from exc
    _emit_proof_result(inputs.state_path, result)


def _emit_proof_result(state_path: Path, result: JsonObject) -> None:
    write_json_text_atomically(
        state_path,
        json.dumps(result["state"], indent=2, sort_keys=True, ensure_ascii=False),
    )
    public_result = {key: value for key, value in result.items() if key != "state"}
    typer.echo(json.dumps(public_result, indent=2))
    if result["status"] != "ACCEPTED":
        raise typer.Exit(1)


def archive_goal_command(
    contract_path: str | None,
    state_path: str | None,
    feature: str | None,
    exit_code: int | None,
    stdout_file: Path | None,
    stderr_file: Path | None,
    json_out: bool,
    *,
    max_transcript_bytes: int = MAX_TRANSCRIPT_BYTES,
) -> None:
    """Execute archive validation, writing, and outcome emission.

    Args:
        contract_path: Raw immutable-contract path token.
        state_path: Raw mutable-state path token.
        feature: Optional feature identity assertion.
        exit_code: Archived process exit code.
        stdout_file: Optional stdout transcript path.
        stderr_file: Optional stderr transcript path.
        json_out: Whether to emit the archive result as JSON.
        max_transcript_bytes: Maximum bytes accepted per transcript.

    Returns:
        None.

    Raises:
        typer.Exit: If validation, archive writing, or emission is blocked.

    Side effects:
        Reads control/transcript files, may write one run artifact, and emits output.
    """
    if exit_code is not None and not 0 <= exit_code <= 255:
        raise archive_blocked("--exit-code must be between 0 and 255", json_out=json_out)
    try:
        inputs, stdout_text, stderr_text = _prepare_archive_inputs(
            contract_path,
            state_path,
            feature,
            stdout_file,
            stderr_file,
            max_transcript_bytes,
        )
    except (GoalInputError, GoalPairError, OSError, SpecsRootNotFoundError, ValueError) as exc:
        raise archive_blocked(str(exc), json_out=json_out) from exc
    _archive_prepared(inputs, feature, exit_code, stdout_text, stderr_text, json_out)


def status_goal_command(state_path: Path) -> None:
    """Execute state-status loading and stable emission.

    Args:
        state_path: Mutable goal-state file to summarize.

    Returns:
        None.

    Raises:
        typer.Exit: If the state file cannot be read or decoded.

    Side effects:
        Reads the state file and emits one status line.
    """
    try:
        state = read_json_object(state_path)
    except (OSError, json.JSONDecodeError) as exc:
        typer.echo(f"goal status blocked: {exc}", err=True)
        raise typer.Exit(2) from exc
    typer.echo(render_goal_status(state))


def _archive_prepared(
    inputs: ResolvedGoalInputs,
    feature: str | None,
    exit_code: int | None,
    stdout_text: str | None,
    stderr_text: str | None,
    json_out: bool,
) -> None:
    try:
        result = archive_goal_run(
            inputs.contract,
            inputs.state,
            project_root=inputs.project_root,
            feature=feature,
            exit_code=exit_code,
            stdout_text=stdout_text,
            stderr_text=stderr_text,
        )
    except (OSError, ValueError) as exc:
        # The CLI owns formatting domain and I/O failures into stable exits.
        raise archive_blocked(str(exc), json_out=json_out) from exc
    emit_archive_result(result, json_out=json_out)


def _prepare_archive_inputs(
    contract_path: str | None,
    state_path: str | None,
    feature: str | None,
    stdout_file: Path | None,
    stderr_file: Path | None,
    max_transcript_bytes: int,
) -> tuple[ResolvedGoalInputs, str | None, str | None]:
    inputs = resolve_goal_pair_inputs(
        contract_path,
        state_path,
        operation="archive",
        feature=feature,
    )
    stdout_text = read_transcript(stdout_file, max_bytes=max_transcript_bytes)
    stderr_text = read_transcript(stderr_file, max_bytes=max_transcript_bytes)
    return inputs, stdout_text, stderr_text


def _detect_livespec_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".agent-sync" / "skills").is_dir() and (parent / "validator").is_dir():
            return parent
    return here.parents[2]


__all__ = [
    "archive_goal_command",
    "prove_goal_command",
    "render_goal_command",
    "status_goal_command",
]
