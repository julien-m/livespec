# LiveSpec traceability anchors
# @spec(FR-001)
# @spec(FR-009)

"""CLI command for project-level LiveSpec health audits."""

from __future__ import annotations

from pathlib import Path

import typer

from validator.cli_commands._common import require_specs_root
from validator.cli_exit_codes import EXIT_MISSING_SPECS
from validator.doctor import run_doctor
from validator.doctor.models import DoctorStatus
from validator.doctor.report import render_doctor_json, render_doctor_text

SUPPORTED_FORMATS = {"compact", "full", "json"}
FORMAT_OPTION = typer.Option(
    "compact",
    "--format",
    "-f",
    help="Output format: compact, full, json.",
)
STRICT_OPTION = typer.Option(False, "--strict", help="Promote warnings to errors.")
FIX_PLAN_OPTION = typer.Option(
    False,
    "--fix-plan",
    help="Print cleanup actions without modifying files.",
)
APPLY_CLEANUP_OPTION = typer.Option(
    False,
    "--apply-cleanup",
    help="Apply safe cleanup actions; destructive actions are refused.",
)


def register(app: typer.Typer) -> None:
    """Register ``livespec doctor``."""
    # @spec FR-001: CLI — .specs/features/055-spec-doctor-project-health/spec.md#fr-001
    app.command(
        name="doctor",
        help="Audit project health beyond structural spec validation.",
    )(doctor_command)


def doctor_command(
    output_format: str = FORMAT_OPTION,
    strict: bool = STRICT_OPTION,
    fix_plan: bool = FIX_PLAN_OPTION,
    apply_cleanup: bool = APPLY_CLEANUP_OPTION,
) -> None:
    """Run the project-level LiveSpec doctor audit."""
    # @spec FR-009: Formats — .specs/features/055-spec-doctor-project-health/spec.md#fr-009
    # @spec FR-012: Tests — .specs/features/055-spec-doctor-project-health/spec.md#fr-012
    # @spec AC-013: Strict — .specs/features/055-spec-doctor-project-health/spec.md#ac-013
    if output_format not in SUPPORTED_FORMATS:
        typer.echo("Error: --format must be compact, full, or json", err=True)
        raise typer.Exit(2)
    try:
        project_root = require_specs_root()
    except typer.Exit as exc:
        typer.echo(
            "BLOCKED at step 1 - prerequisite_unmet - .specs directory missing",
            err=True,
        )
        raise typer.Exit(EXIT_MISSING_SPECS) from exc

    report = run_doctor(
        Path(project_root),
        strict=strict,
        fix_plan=fix_plan,
        apply_cleanup=apply_cleanup,
    )
    if output_format == "json":
        typer.echo(render_doctor_json(report))
    else:
        typer.echo(render_doctor_text(report, full=output_format == "full" or fix_plan))
    raise typer.Exit(0 if report.status == DoctorStatus.OK else 1)


__all__ = ["doctor_command", "register"]
