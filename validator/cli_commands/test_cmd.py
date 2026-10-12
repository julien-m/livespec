# LiveSpec traceability anchors
# @spec(FR-012)
# @spec(FR-024)
# @spec(FR-026)

"""``livespec test`` — run tests via the active driver."""

# @spec FR-001: test subcommand — .specs/features/035-unified-cli-surface/spec.md#fr-001
# @spec AC-001: zero-arg run — .specs/features/035-unified-cli-surface/spec.md#ac-001
# @spec AC-003: --mutation flag — .specs/features/035-unified-cli-surface/spec.md#ac-003
# @spec FR-024, FR-026: compiled-only journey gate in livespec test
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#fr-024

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ..cli_exit_codes import EXIT_FAILURE, EXIT_OK
from ..cli_resolvers import read_threshold_from_conventions
from ..journeys.paths import relative_to_project
from ..journeys.runner import run_journeys
from ._common import (
    emit_summary,
    help_epilog,
    require_specs_root,
    resolve_primary_driver,
    run_with_debug,
)
from .journey_cmd import journey_category_counts
from .test_selection import (
    resolve_feature_or_exit,
    run_coverage_step,
    run_mutation_step,
    selected_tests_or_exit,
)


def test_command(
    feature: str | None = typer.Option(
        None,
        "--feature",
        help=(
            "Run only the tests mapped to one feature: its number (035) or full "
            "directory name (035-unified-cli-surface)."
        ),
    ),
    mutation: bool = typer.Option(
        False,
        "--mutation",
        help="Also invoke the driver's mutation capability after coverage.",
    ),
    no_coverage: bool = typer.Option(
        False,
        "--no-coverage",
        help="Skip the coverage capability (only useful with --mutation).",
    ),
    execution_command: str | None = typer.Option(
        None, "--execution-command", help="Capture a resolved test command"
    ),
    acceptance_mapping: Annotated[
        Path | None,
        typer.Option("--acceptance-mapping", help="Generated reviewed acceptance mapping"),
    ] = None,
    prepare_mapping_review: bool = typer.Option(
        False, "--prepare-mapping-review", help="Prepare existing independent test review input"
    ),
    ingest_mapping_review: Annotated[
        Path | None, typer.Option("--ingest-mapping-review", help="Actual raw test reviewer bundle")
    ] = None,
    report_adapter: str = typer.Option(
        "junit", "--report-adapter", help="Structured execution result adapter"
    ),
    debug: bool = typer.Option(False, "--debug", help="Print the full stacktrace on error."),
) -> None:
    """Run driver tests or prepare, ingest and certify mapped execution evidence.

    Args:
        feature: Informational driver scope; required feature slug for execution/review modes.
        mutation: Run the driver's mutation capability after coverage.
        no_coverage: Skip driver coverage, retaining journey checks and optional mutation.
        execution_command: Shell-tokenized test argv captured by the runner, without a shell.
        acceptance_mapping: Project-confined mapping required by execution/review modes.
        prepare_mapping_review: Emit context/schema JSON; exclusive with ingestion and execution.
        ingest_mapping_review: Raw reviewer bundle to validate and persist before certification.
        report_adapter: Execution result format (default junit); unsupported proof cannot certify.
        debug: Print driver-mode exception tracebacks; not accepted in native modes.

    Native modes require exactly one operation, feature and mapping; driver modifiers are
    rejected. Non-default report_adapter is accepted only for execution.

    Returns:
        No value: emits driver summaries or prepared-review, review-receipt or capture JSON.
    Raises:
        typer.Exit: Success or driver failure/missing environment/capability; native modes exit
            1 for invalid inputs, unreadable files, incomplete reviews or unproven execution.
        TypeError: Malformed direct-call inputs outside the native OSError/ValueError boundary.
    Side effects:
        Reads project/review inputs; ingestion writes a review receipt. Execution starts tests
        and persists runner-owned capture/report/receipt files; driver mode runs journeys,
        coverage and optional mutation commands with their declared filesystem effects.

    Example:
        $ livespec test
        Driver: python · Tests: pytest --cov=. --cov-report=lcov:lcov.info
        Coverage: 87.3% (threshold 70.0%) · OK
        LIVESPEC test · OK · driver=python · coverage=87.3 · threshold=70.0
    """
    from .operation_options import check_execution_options

    try:
        native = check_execution_options(
            feature=feature,
            command=execution_command,
            mapping=acceptance_mapping,
            prepare=prepare_mapping_review,
            ingest=ingest_mapping_review,
            adapter=report_adapter,
            mutation=mutation,
            no_coverage=no_coverage,
            debug=debug,
        )
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
    if native:
        _run_execution_io(
            feature,
            execution_command,
            acceptance_mapping,
            prepare_mapping_review,
            ingest_mapping_review,
            report_adapter,
        )

    run_with_debug(
        lambda: _run_test(
            feature=feature,
            mutation=mutation,
            no_coverage=no_coverage,
        ),
        debug=debug,
        subcommand="test",
    )


