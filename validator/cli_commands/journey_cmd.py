"""CLI commands for canonical executable user journeys."""

from __future__ import annotations

from pathlib import Path

import typer

from validator.cli_commands._common import emit_summary, require_specs_root
from validator.journeys import compile_journeys, scan_journeys, validate_journeys
from validator.journeys.models import JourneySeverity
from validator.journeys.paths import relative_to_project

journey_app = typer.Typer(help="Validate, compile, and report executable user journeys.")


def _format_issue(project_root: Path, severity: str, code: str, path: Path, message: str) -> str:
    """Render a compact CLI issue line."""
    relative_path = relative_to_project(project_root, path)
    return f"{severity} {code} {relative_path}: {message}"


def register(app: typer.Typer) -> None:
    """Register the ``journey`` command group."""
    # @spec FR-003: Journey CLI — .specs/features/056-executable-user-journeys/spec.md#fr-003
    app.add_typer(journey_app, name="journey")


@journey_app.command(name="validate")
def validate_command(
    feature: str | None = typer.Option(None, "--feature", help="Feature slug to validate."),
) -> None:
    """Validate canonical journey YAML files."""
    project_root = require_specs_root()
    result = validate_journeys(project_root, feature)
    for issue in result.issues:
        typer.echo(
            _format_issue(
                project_root,
                issue.severity.value,
                issue.code,
                issue.path,
                issue.message,
            )
        )
    emit_summary(
        "journey validate",
        "OK" if result.error_count == 0 else "FAIL",
        valid=len(result.journeys),
        warnings=result.warning_count,
        errors=result.error_count,
    )
    raise typer.Exit(0 if result.error_count == 0 else 1)


@journey_app.command(name="compile")
def compile_command(
    feature: str | None = typer.Option(None, "--feature", help="Feature slug to compile."),
) -> None:
    """Compile canonical journeys into native test artifacts."""
    project_root = require_specs_root()
    result = compile_journeys(project_root, feature)
    for issue in result.issues:
        typer.echo(
            _format_issue(
                project_root,
                issue.severity.value,
                issue.code,
                issue.path,
                issue.message,
            )
        )
    for artifact in result.artifacts:
        typer.echo(
            f"compiled {artifact.runner}: {relative_to_project(project_root, artifact.output_path)}"
        )
    emit_summary(
        "journey compile",
        "OK" if result.error_count == 0 else "FAIL",
        compiled=len(result.artifacts),
        errors=result.error_count,
    )
    raise typer.Exit(0 if result.error_count == 0 else 1)


@journey_app.command(name="test")
def test_command(
    feature: str | None = typer.Option(None, "--feature", help="Feature slug to test."),
) -> None:
    """Compile journeys and report executable/manual/disabled categories."""
    project_root = require_specs_root()
    compile_result = compile_journeys(project_root, feature)
    report = scan_journeys(project_root, feature)
    for issue in compile_result.issues:
        typer.echo(
            _format_issue(
                project_root,
                issue.severity.value,
                issue.code,
                issue.path,
                issue.message,
            )
        )
    typer.echo(f"Executable user journeys: {report.executable_count}")
    typer.echo(f"Manual journeys: {report.manual_count}")
    typer.echo(f"Disabled journeys: {report.disabled_count}")
    error_count = compile_result.error_count + sum(
        1 for finding in report.findings if finding.severity == JourneySeverity.ERROR
    )
    emit_summary(
        "journey test",
        "OK" if error_count == 0 else "FAIL",
        executable=report.executable_count,
        manual=report.manual_count,
        disabled=report.disabled_count,
        errors=error_count,
    )
    raise typer.Exit(0 if error_count == 0 else 1)


def journey_category_counts(project_root: Path, feature: str | None = None) -> tuple[int, int, int]:
    """Return executable, manual, and disabled journey counts for reports."""
    report = scan_journeys(project_root, feature)
    return report.executable_count, report.manual_count, report.disabled_count


__all__ = ["journey_app", "journey_category_counts", "register"]
