# @spec(FR-007)

# LiveSpec traceability anchors
# @spec(AC-007)
# @spec(AC-011)

"""``livespec verify-output`` — verify a run artifact against expectations.

# @spec FR-005: verify-output CLI + alias + blocked handling
#   — .specs/features/039.1-goal-archive-run-artifacts/spec.md#fr-005
# @spec FR-009: 3 canonical preview error paths, exit 2
#   — .specs/features/039.1-goal-archive-run-artifacts/spec.md#fr-009
"""

from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Any, cast

import typer

from ..command_registry import canonical_command_name, short_command_name
from ..exceptions import (
    ArtifactMalformed,
    ExpectationsInvalid,
    ExpectationsMissing,
    OverrideMalformed,
    SpecsRootNotFoundError,
)
from ..expectations import load_expectations
from ..outcome import exit_code_for
from ..preview import render_preview, save_preview
from ..run_artifacts import (
    find_latest_artifact,
    goal_tasks_incomplete,
    load_run_artifact,
    recheck_receipts,
)
from ..specs_utils import find_specs_root
from ..verify_output import evaluate_rules, render_report, to_json_envelope

COMMAND_ARGUMENT = typer.Argument(..., help="Command name or alias (e.g. specify).")
RUN_OPTION = typer.Option(None, "--run", help="Explicit run artifact path.")
SCENARIO_OPTION = typer.Option(
    None,
    "--scenario",
    help="Space-separated flags replacing the artifact flags for when-branches.",
)
FEATURE_OPTION = typer.Option(
    None,
    "--feature",
    help="Feature slug override (placeholder value + receipt scoping).",
)
JSON_OPTION = typer.Option(False, "--json", help="Emit the JSON envelope.")
PREVIEW_OPTION = typer.Option(False, "--preview", help="Render a project-aware preview.")
SAVE_OPTION = typer.Option(False, "--save", help="With --preview: save under .specs/.previews/.")


def register(app: typer.Typer) -> None:
    """Register the ``verify-output`` subcommand on the ``livespec`` app."""
    app.command("verify-output")(verify_output_command)


def verify_output_command(
    command: str = COMMAND_ARGUMENT,
    run: Path | None = RUN_OPTION,
    scenario: str | None = SCENARIO_OPTION,
    feature: str | None = FEATURE_OPTION,
    json_out: bool = JSON_OPTION,
    preview: bool = PREVIEW_OPTION,
    save: bool = SAVE_OPTION,
) -> None:
    """Verify a command's latest run artifact against its expectations."""
    canonical = canonical_command_name(command)
    if preview:
        _run_preview(canonical, save=save, json_out=json_out)
        return
    project_root = _project_root(json_out=json_out)
    artifact_path = _resolve_artifact_path(canonical, run, project_root, json_out=json_out)
    try:
        artifact = load_run_artifact(artifact_path)
    except ArtifactMalformed as exc:
        raise _blocked(str(exc), json_out=json_out) from exc
    # --scenario replaces the artifact flags as the when-branch source (AC-007).
    active_flags = shlex.split(scenario) if scenario else _string_list(artifact.get("flags"))
    placeholder_feature = feature or _optional_str(artifact.get("feature"))
    receipts_raw = artifact.get("receipts")
    receipt_entries = (
        [cast(dict[str, Any], entry) for entry in cast(list[object], receipts_raw)]
        if isinstance(receipts_raw, list)
        else []
    )
    # Receipt feature scoping applies only when --feature was given (AC-007).
    receipt_checks = recheck_receipts(receipt_entries, project_root=project_root, feature=feature)
    goal_raw = artifact.get("goal")
    goal = cast(dict[str, Any], goal_raw) if isinstance(goal_raw, dict) else {"tasks": []}
    tasks = [
        cast(dict[str, Any], task)
        for task in cast(list[object], goal.get("tasks") or [])
        if isinstance(task, dict)
    ]
    report = evaluate_rules(
        _verify_rules(artifact),
        artifact=artifact,
        active_flags=active_flags,
        feature=placeholder_feature,
        project_root=project_root,
        # @spec FR-004: re-derivation shares the archive.run exclusion rule
        #   — .specs/features/059-pipeline-verify-phase/spec.md#fr-004
        goal_incomplete=goal_tasks_incomplete(tasks),
        receipt_error=any(not check.verified for check in receipt_checks),
    )
    if json_out:
        envelope = to_json_envelope(report, command=canonical, artifact_path=artifact_path)
        typer.echo(json.dumps(envelope, indent=2))
    else:
        typer.echo(render_report(report, command=canonical, artifact_path=artifact_path))
    final_exit = exit_code_for(report.outcome)
    if final_exit != 0:
        raise typer.Exit(final_exit)


