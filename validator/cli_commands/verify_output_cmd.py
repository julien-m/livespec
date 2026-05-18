"""``livespec verify-output`` — compare a run artifact against expectations.

# @spec FR-007: verify-output CLI
#   — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-007
# @spec AC-005, AC-006, AC-007: exit code semantics
#   — .specs/features/039-command-expectations-and-verify-output/spec.md
# @spec FR-005: --preview and --save flags
#   — .specs/features/040-expectations-rich-and-verify-preview/spec.md#fr-005
# @spec FR-008: --save writes .specs/.previews/
#   — .specs/features/040-expectations-rich-and-verify-preview/spec.md#fr-008
# @spec FR-009: canonical error strings
#   — .specs/features/040-expectations-rich-and-verify-preview/spec.md#fr-009
"""

import json
import secrets
from pathlib import Path

import typer

from ..command_registry import normalize_command_name
from ..exceptions import (
    ArtifactMalformed,
    ExpectationsInvalid,
    ExpectationsMissing,
    OverrideMalformed,
)
from ..expectations import load_expectations
from ..preview import ERR_NO_SPECS_DIR, render_preview
from ..run_artifact import find_latest_artifact, read_artifact
from ..specs_utils import find_specs_root
from ..verify_output import (
    VerifyReport,
    blocked_report,
    evaluate,
    render_human,
    render_json,
)

COMMAND_ARGUMENT = typer.Argument(
    ...,
    help="Command name or alias (e.g. 'spec-specify', 'specify', or '/spec.specify').",
)
SCENARIO_OPTION = typer.Option(
    "",
    "--scenario",
    help="Extra flags to activate when: branches (space-separated).",
)
RUN_OPTION = typer.Option(
    None,
    "--run",
    help="Explicit artifact path (overrides latest lookup).",
)
FEATURE_OPTION = typer.Option(
    None,
    "--feature",
    help="Active feature dir name (resolves <feature> placeholder).",
)
JSON_OPTION = typer.Option(
    False,
    "--json",
    help="Emit JSON to stdout instead of a human table.",
)
PREVIEW_OPTION = typer.Option(
    False,
    "--preview",
    help="Project-aware preview (no artifact required); render Section 13 with placeholders.",
)
SAVE_OPTION = typer.Option(
    False,
    "--save",
    help="With --preview, also write the rendered Markdown to .specs/.previews/.",
)


def register(app: typer.Typer) -> None:
    """Register the ``verify-output`` command on ``app``."""
    app.command(
        name="verify-output",
        help="Verify the latest run artifact for a command against its expectations.",
    )(verify_output_command)


def verify_output_command(
    command: str = COMMAND_ARGUMENT,
    scenario: str = SCENARIO_OPTION,
    run: Path | None = RUN_OPTION,
    feature: str | None = FEATURE_OPTION,
    json_out: bool = JSON_OPTION,
    preview: bool = PREVIEW_OPTION,
    save: bool = SAVE_OPTION,
) -> None:
    """Verify the latest run artifact against the command's expectations."""
    command = normalize_command_name(command)
    if preview:
        _run_preview(command, json_out=json_out, save=save)
        return
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


def _run_preview(command: str, *, json_out: bool, save: bool) -> None:
    """Handle the ``--preview`` branch of ``verify-output``.

    # @spec FR-005: --preview wiring
    #   — .specs/features/040-expectations-rich-and-verify-preview/spec.md#fr-005
    # @spec FR-008: --save writes file
    #   — .specs/features/040-expectations-rich-and-verify-preview/spec.md#fr-008
    # @spec FR-009: canonical error strings
    #   — .specs/features/040-expectations-rich-and-verify-preview/spec.md#fr-009
    """
    cwd = Path.cwd()
    specs_dir = cwd / ".specs"
    if not specs_dir.is_dir():
        typer.echo(ERR_NO_SPECS_DIR, err=True)
        raise typer.Exit(2)

    project_root = cwd
    livespec_root = _detect_livespec_root()

    # Load expectations and surface the canonical AC-008/009 error strings.
    try:
        expectations = load_expectations(command, project_root, livespec_root)
    except ExpectationsMissing as exc:
        typer.echo(
            f"no expectations file for {command!r} (searched: {exc.searched_paths})",
            err=True,
        )
        raise typer.Exit(2) from exc
    except OverrideMalformed as exc:
        typer.echo(f"override malformed: {exc.reason}", err=True)
        raise typer.Exit(2) from exc
    except ExpectationsInvalid as exc:
        # AC-008 / AC-009 messages are already shaped inside the parser.
        typer.echo(exc.reason, err=True)
        raise typer.Exit(2) from exc

    if expectations.demo_session is None:
        typer.echo(
            f"section 13 missing in {expectations.source_path.as_posix()}",
            err=True,
        )
        raise typer.Exit(2)

    report = render_preview(expectations, project_root)

    if save:
        previews_dir = project_root / ".specs" / ".previews"
        previews_dir.mkdir(parents=True, exist_ok=True)
        base_name = f"{command}-{report.timestamp}"
        target = previews_dir / f"{base_name}.md"
        if target.exists():
            # Avoid collision on sub-second double-invocation (EC-006).
            suffix = secrets.token_hex(2)[:3]
            target = previews_dir / f"{base_name}-{suffix}.md"
        target.write_text(report.markdown, encoding="utf-8")

    if json_out:
        envelope = {
            "command": report.command,
            "project_root": str(report.project_root),
            "timestamp": report.timestamp,
            "markdown": report.markdown,
        }
        typer.echo(json.dumps(envelope, indent=2))
    else:
        typer.echo(report.markdown)
    raise typer.Exit(0)


def _detect_livespec_root() -> Path:
    """Resolve the LiveSpec checkout root by walking parents of this module."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".agent-sync" / "skills").is_dir() and (
            parent / "validator"
        ).is_dir():
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


# Export the command registration hooks used by the top-level CLI.
__all__ = ["register", "verify_output_command"]
