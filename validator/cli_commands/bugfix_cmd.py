"""Thin ``livespec bugfix`` command group: capture, gate, record (feature 084).

Handlers parse options, call ``validator.bugfix`` services and map outcomes to exit
codes: 0 eligible or observed, 1 fallback or unobserved, 2 usage, 3 configuration.
"""

from __future__ import annotations

import json
import os
import shlex
from datetime import date
from pathlib import Path
from typing import Annotated, NoReturn

import typer

from validator.bugfix.gate import GateRequest, evaluate_gate
from validator.bugfix.models import BugfixConfigError, GateReport
from validator.bugfix.receipts import observe
from validator.bugfix.record import record_bugfix
from validator.execution_capture import capture_execution
from validator.identity import SLUG_REGEX

from ._common import require_specs_root

bugfix_app = typer.Typer(name="bugfix", help="Bugfix lane: RED/GREEN receipts and scoped gate.")

EXIT_USAGE = 2  # Shares Click's usage exit code so scripts can tell it from a fallback.
EXIT_CONFIG = 3  # Constitution principle 4: configuration error.
FEATURE = Annotated[str, typer.Option("--feature", help="Owner feature slug.")]
RED = Annotated[Path, typer.Option("--red", help="RED execution receipt path.")]
REQUIREMENT = Annotated[
    list[str] | None, typer.Option("--requirement", help="Cited FR/AC/SC id (repeatable).")
]
BASE = Annotated[str, typer.Option("--base", help="Base git revision of the bugfix diff.")]
JSON_OUT = Annotated[bool, typer.Option("--json", help="Print JSON on stdout.")]


# @spec FR-001: Bugfix command group
#   — .specs/features/084-bugfix-lane/spec.md#fr-001
def register(app: typer.Typer) -> None:
    """Register the ``livespec bugfix`` command group on ``app``."""
    app.add_typer(bugfix_app, name="bugfix")


def _usage(message: str) -> NoReturn:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(EXIT_USAGE)


# @spec FR-002: Runner-owned RED/GREEN capture
#   — .specs/features/084-bugfix-lane/spec.md#fr-002
@bugfix_app.command("capture")
def capture_command(
    feature: FEATURE,
    expect: Annotated[str, typer.Option("--expect", help="red or green.")],
    command: Annotated[str, typer.Option("--command", help="Test command (no shell).")],
    as_json: JSON_OUT = False,
) -> None:
    """Run the test command once through the runner-owned capture and check the outcome."""
    root = require_specs_root()
    if expect not in ("red", "green"):
        _usage("--expect must be red or green")
    if not SLUG_REGEX.fullmatch(feature) or not (root / ".specs/features" / feature).is_dir():
        _usage(f"unknown feature {feature!r}")
    result = capture_execution(
        shlex.split(command),
        project_root=root,
        feature=feature,
        adapter="junit",
        env=dict(os.environ),
    )
    _, gaps = observe(root, feature, Path(result.receipt_path), expect)
    _emit_capture(result.receipt_path, expect, result.exit_code, gaps, as_json)
    raise typer.Exit(0 if not gaps else 1)


def _emit_capture(
    receipt: str, expect: str, exit_code: int, gaps: list[str], as_json: bool
) -> None:
    payload = {
        "receipt_path": receipt,
        "expected": expect,
        "observed": not gaps,
        "exit_code": exit_code,
        "gaps": gaps,
    }
    if as_json:
        typer.echo(json.dumps(payload))
        return
    typer.echo(f"Receipt: {receipt}")
    typer.echo(f"Expected {expect}: {'observed' if not gaps else 'NOT observed'}")
    for gap in gaps:
        typer.echo(f"  - {gap}")


def _emit(report: GateReport, as_json: bool) -> None:
    if as_json:
        typer.echo(json.dumps(report.to_json()))
        return
    typer.echo(f"Bugfix gate: {report.verdict}")
    for reason in report.reasons:
        typer.echo(f"  - {reason.code}: {reason.detail}")
    if report.regression_tests:
        typer.echo("Regression tests: " + ", ".join(report.regression_tests))
    if report.closing:
        limits = report.limits
        typer.echo(
            f"Counted diff: {len(report.counted_files)}/{limits.max_files} files, "
            f"{report.counted_lines}/{limits.max_lines} lines"
        )
    if report.reasons:
        typer.echo(f"Fallback (complete gate): {report.fallback_command}")


def _request(
    feature: str, red: Path, green: Path | None, requirement: list[str] | None, base: str
) -> GateRequest:
    root = require_specs_root()
    return GateRequest(root, feature, red, green, tuple(requirement or ()), base)


# @spec FR-009: Explicit fallback output
#   — .specs/features/084-bugfix-lane/spec.md#fr-009
@bugfix_app.command("gate")
def gate_command(
    feature: FEATURE,
    red: RED,
    green: Annotated[Path | None, typer.Option("--green", help="GREEN receipt path.")] = None,
    requirement: REQUIREMENT = None,
    base: BASE = "HEAD",
    as_json: JSON_OUT = False,
) -> None:
    """Evaluate the scoped gate: READY before the fix, ELIGIBLE after it, else FALLBACK."""
    try:
        report = evaluate_gate(_request(feature, red, green, requirement, base))
    except BugfixConfigError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(EXIT_CONFIG) from exc
    _emit(report, as_json)
    raise typer.Exit(0 if not report.reasons else 1)


@bugfix_app.command("record")
def record_command(
    feature: FEATURE,
    red: RED,
    green: Annotated[Path, typer.Option("--green", help="GREEN receipt path.")],
    summary: Annotated[str, typer.Option("--summary", help="One-line bugfix summary.")],
    requirement: REQUIREMENT = None,
    base: BASE = "HEAD",
    as_json: JSON_OUT = False,
) -> None:
    """Re-run the closing gate and append the bugfix trace once when eligible."""
    try:
        result = record_bugfix(
            _request(feature, red, green, requirement, base), summary, date.today()
        )
    except BugfixConfigError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(EXIT_CONFIG) from exc
    if result.report is None:
        message = {"verdict": "ELIGIBLE", "already_recorded": True, "feature": feature}
        typer.echo(json.dumps(message) if as_json else "Bugfix trace: already recorded")
        raise typer.Exit(0)
    _emit(result.report, as_json)
    if not as_json:
        for path in result.written:
            typer.echo(f"Recorded: {path}")
    raise typer.Exit(0 if not result.report.reasons else 1)
