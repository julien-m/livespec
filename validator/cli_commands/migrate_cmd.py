"""Migration planning CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from validator.migration_planner import MigrationPlannerError, build_migration_plan

migrate_app = typer.Typer(name="migrate", help="Plan and inspect LiveSpec migrations.")


def register(app: typer.Typer) -> None:
    """Register the ``migrate`` command group."""
    app.add_typer(migrate_app, name="migrate")


@migrate_app.command("plan")
def plan_command(
    project: Annotated[
        Path,
        typer.Option("--project", help="Project root containing .specs/."),
    ] = Path("."),
    livespec: Annotated[
        Path,
        typer.Option("--livespec", help="LiveSpec repository root containing VERSION."),
    ] = Path("."),
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON."),
    ] = False,
) -> None:
    """Print the metadata-aware migration plan.

    # @spec FR-005: Planner CLI
    #   - .specs/features/053-migration-planner-penflow-backfill/spec.md#fr-005
    """
    try:
        plan = build_migration_plan(project, livespec)
    except MigrationPlannerError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
    payload = plan.to_dict()
    if json_output:
        typer.echo(json.dumps(payload, indent=2))
    else:
        typer.echo(f"Project version: {plan.project_version}")
        typer.echo(f"Target version: {plan.target_version}")
        typer.echo(f"Apply: {', '.join(map(str, plan.apply)) or 'none'}")
        typer.echo(f"Skipped: {json.dumps(plan.skipped)}")
        typer.echo(
            "Invalid restore points: "
            f"{', '.join(map(str, plan.invalid_restore_points)) or 'none'}"
        )
    raise typer.Exit(0)


__all__ = ["migrate_app", "register"]
