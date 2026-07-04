# LiveSpec traceability anchors
# @spec(FR-004)
# @spec(FR-005)
# @spec(FR-006)
# @spec(FR-007)
# @spec(FR-008)
# @spec(FR-009)
# @spec(FR-010)

"""Typer wrapper for Agent Device proof commands."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import typer

from validator.cli_commands._common import require_specs_root
from validator.device_proof import DeviceProofFailure, DeviceProofReport, run_device_proof

device_app = typer.Typer(help="Capture Agent Device proof from a LiveSpec-selected target.")
BundleArg = Annotated[str, typer.Argument(help="Target application bundle identifier.")]
PlatformOpt = Annotated[str, typer.Option("--platform", help="Device platform.")]
UdidOpt = Annotated[str | None, typer.Option("--udid", help="Target simulator/device UDID.")]
JourneyOpt = Annotated[
    str | None,
    typer.Option("--journey", help="Read UDID from the journey last-run receipt."),
]
SessionOpt = Annotated[str, typer.Option("--session", help="Agent Device session name.")]
OutDirOpt = Annotated[Path | None, typer.Option("--out-dir", help="Proof output directory.")]
JsonOpt = Annotated[bool, typer.Option("--json", help="Emit JSON output.")]


def register(app: typer.Typer) -> None:
    """Register the ``device`` command group."""
    app.add_typer(device_app, name="device")


@device_app.command(name="proof")
def proof_command(
    bundle: BundleArg,
    platform: PlatformOpt = "ios",
    udid: UdidOpt = None,
    journey: JourneyOpt = None,
    session: SessionOpt = "livespec-proof",
    out_dir: OutDirOpt = None,
    json_output: JsonOpt = False,
) -> None:
    """Run a deterministic Agent Device proof flow for a selected LiveSpec destination."""
    try:
        report = run_device_proof(
            require_specs_root(),
            bundle=bundle,
            platform=platform,
            udid=udid,
            journey=journey,
            session=session,
            out_dir=out_dir,
        )
    except DeviceProofFailure as exc:
        _emit_report(exc.report, json_output)
        raise typer.Exit(exc.exit_code) from exc
    _emit_report(report, json_output)
    raise typer.Exit(0)


def _emit_report(report: DeviceProofReport, json_output: bool) -> None:
    """Emit proof status in JSON or compact human-readable form."""
    if json_output:
        typer.echo(json.dumps(asdict(report)))
        return
    for check in report.checks:
        line = f"{check.name}: {check.status}"
        if check.code:
            line += f" {check.code}"
        if check.detail:
            line += f" - {check.detail}"
        typer.echo(line)
