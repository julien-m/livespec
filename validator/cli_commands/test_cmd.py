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

from ..cli_exit_codes import (
    EXIT_CAPABILITY_UNSUPPORTED,
    EXIT_COVERAGE_FAIL,
    EXIT_OK,
)
from ..cli_resolvers import read_threshold_from_conventions
from ..drivers.patch_coverage import parse_lcov
from ..drivers.runner import run_capability
from ..drivers.schemas import CapabilityNotImplementedError
from ..journeys.paths import relative_to_project
from ..journeys.runner import run_journeys
from ._common import (
    emit_summary,
    require_specs_root,
    resolve_primary_driver,
    run_with_debug,
)
from .journey_cmd import journey_category_counts


def test_command(
    feature: str | None = typer.Option(
        None,
        "--feature",
        help=(
            "Feature slug (e.g. 035-unified-cli-surface). "
            "Reserved for future smart-selection integration (feature 033)."
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
        fail_exit_code=EXIT_COVERAGE_FAIL,
    )


def register(app: typer.Typer) -> None:
    """Register the ``test`` subcommand."""
    app.command(name="test", help="Run the active driver's coverage capability.")(test_command)


def _run_test(
    *,
    feature: str | None,
    mutation: bool,
    no_coverage: bool,
) -> None:
    """Execute the ``test`` subcommand body."""
    project_root = require_specs_root()
    driver = resolve_primary_driver(project_root)

    typer.echo(f"Driver: {driver.name}")
    if feature:
        typer.echo(f"Feature scope: {feature} (informational)")

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
        raise typer.Exit(EXIT_COVERAGE_FAIL)

    coverage_pct: float | None = None
    threshold_pct = read_threshold_from_conventions(project_root)

    if not no_coverage:
        try:
            result = run_capability(driver, "coverage", project_root=project_root, feature=feature)
        except CapabilityNotImplementedError:
            typer.echo(f"Error: driver {driver.name!r} has no coverage capability.", err=True)
            emit_summary("test", "FAIL", driver=driver.name, reason="no_coverage")
            raise typer.Exit(EXIT_CAPABILITY_UNSUPPORTED) from None

        if result.execution_receipt_path:
            typer.echo(f"Execution receipt: {result.execution_receipt_path}")
        for gap in result.certification_gaps:
            typer.echo(f"Certification gap: {gap}")
        if result.stdout:
            typer.echo(result.stdout)
        if result.stderr:
            typer.echo(result.stderr, err=True)

        if result.exit_code != 0:
            emit_summary(
                "test",
                "FAIL",
                driver=driver.name,
                exit_code=result.exit_code,
                threshold=threshold_pct,
            )
            raise typer.Exit(EXIT_COVERAGE_FAIL)

        # Best-effort coverage percentage: parse lcov when the driver declares one.
        if result.report_path:
            lcov_path = Path(result.report_path)
            if not lcov_path.is_absolute():
                lcov_path = project_root / lcov_path
            if lcov_path.exists():
                coverage_pct = _percent_from_lcov(lcov_path)

        coverage_str = f"{coverage_pct:.1f}%" if coverage_pct is not None else "not parsed"
        verdict = "OK"
        if coverage_pct is not None and coverage_pct < threshold_pct:
            verdict = "FAIL"
        typer.echo(f"Coverage: {coverage_str} (threshold {threshold_pct:.1f}%) · {verdict}")
        if verdict == "FAIL":
            emit_summary(
                "test",
                "FAIL",
                driver=driver.name,
                coverage=round(coverage_pct or 0.0, 2),
                threshold=threshold_pct,
            )
            raise typer.Exit(EXIT_COVERAGE_FAIL)

    if mutation:
        try:
            mut = run_capability(driver, "mutation", project_root=project_root, feature=feature)
        except CapabilityNotImplementedError:
            typer.echo(
                f"Note: driver {driver.name!r} does not implement mutation testing.",
                err=True,
            )
            emit_summary(
                "test",
                "WARN",
                driver=driver.name,
                mutation="unsupported",
            )
            raise typer.Exit(EXIT_CAPABILITY_UNSUPPORTED) from None
        if mut.stdout:
            typer.echo(mut.stdout)
        if mut.stderr:
            typer.echo(mut.stderr, err=True)

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


def _percent_from_lcov(lcov_path: Path) -> float | None:
    """Compute a global line-coverage percentage from an ``lcov.info`` file.

    Args:
        lcov_path: Path to the lcov report.

    Returns:
        Percentage (0-100) or ``None`` when the file has no ``DA:`` records.
    """
    data = parse_lcov(lcov_path)
    total = 0
    covered = 0
    for line_map in data.values():
        for hit in line_map.values():
            total += 1
            if hit:
                covered += 1
    if total == 0:
        return None
    return (covered / total) * 100.0


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
