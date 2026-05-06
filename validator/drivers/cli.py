"""Typer subcommand: livespec spec-driver --new <stack>."""

# @spec FR-006: Driver manifests can be scaffolded from the main LiveSpec CLI.
# @spec AC-008: The CLI exposes forceful overwrite and clear failure modes.


from __future__ import annotations

from pathlib import Path

import typer

from .scaffold import DriverFileExistsError, scaffold_custom_driver

driver_app = typer.Typer(name="spec-driver", help="Manage LiveSpec test drivers")


@driver_app.callback(invoke_without_command=True)
def root(
    new: str | None = typer.Option(
        None, "--new", help="Create .specs/drivers/<stack>.yaml from template"
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite existing driver file"
    ),
) -> None:
    """Handle ``livespec spec-driver`` root options.

    Args:
        new: Stack slug to scaffold under ``.specs/drivers``.
        force: Whether to overwrite an existing manifest file.

    Side Effects:
        Writes a manifest file and emits status or error text to the terminal.
    """
    if new is None:
        typer.echo("Usage: livespec spec-driver --new <stack> [--force]")
        raise typer.Exit(0)
    try:
        target = scaffold_custom_driver(new, project_root=Path.cwd(), force=force)
    except DriverFileExistsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from None
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(2) from None
    typer.echo(f"Created {target}")
    typer.echo("Next: edit the file and fill in the capabilities you want to enable.")
