# @spec(FR-001)
# @spec(FR-003)
# @spec(FR-005)
# @spec(FR-006)
# @spec(FR-008)
# @spec(FR-009)
# @spec(FR-010)
# @spec(FR-016)

"""Render, prove, archive, and inspect deterministic command goals."""

from __future__ import annotations

from pathlib import Path

import typer

from ..goal_cli_actions import (
    archive_goal_command,
    prove_goal_command,
    render_goal_command,
    status_goal_command,
)
from ..goal_cli_inputs import MAX_TRANSCRIPT_BYTES

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
CONTRACT_OPTION = typer.Option(None, "--contract", help="Path to goal contract JSON.")
STATE_OPTION = typer.Option(None, "--state", help="Path to mutable goal state JSON.")
REQUIRED_STATE_OPTION = typer.Option(..., "--state", help="Path to mutable goal state JSON.")
TASK_OPTION = typer.Option(..., "--task", help="Task id to prove.")
EVIDENCE_OPTION = typer.Option(..., "--evidence", help="Evidence JSON string or file path.")
EXIT_CODE_OPTION = typer.Option(None, "--exit-code", help="Wrapped command exit code (0-255).")
STDOUT_FILE_OPTION = typer.Option(None, "--stdout-file", help="Captured stdout file to embed.")
STDERR_FILE_OPTION = typer.Option(None, "--stderr-file", help="Captured stderr file to embed.")


# @spec FR-001: Isolate bootstrap render, FR-007: Format blocked diagnostics
#   — .specs/features/076-spec-init-goal-bootstrap/spec.md#fr-001
@goal_app.command("render")
def render_cmd(
    command: str = COMMAND_ARGUMENT,
    feature: str | None = FEATURE_OPTION,
    flags: str = FLAGS_OPTION,
    json_out: bool = JSON_OPTION,
    save: bool = SAVE_OPTION,
) -> None:
    """Render a deterministic goal for a command invocation.

    Args:
        command: Command name or alias.
        feature: Optional feature scope.
        flags: Active command flags.
        json_out: Whether to emit JSON.
        save: Whether to persist paired control files under ``$TMPDIR``.

    Returns:
        None.

    Raises:
        typer.Exit: With 2 when target or expectations validation blocks.

    Side effects:
        Emits stdout/stderr and optionally writes two temporary control files.
    """
    render_goal_command(command, feature, flags, json_out, save)


# @spec FR-004: Validate bootstrap proof, FR-007: Preserve prove exits
#   — .specs/features/076-spec-init-goal-bootstrap/spec.md#fr-004
@goal_app.command("prove")
def prove_cmd(
    contract_path: str | None = CONTRACT_OPTION,
    state_path: str | None = STATE_OPTION,
    task_id: str = TASK_OPTION,
    evidence_input: str = EVIDENCE_OPTION,
) -> None:
    """Submit task evidence and update the mutable state file.

    Args:
        contract_path: Explicit immutable contract file.
        state_path: Explicit mutable state file.
        task_id: Contract task identifier.
        evidence_input: Inline JSON object or external JSON-object file.

    Returns:
        None.

    Raises:
        typer.Exit: With 1 for rejected proof or 2 for blocked input.

    Side effects:
        Rewrites ``state_path`` atomically and emits the proof outcome.
    """
    prove_goal_command(contract_path, state_path, task_id, evidence_input)


# @spec FR-001: archive CLI surface + exit mapping
#   — .specs/features/039.1-goal-archive-run-artifacts/spec.md#fr-001
# @spec FR-005: Archive from persisted root, FR-007: Preserve archive exits
#   — .specs/features/076-spec-init-goal-bootstrap/spec.md#fr-005
@goal_app.command("archive")
def archive_cmd(
    contract_path: str | None = CONTRACT_OPTION,
    state_path: str | None = STATE_OPTION,
    feature: str | None = FEATURE_OPTION,
    exit_code: int | None = EXIT_CODE_OPTION,
    stdout_file: Path | None = STDOUT_FILE_OPTION,
    stderr_file: Path | None = STDERR_FILE_OPTION,
    json_out: bool = JSON_OPTION,
) -> None:
    """Archive an explicit pair under its bound project root.

    Args:
        contract_path: Explicit immutable contract file.
        state_path: Explicit mutable state file.
        feature: Optional feature assertion and receipt scope.
        exit_code: Optional wrapped-command exit code.
        stdout_file: Optional stdout transcript.
        stderr_file: Optional stderr transcript.
        json_out: Whether to emit JSON.

    Returns:
        None.

    Raises:
        typer.Exit: With 1 for drift/error or 2 for blocked input.

    Side effects:
        Writes one atomic RunArtifact and emits its outcome.
    """
    archive_goal_command(
        contract_path,
        state_path,
        feature,
        exit_code,
        stdout_file,
        stderr_file,
        json_out,
        max_transcript_bytes=MAX_TRANSCRIPT_BYTES,
    )


@goal_app.command("status")
def status_cmd(state_path: Path = REQUIRED_STATE_OPTION) -> None:
    """Print mutable goal state status.

    Args:
        state_path: Explicit mutable state JSON file.

    Returns:
        None.

    Raises:
        typer.Exit: With 2 when the state cannot be read as a JSON object.

    Side effects:
        Reads the state file and emits a stable one-line summary.
    """
    status_goal_command(state_path)


__all__ = ["goal_app"]
