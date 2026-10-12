"""Thin ``livespec runtime`` command group: install, pin, upgrade, dev, status, defect.

Handlers parse options, call ``validator.runtime`` services and map domain errors
to exit 1 (usage errors exit 2). ``--json`` payloads go to stdout, diagnostics to stderr.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import NoReturn

import typer

from validator.pipeline import PHASE_MAP
from validator.runtime.defects import DefectRequest, report_defect
from validator.runtime.errors import (
    LiveSpecRuntimeError,
    RuntimeDefectError,
    RuntimeDefectInputError,
)
from validator.runtime.home import (
    executing_root,
    executing_validator,
    require_project_root,
    resolve_home,
)
from validator.runtime.inspection import inspect_project
from validator.runtime.models import JsonObject, SelectionResult
from validator.runtime.project import dev_project, pin_project, upgrade_project
from validator.runtime.snapshot import InstallRequest, install_runtime

runtime_app = typer.Typer(name="runtime", help="Install, pin and inspect pinned LiveSpec runtimes.")

HOME_OPTION = typer.Option(
    None, "--home", help="Runtime home (default $LIVESPEC_HOME, ~/.livespec)."
)
PROJECT_OPTION = typer.Option(None, "--project", help="Project directory (default: cwd).")
JSON_OPTION = typer.Option(False, "--json", help="Print JSON on stdout.")
SOURCE_OPTION = typer.Option(None, "--source", help="LiveSpec git checkout.")
DEV_SOURCE_OPTION = typer.Option(..., "--source", help="LiveSpec checkout to execute.")
# Usage errors share Click's exit code so scripts can tell them from domain failures.
EXIT_USAGE = 2


# @spec FR-009: Runtime group registration
#   — .specs/features/083-pinned-runtime-isolation/spec.md#fr-009
def register(app: typer.Typer) -> None:
    """Register the ``livespec runtime`` command group on ``app``."""
    app.add_typer(runtime_app, name="runtime")


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _fail(exc: LiveSpecRuntimeError) -> NoReturn:
    typer.echo(f"Error: {exc.message}", err=True)
    raise typer.Exit(1) from exc


def _emit(payload: JsonObject, as_json: bool, lines: list[str]) -> None:
    if as_json:
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        return
    for line in lines:
        typer.echo(line)


def _selection_lines(result: SelectionResult) -> list[str]:
    lines = [
        f"{result.mode}: {result.runtime_root} ({'changed' if result.changed else 'no change'})"
    ]
    if result.old_runtime_id is not None:
        lines.append(f"runtime: {result.old_runtime_id} -> {result.lock.get('runtime_id')}")
        if result.migration_required:
            lines.append("migration required: run /spec-migrate")
    lines += [f"retargeted: {path}" for path in result.links.retargeted]
    lines += [f"missing in runtime (unchanged): {path}" for path in result.links.missing]
    return lines


def _emit_selection(result: SelectionResult, as_json: bool) -> None:
    for warning in result.warnings:
        typer.echo(f"Warning: {warning}", err=True)
    _emit(result.to_dict(), as_json, _selection_lines(result))


# @spec FR-001: install CLI — .specs/features/083-pinned-runtime-isolation/spec.md#fr-001
@runtime_app.command("install")
def install_command(
    source: Path | None = SOURCE_OPTION,
    ref: str | None = typer.Option(None, "--ref", help="Commit, branch or tag (default HEAD)."),
    home: Path | None = HOME_OPTION,
    no_activate: bool = typer.Option(False, "--no-activate", help="Leave <home>/current as is."),
    as_json: bool = JSON_OPTION,
) -> None:
    """Install an immutable snapshot of a committed LiveSpec tree."""
    request = InstallRequest(
        home=resolve_home(home),
        python=sys.executable,
        clock=_utc_now,
        source=source,
        ref=ref,
        activate=not no_activate,
    )
    try:
        result = install_runtime(request)
    except LiveSpecRuntimeError as exc:
        _fail(exc)
    lines = [f"{result.status}: {result.runtime_id} at {result.snapshot}", f"shim: {result.shim}"]
    _emit(result.to_dict(), as_json, lines)


# @spec FR-005: pin CLI — .specs/features/083-pinned-runtime-isolation/spec.md#fr-005
@runtime_app.command("pin")
def pin_command(
    project: Path | None = PROJECT_OPTION,
    runtime: str = typer.Option("current", "--runtime", help="Runtime id or current."),
    home: Path | None = HOME_OPTION,
    as_json: bool = JSON_OPTION,
) -> None:
    """Pin the project to an installed, verified runtime."""
    try:
        result = pin_project(project or Path.cwd(), runtime, resolve_home(home))
    except LiveSpecRuntimeError as exc:
        _fail(exc)
    _emit_selection(result, as_json)


# @spec FR-007: upgrade CLI — .specs/features/083-pinned-runtime-isolation/spec.md#fr-007
@runtime_app.command("upgrade")
def upgrade_command(
    project: Path | None = PROJECT_OPTION,
    to: str = typer.Option("current", "--to", help="Runtime id or current."),
    home: Path | None = HOME_OPTION,
    as_json: bool = JSON_OPTION,
) -> None:
    """Move a pinned project to another installed runtime."""
    try:
        result = upgrade_project(project or Path.cwd(), to, resolve_home(home))
    except LiveSpecRuntimeError as exc:
        _fail(exc)
    _emit_selection(result, as_json)


# @spec FR-008: dev CLI — .specs/features/083-pinned-runtime-isolation/spec.md#fr-008
@runtime_app.command("dev")
def dev_command(
    source: Path = DEV_SOURCE_OPTION,
    project: Path | None = PROJECT_OPTION,
    as_json: bool = JSON_OPTION,
) -> None:
    """Declare dev mode: the project executes a LiveSpec checkout."""
    try:
        result = dev_project(project or Path.cwd(), source)
    except LiveSpecRuntimeError as exc:
        _fail(exc)
    _emit_selection(result, as_json)


# @spec FR-012: status CLI — .specs/features/083-pinned-runtime-isolation/spec.md#fr-012
@runtime_app.command("status")
def status_command(
    project: Path | None = PROJECT_OPTION,
    home: Path | None = HOME_OPTION,
    as_json: bool = JSON_OPTION,
) -> None:
    """Report the runtime mode, lock, resolved and executing roots and drift findings."""
    try:
        root = require_project_root(project or Path.cwd())
    except LiveSpecRuntimeError as exc:
        _fail(exc)
    report = inspect_project(root, resolve_home(home), executing_root(), executing_validator())
    lines = [f"mode: {report.mode}", f"executing: {report.executing_root}"]
    lines += [f"{item.severity.value} {item.code}: {item.message}" for item in report.findings]
    _emit(report.to_dict(), as_json, lines)
    raise typer.Exit(1 if report.has_error else 0)


# @spec FR-011: defect CLI — .specs/features/083-pinned-runtime-isolation/spec.md#fr-011
@runtime_app.command("defect")
def defect_command(
    command: str = typer.Option(..., "--command", help="LiveSpec command that failed."),
    error: str = typer.Option(..., "--error", help="Verbatim error text."),
    feature: str | None = typer.Option(None, "--feature", help="Blocked feature slug."),
    phase: str | None = typer.Option(None, "--phase", help="Pipeline phase slug to block."),
    title: str | None = typer.Option(None, "--title", help="Report title (slug source)."),
    project: Path | None = PROJECT_OPTION,
    as_json: bool = JSON_OPTION,
) -> None:
    """Record a LiveSpec tool defect in the project and block the feature phase."""
    if phase is not None and (feature is None or phase not in PHASE_MAP):
        typer.echo("Error: --phase requires --feature and a known phase slug", err=True)
        raise typer.Exit(EXIT_USAGE)
    request = DefectRequest(
        start=project or Path.cwd(),
        command=command,
        error=error,
        home=resolve_home(None),
        clock=_utc_now,
        feature=feature,
        phase=phase,
        title=title,
    )
    try:
        result = report_defect(request)
    except RuntimeDefectInputError as exc:
        typer.echo(f"Error: {exc.message} (nothing written)", err=True)
        raise typer.Exit(EXIT_USAGE) from exc
    except RuntimeDefectError as exc:
        typer.echo(f"Error: {exc.message} (report kept: {exc.report_path})", err=True)
        raise typer.Exit(1) from exc
    except LiveSpecRuntimeError as exc:
        _fail(exc)
    _emit(result.to_dict(), as_json, [f"report: {result.report}"])
