# LiveSpec traceability anchors
# @spec(FR-003)
# @spec(FR-022)
# @spec(FR-023)
# @spec(FR-024)
# @spec(FR-027)

"""CLI commands for global User Journeys v2."""

# @spec FR-022, FR-023, FR-024, FR-027, FR-040: journey CLI, run, policies, migration
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#fr-022

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import typer

from validator.cli_commands._common import emit_summary, require_specs_root
from validator.journeys import compile_journeys, scan_journeys, validate_journeys
from validator.journeys.fixtures import scaffold_fixtures_contract
from validator.journeys.impact import analyze_journey_impacts
from validator.journeys.index import build_journey_index
from validator.journeys.migration import migrate_v1_journeys
from validator.journeys.models import JourneyIssue
from validator.journeys.paths import fixtures_contract_path, relative_to_project
from validator.journeys.runner import run_journeys
from validator.journeys.schema import RunStage

journey_app = typer.Typer(help="Validate, compile, run, and inspect User Journeys v2.")
fixtures_app = typer.Typer(help="Manage the journey fixtures bootstrap contract.")
journey_app.add_typer(fixtures_app, name="fixtures")
RunStageOption = Annotated[RunStage, typer.Option("--stage", help="Run policy stage.")]
ChangedFileOption = Annotated[
    list[Path] | None,
    typer.Option("--changed-file", help="Changed file to analyze; repeatable."),
]


def register(app: typer.Typer) -> None:
    """Register the ``journey`` command group."""
    app.add_typer(journey_app, name="journey")


