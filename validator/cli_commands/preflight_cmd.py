"""``livespec preflight`` — verify (and optionally install) tooling."""

# @spec FR-005: preflight subcommand — .specs/features/035-unified-cli-surface/spec.md#fr-005
# @spec AC-009: read-only status table — .specs/features/035-unified-cli-surface/spec.md#ac-009
# @spec AC-010: --fix invokes feature 034 — .specs/features/035-unified-cli-surface/spec.md#ac-010

from __future__ import annotations

from pathlib import Path

import typer

from .. import preflight_autofix
from ..cli_exit_codes import (
    EXIT_OK,
    EXIT_PREFLIGHT_FAIL,
)
from ._common import emit_summary, require_specs_root, run_with_debug


def preflight_command(
    fix: bool = typer.Option(
        False,
        "--fix",
        help="Auto-install missing tools per the manifest (Feature 034).",
    ),
    full: bool = typer.Option(
        False,
        "--full",
        help="Disable smart scoping — verify every item, not just the impacted ones.",
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Print the full stacktrace on error."
    ),
) -> None:
    """Run the project preflight check.

    Example:
        $ livespec preflight
        Tool                Status      Auto-installable
        pytest-cov          ok          yes
        mutmut              missing     yes
        LIVESPEC preflight · FAIL · ok=1 · missing=1
    """
    run_with_debug(
        lambda: _run_preflight(fix=fix, full=full),
        debug=debug,
        subcommand="preflight",
        fail_exit_code=EXIT_PREFLIGHT_FAIL,
    )


def register(app: typer.Typer) -> None:
    """Register the ``preflight`` subcommand."""
    app.command(
        name="preflight",
        help="Verify the preflight manifest (read-only or with --fix).",
    )(preflight_command)


def _run_preflight(*, fix: bool, full: bool) -> None:
    """Execute the ``preflight`` subcommand body."""
    project_root = require_specs_root()
    manifest_path = project_root / ".specs" / "preflight.md"

    if not manifest_path.exists():
        typer.echo(
            f"Error: {manifest_path} not found. "
            "Run /spec.preflight --regenerate to generate it.",
            err=True,
        )
        emit_summary("preflight", "FAIL", reason="manifest_missing")
        raise typer.Exit(EXIT_PREFLIGHT_FAIL)

    items = preflight_autofix.parse_preflight_manifest(
        manifest_path.read_text(encoding="utf-8")
    )
    if not items:
        typer.echo("Preflight: no fixable items declared in manifest.")
        emit_summary("preflight", "OK", items=0)
        raise typer.Exit(EXIT_OK)

    if fix:
        _run_fix_mode(project_root, items, full=full)
    else:
        _run_verify_mode(items)


def _run_verify_mode(items: list[preflight_autofix.PreflightItem]) -> None:
    """Read-only verification — print a table and emit the summary."""
    rows: list[tuple[str, str, str]] = [("Tool", "Status", "Auto-installable")]
    ok_count = 0
    missing_count = 0
    for item in items:
        is_ok = preflight_autofix.verify_item(item)
        if is_ok:
            ok_count += 1
            status = "ok"
        else:
            missing_count += 1
            status = "missing"
        auto = "yes" if item.safe_for_auto else "no"
        rows.append((item.name, status, auto))

    widths = [max(len(row[i]) for row in rows) for i in range(3)]
    for i, row in enumerate(rows):
        typer.echo("  ".join(cell.ljust(widths[idx]) for idx, cell in enumerate(row)))
        if i == 0:
            typer.echo("  ".join("-" * w for w in widths))

    if missing_count:
        emit_summary(
            "preflight",
            "FAIL",
            ok=ok_count,
            missing=missing_count,
        )
        raise typer.Exit(EXIT_PREFLIGHT_FAIL)
    emit_summary("preflight", "OK", ok=ok_count, missing=0)


def _run_fix_mode(
    project_root: Path,
    items: list[preflight_autofix.PreflightItem],
    *,
    full: bool,
) -> None:
    """Delegate to ``preflight_autofix.run_fix`` and surface the summary."""
    results = preflight_autofix.run_fix(
        items,
        repo=project_root,
        full=full,
        auto=True,
        dry_run=False,
    )
    typer.echo(preflight_autofix.render_summary(results))

    raw_exit = preflight_autofix.exit_code_for(results)
    failed = sum(1 for r in results if r.status == "failed")
    manual = sum(1 for r in results if r.status == "manual_required")
    installed = sum(1 for r in results if r.status == "installed")

    if raw_exit != 0:
        emit_summary(
            "preflight",
            "FAIL",
            failed=failed,
            manual_required=manual,
            installed=installed,
        )
        raise typer.Exit(EXIT_PREFLIGHT_FAIL)

    emit_summary(
        "preflight",
        "OK",
        failed=0,
        manual_required=manual,
        installed=installed,
    )


__all__ = ["register"]
