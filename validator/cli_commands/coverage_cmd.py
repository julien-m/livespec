"""``livespec coverage`` — patch coverage vs base branch."""

# @spec FR-002: coverage subcommand — .specs/features/035-unified-cli-surface/spec.md#fr-002
# @spec AC-004: auto base detection — .specs/features/035-unified-cli-surface/spec.md#ac-004
# @spec AC-005: --base override — .specs/features/035-unified-cli-surface/spec.md#ac-005
# @spec EC-002: no diff vs base exits 0 — .specs/features/035-unified-cli-surface/spec.md#ec-002

from __future__ import annotations

from pathlib import Path

import typer

from ..cli_exit_codes import (
    EXIT_CAPABILITY_UNSUPPORTED,
    EXIT_COVERAGE_FAIL,
    EXIT_MISSING_SPECS,
    EXIT_OK,
)
from ..cli_resolvers import detect_base_branch, read_threshold_from_conventions
from ..drivers.patch_coverage import (
    compute_patch_coverage,
    evaluate_patch_gate,
    git_diff,
    summarise_patch_coverage,
)
from ._common import (
    emit_summary,
    require_specs_root,
    resolve_primary_driver,
    run_with_debug,
)


def coverage_command(
    base: str | None = typer.Option(
        None,
        "--base",
        help=(
            "Base branch / ref to diff against. When omitted, the CLI "
            "auto-detects in this order: origin/main, origin/master, "
            "develop, dev, main, master."
        ),
    ),
    threshold: float | None = typer.Option(
        None,
        "--threshold",
        help=(
            "Patch coverage threshold (percentage 0-100). Defaults to the "
            "value declared in .conventions/index.md, or 70 otherwise."
        ),
    ),
    report_path: Path | None = typer.Option(  # noqa: B008
        None,
        "--report-path",
        help=("lcov.info path (defaults to the active driver's coverage.report_path field)."),
    ),
    debug: bool = typer.Option(False, "--debug", help="Print the full stacktrace on error."),
) -> None:
    """Compute patch coverage and print a summary plus a CI line.

    Example:
        $ livespec coverage --base origin/main
        Patch coverage: 92.5% (74/80 changed lines covered)
        Gate PASSED — all files >= 70%.
        LIVESPEC coverage · OK · base=origin/main · overall=0.925 · failing=0
    """
    run_with_debug(
        lambda: _run_coverage(
            base=base,
            threshold=threshold,
            report_path=report_path,
        ),
        debug=debug,
        subcommand="coverage",
        fail_exit_code=EXIT_COVERAGE_FAIL,
    )


def register(app: typer.Typer) -> None:
    """Register the ``coverage`` subcommand."""
    app.command(name="coverage", help="Compute patch coverage vs the base branch.")(
        coverage_command
    )


def _run_coverage(
    *,
    base: str | None,
    threshold: float | None,
    report_path: Path | None,
) -> None:
    """Execute the ``coverage`` subcommand body."""
    project_root = require_specs_root()
    driver = resolve_primary_driver(project_root)

    base_ref = base or detect_base_branch(project_root)
    if base_ref is None:
        typer.echo(
            "Error: no base branch detected (tried origin/main, origin/master, "
            "develop, dev, main, master). Pass --base BRANCH to override.",
            err=True,
        )
        emit_summary("coverage", "ERROR", reason="no_base_branch")
        raise typer.Exit(EXIT_MISSING_SPECS)

    threshold_pct = (
        threshold if threshold is not None else read_threshold_from_conventions(project_root)
    )
    threshold_ratio = threshold_pct / 100.0

    diff_text = git_diff(base_ref, project_root=project_root)

    if not diff_text.strip():
        # EC-002 — no diff vs base, exit cleanly.
        typer.echo(f"Patch coverage: no changes since base {base_ref}.")
        emit_summary(
            "coverage",
            "OK",
            base=base_ref,
            files_changed=0,
            overall=1.0,
            threshold=threshold_pct,
        )
        raise typer.Exit(EXIT_OK)

    cap = driver.get_capability("coverage")
    if cap is None or cap.report_path is None:
        typer.echo(
            f"Error: driver {driver.name!r} does not declare a coverage capability "
            "with a report_path. Pass --report-path PATH to override.",
            err=True,
        )
        emit_summary("coverage", "ERROR", reason="no_coverage_capability")
        raise typer.Exit(EXIT_CAPABILITY_UNSUPPORTED)

    lcov_path = report_path or Path(cap.report_path)
    if not lcov_path.is_absolute():
        lcov_path = project_root / lcov_path

    if not lcov_path.exists():
        typer.echo(
            f"Error: coverage report not found at {lcov_path}. Run `livespec test` "
            "first or pass --report-path PATH.",
            err=True,
        )
        emit_summary("coverage", "ERROR", reason="lcov_missing")
        raise typer.Exit(EXIT_COVERAGE_FAIL)

    report = compute_patch_coverage(
        lcov_path,
        diff_text,
        project_root=project_root,
    )
    typer.echo(summarise_patch_coverage(report, threshold=threshold_ratio))

    failing = evaluate_patch_gate(report.files, threshold_ratio)
    if failing:
        emit_summary(
            "coverage",
            "FAIL",
            base=base_ref,
            overall=round(report.overall_ratio, 4),
            threshold=threshold_pct,
            failing=len(failing),
        )
        raise typer.Exit(EXIT_COVERAGE_FAIL)

    emit_summary(
        "coverage",
        "OK",
        base=base_ref,
        overall=round(report.overall_ratio, 4),
        threshold=threshold_pct,
        failing=0,
    )


__all__ = ["register"]
