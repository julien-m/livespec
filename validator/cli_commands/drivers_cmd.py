"""``livespec drivers`` — list discoverable drivers."""

# @spec FR-003: drivers subcommand — .specs/features/035-unified-cli-surface/spec.md#fr-003
# @spec AC-006: Table output — .specs/features/035-unified-cli-surface/spec.md#ac-006
# @spec AC-007: --json output — .specs/features/035-unified-cli-surface/spec.md#ac-007
# @spec EC-003: Empty array on no match — .specs/features/035-unified-cli-surface/spec.md#ec-003

from __future__ import annotations

import json

import typer

from ..cli_exit_codes import EXIT_MISSING_SPECS
from ..drivers.registry import DriverRegistry
from ..drivers.test_config import pick_primary_driver
from ._common import (
    emit_summary,
    join_capabilities,
    require_specs_root,
    run_with_debug,
)


def drivers_command(
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Emit a JSON array suitable for tooling instead of a human table.",
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Print the full stacktrace on error."
    ),
) -> None:
    """List built-in and custom drivers seen by the registry.

    Example:
        $ livespec drivers
        Driver      Source     Match  Capabilities
        python      built-in   yes*   coverage,mutation
    """
    run_with_debug(
        lambda: _run_drivers(as_json=as_json),
        debug=debug,
        subcommand="drivers",
        fail_exit_code=EXIT_MISSING_SPECS,
    )


def register(app: typer.Typer) -> None:
    """Register the ``drivers`` subcommand on ``app``."""
    app.command(
        name="drivers",
        help="List discoverable drivers for the current project.",
    )(drivers_command)


def _run_drivers(*, as_json: bool) -> None:
    """Execute the ``drivers`` subcommand body."""
    project_root = require_specs_root()
    registry = DriverRegistry(project_root)
    registry.discover()
    all_drivers = registry.all()
    matching_drivers = registry.matching()
    matching = {driver.name for driver in matching_drivers}
    primary = pick_primary_driver(matching_drivers, project_root)
    primary_name = primary.name if primary else None

    if as_json:
        # EC-003 requires tooling mode to degrade to ``[]`` when nothing matches,
        # so scripts can treat "no usable driver" as an empty result set.
        payload = [] if not matching_drivers else [
            {
                "name": d.name,
                "source": "custom" if d.is_custom else "built-in",
                "match": d.name in matching,
                "primary": d.name == primary_name,
                "capabilities": d.implemented_capabilities(),
            }
            for d in all_drivers
        ]
        typer.echo(json.dumps(payload, indent=2))
    else:
        # AC-006 — fixed-width table for human consumption.
        header = ("Driver", "Source", "Match", "Capabilities")
        rows: list[tuple[str, str, str, str]] = [header]
        if not all_drivers:
            typer.echo("No drivers found.")
        else:
            for d in all_drivers:
                match_marker = "yes" if d.name in matching else "no"
                if d.name == primary_name:
                    match_marker += "*"
                rows.append(
                    (
                        d.name,
                        "custom" if d.is_custom else "built-in",
                        match_marker,
                        join_capabilities(d),
                    )
                )
            widths = [max(len(row[i]) for row in rows) for i in range(4)]
            for i, row in enumerate(rows):
                line = "  ".join(cell.ljust(widths[idx]) for idx, cell in enumerate(row))
                typer.echo(line)
                if i == 0:
                    typer.echo("  ".join("-" * w for w in widths))
            if primary_name:
                typer.echo(f"\n* primary driver — {primary_name}")

    emit_summary(
        "drivers",
        "OK",
        total=len(all_drivers),
        matching=len(matching),
        primary=primary_name or "-",
    )


__all__ = ["register"]
