"""CLI surface for the visual feature gate (``livespec visual-gate``).

# @spec FR-100: Visual gate CLI surface — feature TBD (visual-gate-fix cycle)
# @spec FR-101: cleanup with dry-run and quarantine — feature TBD (visual-gate-fix cycle)
# @spec FR-102: promote into the canonical registry — feature TBD (visual-gate-fix cycle)

Subcommands:
* ``validate``: aggregate Penflow, design-alignment, registry-link, and
  runtime-misplacement checks for one feature/target. Exit ``0|6|7``.
* ``cleanup``: detect and (with ``--apply``) quarantine misplaced runtime
  captures under ``.specs/design/screens/``. Exit ``0|8``.
* ``promote``: copy a ``run/<ts>/<target>/<screen>.png`` into the registry
  and create the canonical symlink in the feature-local baselines dir.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Annotated, Literal

import typer

from validator.cli_exit_codes import (
    EXIT_OK,
    EXIT_VISUAL_GATE_BLOCKED,
    EXIT_VISUAL_GATE_CLEANUP_DRIFT,
    EXIT_VISUAL_GATE_FAIL,
)
from validator.visual_evidence import VisualReceiptError
from validator.visual_gate import (
    GateCommand,
    GateTarget,
    apply_cleanup,
    certify_visual_evidence,
    plan_cleanup,
    promote_baseline,
    render_text_report,
    validate_gate,
    verdict_to_exit_code,
    write_cleanup_report,
)

visual_gate_app = typer.Typer(
    name="visual-gate",
    help=(
        "Aggregate Penflow + design-alignment + registry-link checks for a "
        "feature. Used by /spec-check, /spec-fix, /spec-test, /spec-feature."
    ),
    no_args_is_help=True,
)


def register(app: typer.Typer) -> None:
    """Register the ``visual-gate`` command group on ``app``."""
    app.add_typer(visual_gate_app, name="visual-gate")


def _timestamp() -> str:
    return _dt.datetime.now(tz=_dt.UTC).strftime("%Y%m%dT%H%M%SZ")


def _receipt_exit_code(verdict: str) -> int:
    if verdict == "PASS":
        return EXIT_OK
    if verdict == "FAIL":
        return EXIT_VISUAL_GATE_FAIL
    return EXIT_VISUAL_GATE_BLOCKED


@visual_gate_app.command("validate")
def validate_command(
    feature: Annotated[
        str | None,
        typer.Option("--feature", help="Feature slug under .specs/features/."),
    ] = None,
    command: Annotated[
        str,
        typer.Option(
            "--command",
            help="Caller skill: spec-check | spec-fix | spec-test | spec-feature.",
        ),
    ] = "spec-check",
    target: Annotated[
        str | None,
        typer.Option(
            "--target",
            help="UI target: web | ios | android | tauri. Omit for target-agnostic checks.",
        ),
    ] = None,
    project: Annotated[
        Path,
        typer.Option("--project", help="Project root containing .specs/."),
    ] = Path("."),
    strict_links: Annotated[
        bool,
        typer.Option(
            "--strict-links/--no-strict-links",
            help="Enforce symlink-default + manifest invariants (default on).",
        ),
    ] = True,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON."),
    ] = False,
    receipt: Annotated[
        Path | None,
        typer.Option(
            "--receipt",
            help="Validate a visual evidence receipt instead of aggregating the gate.",
        ),
    ] = None,
) -> None:
    """Run the gate and exit 0 (PASS), 6 (FAIL), or 7 (BLOCKED)."""
    if feature is None:
        typer.echo("Error: --feature is required.", err=True)
        raise typer.Exit(EXIT_VISUAL_GATE_BLOCKED)
    if command not in ("spec-check", "spec-fix", "spec-test", "spec-feature"):
        typer.echo(
            "Error: --command must be one of spec-check, spec-fix, spec-test, spec-feature.",
            err=True,
        )
        raise typer.Exit(EXIT_VISUAL_GATE_BLOCKED)
    if target is not None and target not in ("web", "ios", "android", "tauri"):
        typer.echo(
            "Error: --target must be one of web, ios, android, tauri.",
            err=True,
        )
        raise typer.Exit(EXIT_VISUAL_GATE_BLOCKED)
    validated_command: GateCommand = command
    validated_target: GateTarget | None = target
    report = validate_gate(
        project_root=project.resolve(),
        feature_slug=feature,
        command=validated_command,
        target=validated_target,
        strict_links=strict_links,
        receipt_path=receipt,
    )
    if json_output:
        payload = report.to_dict()
        payload["exit_code"] = verdict_to_exit_code(report.verdict)
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
    else:
        typer.echo(render_text_report(report))
    raise typer.Exit(verdict_to_exit_code(report.verdict))


@visual_gate_app.command("certify")
def certify_command(
    feature: Annotated[
        str,
        typer.Option("--feature", help="Feature slug under .specs/features/."),
    ],
    command: Annotated[
        str,
        typer.Option(
            "--command",
            help="Caller skill: spec-check | spec-fix | spec-test | spec-feature.",
        ),
    ],
    target: Annotated[
        str,
        typer.Option("--target", help="UI target: web | ios | android | tauri."),
    ],
    run_id: Annotated[
        str,
        typer.Option("--run-id", help="Runtime capture run id under the feature run dir."),
    ],
    project: Annotated[
        Path,
        typer.Option("--project", help="Project root containing .specs/."),
    ] = Path("."),
    threshold_percent: Annotated[
        float,
        typer.Option(
            "--threshold-percent",
            help="Allowed mockup/runtime changed-pixel percentage.",
        ),
    ] = 5.0,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON."),
    ] = False,
) -> None:
    """Create a deterministic visual evidence receipt from real PNG files."""
    if command not in ("spec-check", "spec-fix", "spec-test", "spec-feature"):
        typer.echo(
            "Error: --command must be one of spec-check, spec-fix, spec-test, spec-feature.",
            err=True,
        )
        raise typer.Exit(EXIT_VISUAL_GATE_BLOCKED)
    if target not in ("web", "ios", "android", "tauri"):
        typer.echo(
            "Error: --target must be one of web, ios, android, tauri.",
            err=True,
        )
        raise typer.Exit(EXIT_VISUAL_GATE_BLOCKED)
    try:
        payload = certify_visual_evidence(
            project_root=project.resolve(),
            feature_slug=feature,
            command=command,
            target=target,
            run_id=run_id,
            threshold_percent=threshold_percent,
        )
    except (OSError, VisualReceiptError) as exc:
        payload: dict[str, object] = {
            "feature_slug": feature,
            "command": command,
            "target": target,
            "run_id": run_id,
            "verdict": "BLOCKED",
            "receipt_path": None,
            "missing_artifacts": [str(exc)],
        }
    verdict = str(payload["verdict"])
    exit_code = _receipt_exit_code(verdict)
    payload["exit_code"] = exit_code
    if json_output:
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
    else:
        typer.echo(f"Visual Evidence Certification Verdict: {verdict}")
        if payload.get("receipt_path"):
            typer.echo(f"receipt: {payload['receipt_path']}")
    raise typer.Exit(exit_code)


@visual_gate_app.command("cleanup")
def cleanup_command(
    feature: Annotated[
        str,
        typer.Option("--feature", help="Feature slug under .specs/features/."),
    ],
    project: Annotated[
        Path,
        typer.Option("--project", help="Project root containing .specs/."),
    ] = Path("."),
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run/--apply",
            help="Default: dry-run. Use --apply to perform the quarantine moves.",
        ),
    ] = True,
    delete: Annotated[
        bool,
        typer.Option(
            "--delete",
            help=(
                "Delete misplaced files instead of archiving. Forbidden "
                "unless combined with --force-delete."
            ),
        ),
    ] = False,
    force_delete: Annotated[
        bool,
        typer.Option(
            "--force-delete",
            help="Acknowledge that --delete will discard files irretrievably.",
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON."),
    ] = False,
) -> None:
    """Detect and quarantine runtime captures misplaced under design/screens.

    Defaults are safe: ``--dry-run --archive``. ``--apply`` performs the
    moves; ``--delete`` is rejected unless ``--force-delete`` is also set.
    """
    if delete and not force_delete:
        typer.echo(
            "Error: --delete requires --force-delete to acknowledge "
            "irreversible removal.",
            err=True,
        )
        raise typer.Exit(EXIT_VISUAL_GATE_BLOCKED)
    mode: Literal["archive", "delete"] = "delete" if delete else "archive"
    timestamp = _timestamp()
    plan = plan_cleanup(
        project_root=project.resolve(),
        feature_slug=feature,
        timestamp=timestamp,
        mode=mode,
    )
    applied = [] if dry_run else apply_cleanup(plan)
    report_path = write_cleanup_report(
        project_root=project.resolve(),
        plan=plan,
        applied=applied,
        timestamp=timestamp,
    )
    if json_output:
        payload = {
            "plan": plan.to_dict(),
            "applied": [a.to_dict() for a in applied],
            "report_path": str(report_path),
            "dry_run": dry_run,
        }
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
    else:
        typer.echo(f"feature={feature} mode={mode} dry_run={dry_run}")
        typer.echo(f"planned actions: {len(plan.actions)}")
        typer.echo(f"applied actions: {len(applied)}")
        typer.echo(f"report: {report_path}")
        if plan.actions:
            for action in plan.actions:
                typer.echo(
                    f"  - {action.reason}: {action.source} -> "
                    f"{action.quarantine_target or '<delete>'}"
                )
    if dry_run and plan.has_drift:
        raise typer.Exit(EXIT_VISUAL_GATE_CLEANUP_DRIFT)
    raise typer.Exit(EXIT_OK)


@visual_gate_app.command("promote")
def promote_command(
    feature: Annotated[
        str,
        typer.Option("--feature", help="Feature slug under .specs/features/."),
    ],
    target: Annotated[
        str,
        typer.Option("--target", help="UI target: web | ios | android | tauri."),
    ],
    screen: Annotated[
        str,
        typer.Option("--screen", help="Screen id (with or without .png suffix)."),
    ],
    run_id: Annotated[
        str,
        typer.Option(
            "--run-id",
            help=(
                "Timestamp folder name under .specs/features/<slug>/run/ "
                "produced by the runner."
            ),
        ),
    ],
    project: Annotated[
        Path,
        typer.Option("--project", help="Project root containing .specs/."),
    ] = Path("."),
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON."),
    ] = False,
) -> None:
    """Promote a runtime capture into the registry + create the symlink."""
    if target not in ("web", "ios", "android", "tauri"):
        typer.echo(
            "Error: --target must be one of web, ios, android, tauri.",
            err=True,
        )
        raise typer.Exit(EXIT_VISUAL_GATE_BLOCKED)
    try:
        registry, local = promote_baseline(
            project_root=project.resolve(),
            feature_slug=feature,
            target=target,
            screen=screen,
            run_id=run_id,
        )
    except FileNotFoundError as exc:
        typer.echo(f"BLOCKED: {exc}", err=True)
        raise typer.Exit(EXIT_VISUAL_GATE_BLOCKED) from exc
    if json_output:
        payload = {
            "feature": feature,
            "target": target,
            "screen": screen,
            "run_id": run_id,
            "registry_path": str(registry),
            "feature_local_path": str(local) if local else None,
        }
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
    else:
        typer.echo(f"Promoted {screen} ({target}) into registry: {registry}")
        if local:
            typer.echo(f"Symlink created: {local}")
        else:
            typer.echo("Symlink unsupported on this filesystem; manifest mode active.")
    raise typer.Exit(EXIT_OK)


__all__ = ["register", "visual_gate_app"]
