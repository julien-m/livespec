"""Driver-mode steps of ``livespec test``: feature selection, coverage, mutation."""

# @spec AC-002: Feature-scoped selection — .specs/features/035-unified-cli-surface/spec.md#ac-002
# @spec AC-011: Run failure 1, missing configuration 3
# — .specs/features/035-unified-cli-surface/spec.md#ac-011

from __future__ import annotations

from pathlib import Path

import typer

from ..cli_exit_codes import EXIT_CONFIG, EXIT_FAILURE, EXIT_USAGE
from ..cli_resolvers import resolve_feature_dir
from ..drivers.patch_coverage import parse_lcov
from ..drivers.runner import run_capability
from ..drivers.schemas import CapabilityNotImplementedError, DriverManifest
from ..exceptions import DriverTestSelectionError, FeatureResolutionError
from ..journeys.paths import relative_to_project
from ..journeys.runner import run_journeys
from ..selector import SmartTestSelector
from ._common import emit_summary
from .journey_cmd import journey_category_counts


def resolve_feature_or_exit(project_root: Path, value: str) -> str:
    """Return the feature slug for ``--feature`` or exit with the usage code.

    Args:
        project_root: Project root containing ``.specs/features/``.
        value: The ``--feature`` argument (number or full directory name).

    Returns:
        The resolved feature directory name.

    Raises:
        typer.Exit: :data:`EXIT_USAGE` when zero or several directories match.
    """
    try:
        return resolve_feature_dir(project_root, value).name
    except FeatureResolutionError as exc:
        typer.echo(f"Error: {exc}", err=True)
        emit_summary("test", "ERROR", reason="feature_unresolved")
        raise typer.Exit(EXIT_USAGE) from exc


def selected_tests_or_exit(project_root: Path, feature: str) -> list[str]:
    """Return the test files mapped to ``feature`` or exit with the configuration code.

    Args:
        project_root: Project root containing ``.specs/``.
        feature: Resolved feature directory name.

    Returns:
        Project-relative test file paths, deduplicated in selector order.

    Raises:
        typer.Exit: :data:`EXIT_CONFIG` when no test is mapped to the feature.
    """
    selector = SmartTestSelector(project_root / ".specs")
    paths: list[str] = []
    for ref in selector.tests_for_features({feature}):
        if ref["test_file"] not in paths:
            paths.append(ref["test_file"])
    if not paths:
        typer.echo(
            f"Error: no test is mapped to feature {feature!r} (implementation.md or tests/). "
            "Map its tests or run without --feature.",
            err=True,
        )
        emit_summary("test", "ERROR", feature=feature, reason="no_selected_tests")
        raise typer.Exit(EXIT_CONFIG)
    return paths


def percent_from_lcov(lcov_path: Path) -> float | None:
    """Compute a global line-coverage percentage from an ``lcov.info`` file.

    Args:
        lcov_path: Path to the lcov report.

    Returns:
        Percentage (0-100) or ``None`` when the file has no ``DA:`` records.
    """
    total = 0
    covered = 0
    for line_map in parse_lcov(lcov_path).values():
        for hit in line_map.values():
            total += 1
            if hit:
                covered += 1
    if total == 0:
        return None
    return (covered / total) * 100.0


def run_coverage_step(
    project_root: Path,
    driver: DriverManifest,
    feature: str | None,
    test_paths: list[str] | None,
    threshold_pct: float,
) -> float | None:
    """Run the coverage capability; exit 1 on failure, 3 when unsupported (AC-011)."""
    try:
        result = run_capability(
            driver,
            "coverage",
            project_root=project_root,
            feature=feature,
            test_paths=test_paths,
        )
    except CapabilityNotImplementedError:
        typer.echo(f"Error: driver {driver.name!r} has no coverage capability.", err=True)
        emit_summary("test", "FAIL", driver=driver.name, reason="no_coverage")
        raise typer.Exit(EXIT_CONFIG) from None
    except DriverTestSelectionError as exc:
        typer.echo(f"Error: {exc}", err=True)
        emit_summary("test", "FAIL", driver=driver.name, reason="no_test_selection")
        raise typer.Exit(EXIT_CONFIG) from exc

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
        raise typer.Exit(EXIT_FAILURE)

    coverage_pct = _declared_lcov_percent(project_root, result.report_path)
    coverage_str = f"{coverage_pct:.1f}%" if coverage_pct is not None else "not parsed"
    failed = coverage_pct is not None and coverage_pct < threshold_pct
    verdict = "FAIL" if failed else "OK"
    typer.echo(f"Coverage: {coverage_str} (threshold {threshold_pct:.1f}%) · {verdict}")
    if failed:
        emit_summary(
            "test",
            "FAIL",
            driver=driver.name,
            coverage=round(coverage_pct or 0.0, 2),
            threshold=threshold_pct,
        )
        raise typer.Exit(EXIT_FAILURE)
    return coverage_pct


def _declared_lcov_percent(project_root: Path, report_path: str | None) -> float | None:
    """Best-effort coverage percentage from the lcov report the driver declares."""
    if not report_path:
        return None
    lcov_path = Path(report_path)
    if not lcov_path.is_absolute():
        lcov_path = project_root / lcov_path
    return percent_from_lcov(lcov_path) if lcov_path.exists() else None


def run_mutation_step(project_root: Path, driver: DriverManifest, feature: str | None) -> None:
    """Run the optional mutation capability; exit 3 when the driver lacks it."""
    try:
        mut = run_capability(driver, "mutation", project_root=project_root, feature=feature)
    except CapabilityNotImplementedError:
        typer.echo(
            f"Note: driver {driver.name!r} does not implement mutation testing.",
            err=True,
        )
        emit_summary("test", "WARN", driver=driver.name, mutation="unsupported")
        raise typer.Exit(EXIT_CONFIG) from None
    if mut.stdout:
        typer.echo(mut.stdout)
    if mut.stderr:
        typer.echo(mut.stderr, err=True)
    if mut.exit_code:
        emit_summary("test", "FAIL", driver=driver.name, exit_code=mut.exit_code)
        raise typer.Exit(EXIT_FAILURE)


__all__ = [
    "percent_from_lcov",
    "resolve_feature_or_exit",
    "run_coverage_step",
    "run_mutation_step",
    "selected_tests_or_exit",
]


def run_driver_journeys(
    project_root: Path, feature: str | None, driver_name: str
) -> tuple[int, int]:
    """Report and run selected journeys inside the driver's shared command envelope."""
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
            driver=driver_name,
            journeys=len(journey_run.executed),
            journey_errors=journey_run.error_count,
        )
        raise typer.Exit(EXIT_FAILURE)

    return executable_journeys, manual_journeys