@journey_app.command(name="validate")
def validate_command(
    journey: str | None = typer.Option(None, "--journey", help="Journey ID to validate."),
    feature: str | None = typer.Option(None, "--feature", help="Covered feature slug."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Validate canonical v2 journey YAML files."""
    project_root = require_specs_root()
    result = validate_journeys(project_root, feature)
    if journey is not None:
        result = type(result)(
            journeys=[item for item in result.journeys if item.journey_id == journey],
            issues=[issue for issue in result.issues if journey in issue.path.as_posix()],
        )
    if json_output:
        typer.echo(
            json.dumps(
                {
                    "summary": {
                        "valid": len(result.journeys),
                        "warnings": result.warning_count,
                        "errors": result.error_count,
                    },
                    "issues": [_issue_json(project_root, issue) for issue in result.issues],
                }
            )
        )
    else:
        _emit_issues(project_root, result.issues)
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
    journey: str | None = typer.Option(None, "--journey", help="Journey ID to compile."),
    feature: str | None = typer.Option(None, "--feature", help="Covered feature slug."),
    changed: bool = typer.Option(False, "--changed", help="Compile changed journeys."),
    force: bool = typer.Option(False, "--force", help="Overwrite compiled artifacts."),
) -> None:
    """Compile v2 journeys into native test artifacts."""
    project_root = require_specs_root()
    result = compile_journeys(project_root, feature, journey=journey, force=force or changed)
    _emit_issues(project_root, result.issues)
    for artifact in result.artifacts:
        output_path = relative_to_project(project_root, artifact.output_path)
        typer.echo(f"compiled {artifact.runner}: {output_path}")
    emit_summary(
        "journey compile",
        "OK" if result.error_count == 0 else "FAIL",
        compiled=len(result.artifacts),
        errors=result.error_count,
    )
    raise typer.Exit(0 if result.error_count == 0 else 1)


@journey_app.command(name="run")
def run_command(
    journey: str | None = typer.Option(None, "--journey", help="Journey ID to run."),
    feature: str | None = typer.Option(None, "--feature", help="Covered feature slug."),
    impacted: bool = typer.Option(False, "--impacted", help="Run impacted journeys."),
    all_journeys: bool = typer.Option(False, "--all", help="Run all selected journeys."),
    stage: RunStageOption = RunStage.LOCAL,
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run compiled journey artifacts without compiling."""
    _ = impacted, all_journeys
    project_root = require_specs_root()
    result = run_journeys(
        project_root,
        journey=journey,
        feature=feature,
        stage=stage,
    )
    if json_output:
        typer.echo(
            json.dumps(
                {
                    "executed": result.executed,
                    "manual": result.manual,
                    "disabled": result.disabled,
                    "issues": [_issue_json(project_root, issue) for issue in result.issues],
                    # @spec FR-002: Journey run JSON exposes replay records
                    # — .specs/features/074-agent-device-proof-adapter/spec.md#fr-002
                    "runs": [asdict(record) for record in result.runs],
                }
            )
        )
    else:
        _emit_issues(project_root, result.issues)
        for record in result.runs:
            typer.echo(
                "run: "
                f"{record.journey_id} "
                f"runner={record.runner} "
                f"udid={record.udid or '-'} "
                f"destination={record.destination or '-'}"
            )
        emit_summary(
            "journey run",
            "OK" if result.error_count == 0 else "FAIL",
            executed=len(result.executed),
            manual=len(result.manual),
            disabled=len(result.disabled),
            errors=result.error_count,
        )
    raise typer.Exit(0 if result.error_count == 0 else 1)


@journey_app.command(name="test")
def test_command(
    feature: str | None = typer.Option(None, "--feature", help="Covered feature slug."),
) -> None:
    """Deprecated alias for `journey run`; never compiles."""
    project_root = require_specs_root()
    result = run_journeys(project_root, feature=feature)
    _emit_issues(project_root, result.issues)
    emit_summary(
        "journey test",
        "OK" if result.error_count == 0 else "FAIL",
        executed=len(result.executed),
        manual=len(result.manual),
        disabled=len(result.disabled),
        errors=result.error_count,
    )
    raise typer.Exit(0 if result.error_count == 0 else 1)


@journey_app.command(name="impact")
def impact_command(
    changed_files: ChangedFileOption = None,
    feature: str | None = typer.Option(None, "--feature", help="Feature slug to scope."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Analyze changed files against existing journeys."""
    _ = feature
    project_root = require_specs_root()
    impacts = analyze_journey_impacts(project_root, changed_files=changed_files or [])
    if json_output:
        typer.echo(json.dumps({"impacts": [impact.__dict__ for impact in impacts]}))
    else:
        for impact in impacts:
            typer.echo(f"{impact.journey_id}: {impact.reason} -> {impact.recommended_command}")
        emit_summary("journey impact", "OK", impacts=len(impacts))


@journey_app.command(name="list")
def list_command(
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """List valid v2 journeys."""
    project_root = require_specs_root()
    index = build_journey_index(project_root)
    journeys = [
        {"id": journey.journey_id, "features": journey.covered_features}
        for journey in index.journeys.values()
    ]
    if json_output:
        typer.echo(json.dumps({"journeys": journeys}))
    else:
        for item in journeys:
            typer.echo(f"{item['id']} features={','.join(item['features'])}")


@journey_app.command(name="inspect")
def inspect_command(
    journey_id: str,
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Inspect one valid v2 journey."""
    project_root = require_specs_root()
    index = build_journey_index(project_root)
    journey = index.journeys.get(journey_id)
    if journey is None:
        typer.echo(f"Journey not found: {journey_id}", err=True)
        raise typer.Exit(1)
    data = {
        "id": journey.journey_id,
        "features": journey.covered_features,
        "source": relative_to_project(project_root, journey.path),
    }
    typer.echo(json.dumps(data) if json_output else f"{data['id']} {data['source']}")


@journey_app.command(name="migrate")
def migrate_command(
    from_v1: bool = typer.Option(False, "--from-v1", help="Migrate v1 journeys."),
    apply: bool = typer.Option(False, "--apply", help="Write migrated v2 journey files."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Migrate v1 journeys to v2 directories."""
    if not from_v1:
        typer.echo("Nothing to migrate. Pass --from-v1 to inspect legacy journeys.")
        return
    project_root = require_specs_root()
    result = migrate_v1_journeys(project_root, apply=apply)
    if json_output:
        typer.echo(
            json.dumps(
                {
                    "migrated": result.migrated,
                    "issues": [_issue_json(project_root, issue) for issue in result.issues],
                    "applied": apply,
                }
            )
        )
    else:
        _emit_issues(project_root, result.issues)
        action = "migrated" if apply else "would migrate"
        for journey_id in result.migrated:
            typer.echo(f"{action}: {journey_id}")
        emit_summary(
            "journey migrate",
            "OK" if not result.issues else "FAIL",
            migrated=len(result.migrated),
            errors=len(result.issues),
        )
    raise typer.Exit(0 if not result.issues else 1)


@fixtures_app.command(name="scaffold")
def fixtures_scaffold_command() -> None:
    """Scaffold .specs/journeys/fixtures.yaml from existing journey fixtures."""
    # @spec FR-009: journey fixtures scaffold CLI subcommand
    # — .specs/features/060-journey-fixture-bootstrap-contract/spec.md#fr-009
    project_root = require_specs_root()
    if fixtures_contract_path(project_root).exists():
        # Idempotence: the existing contract is never touched; the no-op exits 0
        # so migration v21 stays green on already-scaffolded projects.
        typer.echo("fixtures contract already present")
        emit_summary("journey fixtures scaffold", "OK", scaffolded=0)
        return
    try:
        written = scaffold_fixtures_contract(project_root)
    except OSError as error:
        typer.echo(f"failed to write fixtures contract: {error}", err=True)
        raise typer.Exit(1) from error
    if written is None:
        typer.echo("no fixture journeys found")
        emit_summary("journey fixtures scaffold", "OK", scaffolded=0)
        return
    typer.echo(f"scaffolded: {relative_to_project(project_root, written)}")
    emit_summary("journey fixtures scaffold", "OK", scaffolded=1)


def journey_category_counts(project_root: Path, feature: str | None = None) -> tuple[int, int, int]:
    """Return executable, manual, and disabled journey counts for reports."""
    report = scan_journeys(project_root, feature)
    return report.executable_count, report.manual_count, report.disabled_count


def _emit_issues(project_root: Path, issues: list[JourneyIssue]) -> None:
    """Emit human-readable journey issues."""
    for issue in issues:
        typer.echo(
            f"{issue.severity.value} {issue.code} "
            f"{relative_to_project(project_root, issue.path)}: {issue.message}"
        )


def _issue_json(project_root: Path, issue: JourneyIssue) -> dict[str, str]:
    """Serialize a journey issue for JSON CLI output."""
    return {
        "severity": issue.severity.value,
        "code": issue.code,
        "path": relative_to_project(project_root, issue.path),
        "message": issue.message,
    }


__all__ = ["journey_app", "journey_category_counts", "register"]