def register(app: typer.Typer) -> None:
    """Register the ``test`` subcommand."""
    app.command(
        name="test",
        help="Run the active driver's coverage capability.",
        epilog=help_epilog("livespec test --feature 035"),
    )(test_command)


def _run_test(
    *,
    feature: str | None,
    mutation: bool,
    no_coverage: bool,
) -> None:
    """Execute the ``test`` subcommand body (driver mode)."""
    project_root = require_specs_root()
    driver = resolve_primary_driver(project_root)

    typer.echo(f"Driver: {driver.name}")
    test_paths: list[str] | None = None
    if feature:
        # @spec AC-002: Resolve one feature, then its mapped tests
        # — .specs/features/035-unified-cli-surface/spec.md#ac-002
        feature = resolve_feature_or_exit(project_root, feature)
        typer.echo(f"Feature scope: {feature}")
        if not no_coverage:
            # Selection only feeds the coverage capability; --no-coverage skips it.
            test_paths = selected_tests_or_exit(project_root, feature)
            typer.echo(f"Selected tests: {len(test_paths)} file(s)")

    executable_journeys, manual_journeys, disabled_journeys = journey_category_counts(
        project_root,
        feature,
    )
    # @spec FR-012: Separate journey reporting
    # — .specs/features/056-executable-user-journeys/spec.md#fr-012
    typer.echo("Direct tests: driver coverage capability")
    typer.echo(f"Executable user journeys: {executable_journeys}")
    typer.echo(f"Manual tests: {manual_journeys}")
    typer.echo(f"Disabled journeys: {disabled_journeys}")
    journey_run = run_journeys(project_root, feature=feature)
    for issue in journey_run.issues:
        typer.echo(
            f"{issue.severity.value} {issue.code} "
            f"{relative_to_project(project_root, issue.path)}: {issue.message}"
        )
    if journey_run.error_count:
        emit_summary(
            "test",
            "FAIL",
            driver=driver.name,
            journeys=len(journey_run.executed),
            journey_errors=journey_run.error_count,
        )
        raise typer.Exit(EXIT_FAILURE)

    threshold_pct = read_threshold_from_conventions(project_root)
    coverage_pct = (
        None
        if no_coverage
        else run_coverage_step(project_root, driver, feature, test_paths, threshold_pct)
    )

    if mutation:
        run_mutation_step(project_root, driver, feature)

    emit_summary(
        "test",
        "OK",
        driver=driver.name,
        coverage=round(coverage_pct, 2) if coverage_pct is not None else "n/a",
        threshold=threshold_pct,
        mutation="ran" if mutation else "skipped",
        journeys=executable_journeys,
        manual=manual_journeys,
    )
    raise typer.Exit(EXIT_OK)


__all__ = ["register"]


def _run_execution_io(
    feature: str | None,
    execution_command: str | None,
    acceptance_mapping: Path | None,
    prepare_mapping_review: bool,
    ingest_mapping_review: Path | None,
    report_adapter: str,
) -> None:
    from .execution_io import execution_io

    try:
        execution_io(
            require_specs_root(),
            feature,
            command=execution_command,
            mapping_path=acceptance_mapping,
            prepare=prepare_mapping_review,
            ingest=ingest_mapping_review,
            adapter=report_adapter,
        )
    except (OSError, ValueError) as exc:
        typer.echo(f"BLOCKED: {exc}", err=True)
        raise typer.Exit(1) from exc
