"""Typer subcommand: livespec spec-driver --new <stack>."""

# @spec FR-006: livespec spec-driver --new — .specs/features/016-cross-language-test-driver-architecture/spec.md#fr-006  # noqa: E501
# @spec AC-008: Scaffold + --force + clear error — .specs/features/016-cross-language-test-driver-architecture/spec.md#ac-008  # noqa: E501


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
    """Driver management entry point."""
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
