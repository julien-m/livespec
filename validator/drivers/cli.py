# LiveSpec traceability anchors
# @spec(FR-006)

"""Typer subcommand: livespec spec.driver --new <stack>."""

# Feature 023: driver custom scaffolding.
# @spec FR-001: livespec spec.driver --new <stack> CLI
# @spec AC-010: After scaffold, prints path + reminder + integration command

from __future__ import annotations

from pathlib import Path

import typer

from .scaffold import DriverFileExistsError, scaffold_custom_driver

driver_app = typer.Typer(name="spec.driver", help="Manage LiveSpec test drivers")


@driver_app.callback(invoke_without_command=True)
def root(
    new: str | None = typer.Option(
        None, "--new", help="Create .specs/drivers/<stack>.yaml from template"
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing driver file"),
) -> None:
    """Handle ``livespec spec.driver`` root options.

    Args:
        new: Stack slug to scaffold under ``.specs/drivers``.
        force: Whether to overwrite an existing manifest file.

    Side Effects:
        Writes a manifest file and emits status or error text to the terminal.
    """
    if new is None:
        typer.echo("Usage: livespec spec.driver --new <stack> [--force]")
        raise typer.Exit(0)
    project_root = Path.cwd()
    specs_dir = project_root / ".specs"
    if not specs_dir.is_dir():
        # EC-004: warn but don't block.
        typer.echo(
            "Note: .specs/ directory not found — "
            "run `livespec spec-init` first if this project is not initialized.",
            err=True,
        )
    try:
        target = scaffold_custom_driver(new, project_root=project_root, force=force)
    except DriverFileExistsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from None
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(2) from None
    rel = target.relative_to(project_root) if target.is_absolute() else target
    typer.echo(f"Created {rel}")
    typer.echo("Next steps:")
    typer.echo("  1. Edit the file and fill in each capability's `command:` (or `script:`).")
    typer.echo("  2. Verify the manifest with: livespec spec-check")
    typer.echo("  3. See .specs/spec-system.md for the driver integration guide.")
