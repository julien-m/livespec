"""CLI surface for root Penflow UI contract workspaces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from validator.penflow_contract import (
    PenflowContractStatus,
    bootstrap_penflow_workspace,
    get_penflow_contract_status,
)

penflow_contract_app = typer.Typer(
    name="penflow-contract",
    help="Inspect and bootstrap the root penflow/ UI contract workspace.",
    no_args_is_help=True,
)


def register(app: typer.Typer) -> None:
    """Register the ``penflow-contract`` command group.

    Args:
        app: Top-level Typer app mutated with the Penflow command group.
    """
    app.add_typer(penflow_contract_app, name="penflow-contract")


def _verdict_from_status(status: PenflowContractStatus) -> str:
    """Return the observable Penflow contract verdict for CLI consumers."""
    if status.state == "absent":
        return "ABSENT"
    if status.state == "incomplete" or status.runtime_comparison == "BLOCKED":
        return "BLOCKED"
    return "PASS"


@penflow_contract_app.command("status")
def status_command(
    project: Annotated[
        Path,
        typer.Option("--project", help="Project root containing penflow/."),
    ] = Path("."),
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON."),
    ] = False,
    require_actual: Annotated[
        bool,
        typer.Option(
            "--require-actual",
            help="Treat missing actual-ui-tree.json as BLOCKED for UI runtime comparison.",
        ),
    ] = False,
) -> None:
    """Print root Penflow workspace status.

    Args:
        project: Project root to inspect.
        json_output: Emit parseable JSON instead of human-readable text.
        require_actual: Treat missing runtime actual tree as blocking.

    Side effects:
        Writes status to stdout and exits with ``0``, ``1``, or ``2``.
    """
    status = get_penflow_contract_status(project.resolve(), require_actual=require_actual)
    verdict = _verdict_from_status(status)
    if json_output:
        payload = status.to_dict()
        payload["verdict"] = verdict
        typer.echo(json.dumps(payload, indent=2))
    else:
        typer.echo(f"Penflow contract: {status.state}")
        typer.echo(f"Runtime comparison: {status.runtime_comparison}")
        typer.echo(f"Runtime reason: {status.runtime_reason}")
        typer.echo(f"Workspace: {status.workspace}")
        typer.echo(f"Present: {', '.join(status.present) or 'none'}")
        typer.echo(f"Missing: {', '.join(status.missing) or 'none'}")
        typer.echo(f"Flows: {status.flow_count} · Screens: {status.screen_count}")
        if status.parse_error:
            typer.echo(f"Semantic tree parse warning: {status.parse_error}", err=True)
        typer.echo(f"Penflow Contract Verdict: {verdict}")
    if status.runtime_comparison == "BLOCKED":
        raise typer.Exit(2)
    raise typer.Exit(0 if status.state != "incomplete" else 1)


@penflow_contract_app.command("bootstrap")
def bootstrap_command(
    project: Annotated[
        Path,
        typer.Option("--project", help="Project root containing .brainstorm/penflow/."),
    ] = Path("."),
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON."),
    ] = False,
) -> None:
    """Copy ``.brainstorm/penflow/`` to root ``penflow/`` when absent.

    Args:
        project: Project root containing optional ``.brainstorm/penflow/``.
        json_output: Emit parseable JSON instead of human-readable text.

    Side effects:
        May copy a Penflow workspace and writes the result to stdout.
    """
    result = bootstrap_penflow_workspace(project.resolve())
    if json_output:
        typer.echo(json.dumps(result.to_dict(), indent=2))
    else:
        typer.echo(f"Penflow bootstrap: {result.reason}")
        typer.echo(f"Source: {result.source}")
        typer.echo(f"Destination: {result.destination}")
        typer.echo(f"Status: {result.status.state}")
    raise typer.Exit(0)


# Export the command group and registrar for the unified CLI loader.
__all__ = ["penflow_contract_app", "register"]