def _run_preview(canonical: str, *, save: bool, json_out: bool) -> None:
    """Render the project-aware preview (FR-008) with canonical errors (FR-009)."""
    try:
        specs_root = find_specs_root()
    except SpecsRootNotFoundError as exc:
        # @spec AC-011: canonical preview error strings, exit 2
        #   — .specs/features/039.1-goal-archive-run-artifacts/spec.md#ac-011
        raise _blocked(
            "preview requires a LiveSpec project (no .specs/ found)",
            json_out=json_out,
        ) from exc
    project_root = specs_root.parent
    try:
        expectations = load_expectations(canonical, project_root, _livespec_root())
    except (ExpectationsInvalid, OverrideMalformed, ExpectationsMissing) as exc:
        # Section 13 errors surface verbatim — their reasons carry the exact
        # canonical substrings from 040 AC-008/AC-009.
        raise _blocked(f"preview blocked: {exc}", json_out=json_out) from exc
    markdown = render_preview(expectations, project_root)
    saved: Path | None = None
    if save:
        saved = save_preview(markdown, canonical, project_root)
    if json_out:
        envelope = {
            "command": canonical,
            "project_root": project_root.as_posix(),
            "saved": saved.as_posix() if saved else None,
            "markdown": markdown,
        }
        typer.echo(json.dumps(envelope, indent=2))
    else:
        typer.echo(markdown)
        if saved is not None:
            typer.echo(f"saved: {saved.as_posix()}")


def _resolve_artifact_path(
    canonical: str,
    run: Path | None,
    project_root: Path,
    *,
    json_out: bool,
) -> Path:
    """Resolve --run or the lexicographically latest artifact; blocked otherwise."""
    if run is not None:
        if run.is_file():
            return run
        raise _blocked(f"run artifact not found: {run.as_posix()}", json_out=json_out)
    runs_dir = project_root / ".specs" / ".runs"
    latest = find_latest_artifact(canonical, runs_dir)
    if latest is None:
        # Tolerate short-name artifacts emitted by older wrappers.
        latest = find_latest_artifact(short_command_name(canonical), runs_dir)
    if latest is None:
        raise _blocked(
            f"no run artifact for {canonical} under {runs_dir.as_posix()}",
            json_out=json_out,
        )
    return latest


def _verify_rules(artifact: dict[str, Any]) -> dict[str, Any]:
    rules = artifact.get("verify_rules")
    if isinstance(rules, dict):
        return cast(dict[str, Any], rules)
    return {"must": [], "may": [], "must_not": [], "when": []}


def _project_root(*, json_out: bool) -> Path:
    try:
        return find_specs_root().parent
    except SpecsRootNotFoundError as exc:
        raise _blocked(str(exc), json_out=json_out) from exc


def _blocked(reason: str, *, json_out: bool) -> typer.Exit:
    """Emit a blocked envelope for JSON callers and return exit 2."""
    if json_out:
        typer.echo(json.dumps({"outcome": "blocked", "reason": reason}))
    typer.echo(f"verify-output blocked: {reason}", err=True)
    return typer.Exit(2)


def _livespec_root() -> Path:
    """Resolve the LiveSpec checkout root by walking parents of this module."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".agent-sync" / "skills").is_dir() and (parent / "validator").is_dir():
            return parent
    return here.parents[2]


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in cast(list[object], value)]


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


__all__ = ["register", "verify_output_command"]
