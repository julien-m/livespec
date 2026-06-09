"""``livespec mutation`` — run mutation testing via the active driver."""

# @spec FR-004: mutation subcommand — .specs/features/035-unified-cli-surface/spec.md#fr-004
# @spec AC-008: historical Markdown report — .specs/features/035-unified-cli-surface/spec.md#ac-008
# @spec EC-004: capability absent → exit 4 — .specs/features/035-unified-cli-surface/spec.md#ec-004

from __future__ import annotations

import datetime as _dt
from pathlib import Path

import typer

from ..cli_exit_codes import (
    EXIT_CAPABILITY_UNSUPPORTED,
    EXIT_COVERAGE_FAIL,
    EXIT_OK,
)
from ..cli_resolvers import read_threshold_from_conventions
from ..drivers.mutation_report import run_mutation, write_mutation_report
from ._common import (
    emit_summary,
    require_specs_root,
    resolve_primary_driver,
    run_with_debug,
)


def mutation_command(
    threshold: float | None = typer.Option(
        None,
        "--threshold",
        help=("Mutation kill-rate threshold (0-100). Defaults to the conventions value or 70."),
    ),
    report_path: Path | None = typer.Option(  # noqa: B008
        None,
        "--report-path",
        help=("Markdown report destination. Defaults to .specs/reports/mutation-YYYY-MM-DD.md."),
    ),
    debug: bool = typer.Option(False, "--debug", help="Print the full stacktrace on error."),
) -> None:
    """Run mutation testing and append a historical Markdown report.

    Example:
        $ livespec mutation
        Mutation: python · kill_rate=78.0% · threshold=70.0% · OK
        Report: .specs/reports/mutation-2026-05-07.md
        LIVESPEC mutation · OK · driver=python · kill_rate=78.0 · threshold=70.0
    """
    run_with_debug(
        lambda: _run_mutation(threshold=threshold, report_path=report_path),
        debug=debug,
        subcommand="mutation",
        fail_exit_code=EXIT_COVERAGE_FAIL,
    )


def register(app: typer.Typer) -> None:
    """Register the ``mutation`` subcommand."""
    app.command(
        name="mutation",
        help="Run mutation testing using the active driver.",
    )(mutation_command)


def _run_mutation(*, threshold: float | None, report_path: Path | None) -> None:
    """Execute the ``mutation`` subcommand body."""
    project_root = require_specs_root()
    driver = resolve_primary_driver(project_root)

    threshold_pct = (
        threshold if threshold is not None else read_threshold_from_conventions(project_root)
    )

    today = _dt.date.today().isoformat()
    target_path = report_path or (project_root / ".specs" / "reports" / f"mutation-{today}.md")
    target_path.parent.mkdir(parents=True, exist_ok=True)

    result = run_mutation(
        driver,
        project_root=project_root,
        report_path=None,
    )
    if result is None:
        typer.echo(
            f"Error: driver {driver.name!r} does not implement mutation testing.",
            err=True,
        )
        emit_summary("mutation", "FAIL", driver=driver.name, reason="unsupported")
        raise typer.Exit(EXIT_CAPABILITY_UNSUPPORTED)

    # Apply threshold and write report.
    from dataclasses import replace

    gated = replace(
        result,
        # ``MutationResult.kill_rate`` is already stored as a percentage (78.0, not 0.78),
        # so the gate must compare against the percentage threshold in the same unit.
        threshold=threshold_pct,
        gate_failed=result.kill_rate < threshold_pct,
    )
    write_mutation_report(gated, target_path, project_name=project_root.name)

    # ``MutationResult.kill_rate`` is already stored in percentage units, so the
    # CLI must render and compare it directly instead of multiplying by 100 again.
    kill_pct = gated.kill_rate
    verdict = "FAIL" if gated.gate_failed else "OK"
    typer.echo(
        f"Mutation: {driver.name} · kill_rate={kill_pct:.1f}% · "
        f"threshold={threshold_pct:.1f}% · {verdict}"
    )
    typer.echo(f"Report: {target_path}")

    emit_summary(
        "mutation",
        verdict,
        driver=driver.name,
        kill_rate=round(kill_pct, 2),
        threshold=threshold_pct,
        report=str(target_path),
    )
    raise typer.Exit(EXIT_OK if not gated.gate_failed else EXIT_COVERAGE_FAIL)


__all__ = ["register"]
