"""CLI for the Design Alignment Gate."""

# @spec FR-004: Design alignment CLI
#   — .specs/features/047-design-alignment-gate/spec.md#fr-004

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from validator.design_alignment import compare_contract_files

design_alignment_app = typer.Typer(
    name="design-alignment",
    help="Compare ui.pen-derived design contracts with runtime UI contracts.",
    no_args_is_help=True,
)


def register(app: typer.Typer) -> None:
    """Register the design-alignment command group."""
    app.add_typer(design_alignment_app, name="design-alignment")


@design_alignment_app.command("compare")
def compare_command(
    design: Annotated[
        Path,
        typer.Option(
            "--design",
            help="Path to penflow/ui.pen or normalized design contract JSON.",
        ),
    ],
    runtime: Annotated[
        Path,
        typer.Option(
            "--runtime",
            help="Path to normalized runtime contract JSON captured by a UI runner.",
        ),
    ],
    screen: Annotated[str, typer.Option("--screen", help="Screen id to compare.")],
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            help="Directory for report, diff, and manifest artifacts.",
        ),
    ],
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Emit machine-readable JSON.",
        ),
    ] = False,
) -> None:
    """Run design alignment and exit 0/1/2 for PASS/FAIL/BLOCKED."""
    result = compare_contract_files(
        design_path=design,
        runtime_path=runtime,
        screen=screen,
        output_dir=output_dir,
    )
    if json_output:
        typer.echo(json.dumps(result.to_dict(), indent=2))
    else:
        typer.echo(result.summary)
        if result.report_path:
            typer.echo(f"Report: {result.report_path}")
        for issue in result.issues:
            typer.echo(f"- {issue.message}")
    raise typer.Exit(result.exit_code)


__all__ = ["design_alignment_app", "register"]
