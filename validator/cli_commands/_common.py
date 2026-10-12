"""Shared helpers for the unified ``livespec`` subcommands."""

# @spec FR-008: Single-line errors unless --debug
#               .specs/features/035-unified-cli-surface/spec.md#fr-008
# @spec FR-009: Structured CI summary
#               .specs/features/035-unified-cli-surface/spec.md#fr-009

from __future__ import annotations

import traceback
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import TypeVar

import typer

from ..cli_exit_codes import EXIT_CONFIG, EXIT_FAILURE, EXIT_INTERRUPTED, EXIT_MISSING_SPECS
from ..cli_resolvers import detect_specs_root
from ..drivers.degradation import format_degradation_message
from ..drivers.registry import DriverRegistry
from ..drivers.schemas import DriverManifest
from ..drivers.test_config import pick_primary_driver

T = TypeVar("T")


def require_specs_root(start: Path | None = None) -> Path:
    """Return the project root or exit with :data:`EXIT_MISSING_SPECS`.

    Args:
        start: Where to begin the upward search. Defaults to the current
            working directory.

    Returns:
        The directory that contains ``.specs/``.

    Raises:
        typer.Exit: When ``.specs/`` cannot be located.
    """
    root = detect_specs_root(start)
    if root is None:
        typer.echo(
            "Error: .specs/ directory not found — run /spec-init in your project root.",
            err=True,
        )
        raise typer.Exit(EXIT_MISSING_SPECS)
    return root


def resolve_primary_driver(project_root: Path) -> DriverManifest:
    """Discover drivers and pick the primary one for ``project_root``.

    Args:
        project_root: Project root used for driver detection.

    Returns:
        The manifest selected by :func:`pick_primary_driver`.

    Raises:
        typer.Exit: When no driver matches the project (exit code
            :data:`EXIT_CONFIG`).
    """
    registry = DriverRegistry(project_root)
    matching = registry.discover()
    if not matching:
        typer.echo(format_degradation_message(project_root), err=True)
        raise typer.Exit(EXIT_CONFIG)
    primary = pick_primary_driver(matching, project_root)
    if primary is None:
        typer.echo(format_degradation_message(project_root), err=True)
        raise typer.Exit(EXIT_CONFIG)
    return primary


def format_summary_line(subcommand: str, status: str, **fields: object) -> str:
    """Render the structured one-line summary for CI logs (FR-009).

    Args:
        subcommand: The name of the subcommand emitting the summary.
        status: A short verdict (``OK``, ``FAIL``, ``BLOCKED``…).
        **fields: Extra ``key=value`` pairs appended in insertion order.

    Returns:
        A line of the form ``LIVESPEC <subcommand> · <status> · k=v · k=v``.
    """
    parts = [f"LIVESPEC {subcommand}", status]
    parts.extend(f"{key}={value}" for key, value in fields.items())
    return " · ".join(parts)


def emit_summary(
    subcommand: str, status: str, *, to_stderr: bool = False, **fields: object
) -> None:
    """Print the structured CI summary (FR-009).

    Args:
        subcommand: The name of the subcommand emitting the summary.
        status: A short verdict (``OK``, ``FAIL``, ``ERROR``…).
        to_stderr: Write to stderr so a ``--json`` stdout stays valid JSON (AC-012).
        **fields: Extra ``key=value`` pairs appended in insertion order.
    """
    typer.echo(format_summary_line(subcommand, status, **fields), err=to_stderr)


def help_epilog(example: str) -> str:
    """Return the ``--help`` epilog carrying one runnable example (AC-013).

    Args:
        example: Full command line starting with ``livespec <command>``.

    Returns:
        The epilog text rendered after the options panel.
    """
    # @spec AC-013: One example per command — .specs/features/035-unified-cli-surface/spec.md#ac-013
    return f"Example: {example}"


def run_with_debug(
    func: Callable[[], T],
    *,
    debug: bool,
    subcommand: str,
) -> T:
    """Execute ``func`` with the standard error-handling wrapper.

    Generic exceptions are caught and surfaced as a one-line message unless
    ``debug`` is true, in which case the full stacktrace is printed before the
    exit. ``typer.Exit`` is re-raised verbatim so callers drive the exit code.

    Args:
        func: Callable executing the subcommand body.
        debug: Whether to surface the full Python stacktrace on failure.
        subcommand: Subcommand name used in the structured summary.

    Returns:
        Whatever ``func`` returns when it completes successfully.

    Raises:
        typer.Exit: Re-raised from ``func``, :data:`EXIT_INTERRUPTED` on Ctrl+C,
            or :data:`EXIT_FAILURE` for an unexpected exception (AC-011).
    """
    try:
        return func()
    except typer.Exit:
        raise
    except KeyboardInterrupt:
        typer.echo("\nInterrupted.", err=True)
        raise typer.Exit(EXIT_INTERRUPTED) from None
    except Exception as exc:  # CLI boundary — surface generic errors as one line
        if debug:
            typer.echo(traceback.format_exc(), err=True)
        else:
            typer.echo(f"Error: {exc}", err=True)
        emit_summary(subcommand, "ERROR", reason=type(exc).__name__)
        raise typer.Exit(EXIT_FAILURE) from exc


def join_capabilities(driver: DriverManifest) -> str:
    """Render a comma-separated list of implemented capabilities."""
    return ",".join(driver.implemented_capabilities()) or "-"


def coalesce_paths(paths: Iterable[Path | None]) -> Sequence[Path]:
    """Filter ``None`` entries while preserving order — small typing helper."""
    return [p for p in paths if p is not None]


__all__ = [
    "coalesce_paths",
    "emit_summary",
    "format_summary_line",
    "help_epilog",
    "join_capabilities",
    "require_specs_root",
    "resolve_primary_driver",
    "run_with_debug",
]
