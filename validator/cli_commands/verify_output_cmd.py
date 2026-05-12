"""``livespec verify-output`` — compare a run artifact against expectations.

# @spec FR-007: verify-output CLI — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-007
# @spec AC-005, AC-006, AC-007: exit code semantics — .specs/features/039-command-expectations-and-verify-output/spec.md
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from ..exceptions import (
    ArtifactMalformed,
    ExpectationsInvalid,
    ExpectationsMissing,
    OverrideMalformed,
)
from ..expectations import load_expectations
from ..run_artifact import find_latest_artifact, read_artifact
from ..specs_utils import find_specs_root
from ..verify_output import (
    VerifyReport,
    blocked_report,
    evaluate,
    render_human,
    render_json,
)


def register(app: typer.Typer) -> None:
    """Register the ``verify-output`` command on ``app``."""
    app.command(
        name="verify-output",
        help="Verify the latest run artifact for a command against its expectations.",
    )(verify_output_command)


def verify_output_command(
    command: str = typer.Argument(..., help="Command name (e.g. 'specify')."),
    scenario: str = typer.Option(
        "",
        "--scenario",
        help="Extra flags to activate when: branches (space-separated).",
    ),
    run: Path | None = typer.Option(
        None,
        "--run",
        help="Explicit artifact path (overrides latest lookup).",
    ),
    feature: str | None = typer.Option(
        None,
        "--feature",
        help="Active feature dir name (resolves <feature> placeholder).",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit JSON to stdout instead of a human table.",
    ),
) -> None:
    """Verify the latest run artifact against the command's expectations."""
    try:
        project_root = find_specs_root().parent
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(2) from exc
    livespec_root = _detect_livespec_root()

    # 1. Resolve expectations file.
    try:
        expectations = load_expectations(command, project_root, livespec_root)
    except OverrideMalformed as exc:
        _emit_blocked(
            command, None, None, f"override malformed: {exc.reason}", json_out
        )
        raise typer.Exit(2) from exc
    except ExpectationsMissing as exc:
        _emit_blocked(
            command,
            None,
            None,
            f"no expectations file for {command!r} (searched: {exc.searched_paths})",
            json_out,
        )
        raise typer.Exit(2) from exc
    except ExpectationsInvalid as exc:
        _emit_blocked(
            command, None, None, f"expectations invalid: {exc.reason}", json_out
        )
        raise typer.Exit(2) from exc

    # 2. Resolve artifact path.
    runs_dir = project_root / ".specs" / ".runs"
    artifact_path = run or find_latest_artifact(command, runs_dir)
    if artifact_path is None or not artifact_path.exists():
        _emit_blocked(
            command,
            expectations.source_path,
            None,
            f"no run artifact found for {command!r} under {runs_dir}",
            json_out,
        )
        raise typer.Exit(2)

    # 3. Load artifact (malformed -> blocked, EC-007).
    try:
        artifact = read_artifact(artifact_path)
    except ArtifactMalformed as exc:
        _emit_blocked(
            command,
            expectations.source_path,
            artifact_path,
            f"malformed artifact at {exc.path}: {exc.reason}",
            json_out,
        )
        raise typer.Exit(2) from exc

    # 4. Evaluate.
    scenario_flags = scenario.split() if scenario else []
    report = evaluate(
        expectations,
        artifact,
        scenario_flags=scenario_flags,
        feature=feature,
        artifact_path=artifact_path,
    )
    _emit_report(report, json_out)
    raise typer.Exit(report.exit_code)


def _detect_livespec_root() -> Path:
    """Resolve the LiveSpec checkout root by walking parents of this module."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "commands").is_dir() and (parent / "validator").is_dir():
            return parent
    return here.parents[2]


def _emit_blocked(
    command: str,
    source_path: Path | None,
    artifact_path: Path | None,
    reason: str,
    json_out: bool,
) -> None:
    report = blocked_report(
        command=command,
        source_path=source_path,
        artifact_path=artifact_path,
        reason=reason,
    )
    _emit_report(report, json_out)


def _emit_report(report: VerifyReport, json_out: bool) -> None:
    if json_out:
        typer.echo(json.dumps(render_json(report), indent=2))
    else:
        typer.echo(render_human(report))


__all__ = ["register", "verify_output_command"]
