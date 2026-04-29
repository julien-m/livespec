"""Typer CLI for the brainstorm subcommand.

Architecture rationale (addresses plan-review Finding #2/#3):

The CLI exposes 4 deterministic subcommands — `detect`, `validate`,
`plan`, and `apply` — driven by the slash commands `/spec.init` and
`/spec.refine`. The split keeps each phase pure and testable; the
`plan` command emits a JSON `IngestionPlan` that `apply` consumes.
This intermediate JSON is the contract: it allows dry-runs (the LLM
can show the user the plan before approving), reproducibility, and
atomicity (the plan is fully built before any write).

Exit codes:
    0 — success
    1 — apply error (refine mode may leave partial state — see message)
    2 — grammar violations
    3 — missing mockup / file integrity violation
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from .apply import apply_plan, build_plan, plan_from_json, plan_to_json
from .detect import detect as detect_artifacts
from .grammar import validate_all

app = typer.Typer(
    name="brainstorm",
    help="Ingest project-brainstorm artifacts into .specs/",
    no_args_is_help=True,
)


def _resolve_cwd(cwd: str | None) -> Path:
    return Path(cwd).resolve() if cwd else Path.cwd()


# @spec FR-001: detect subcommand — .specs/features/012-brainstorm-ingestion/spec.md#fr-001
@app.command()
def detect(
    cwd: str | None = typer.Option(None, "--cwd", help="Directory to scan"),
) -> None:
    """Scan CWD for brainstorm artifacts; emit JSON snapshot."""
    typer.echo(detect_artifacts(_resolve_cwd(cwd)).to_json())
    raise typer.Exit(0)


# @spec FR-002: validate subcommand — .specs/features/012-brainstorm-ingestion/spec.md#fr-002
@app.command()
def validate(
    cwd: str | None = typer.Option(None, "--cwd", help="Directory to scan"),
    output_format: str = typer.Option(
        "compact", "--format", "-f", help="compact | json"
    ),
) -> None:
    """Validate flow grammar and mockup references; emit violations."""
    report = validate_all(_resolve_cwd(cwd))
    if output_format == "json":
        typer.echo(
            json.dumps(
                {
                    "ok": report.ok,
                    "violations": [v.model_dump() for v in report.all_violations],
                }
            )
        )
    else:
        if report.ok:
            typer.echo(f"OK — {len(report.flows)} flow(s) validated.")
        else:
            for v in report.all_violations:
                typer.echo(f"  [{v.rule_id}] {v.file}: {v.message}", err=True)
            typer.echo(
                f"\n{len(report.all_violations)} violation(s) across "
                f"{len(report.flows)} flow(s).",
                err=True,
            )
    if report.ok:
        raise typer.Exit(0)
    has_mockup_miss = any(
        v.rule_id == "MOCKUP_MISSING" for v in report.all_violations
    )
    raise typer.Exit(3 if has_mockup_miss else 2)


# @spec FR-009: plan subcommand — .specs/features/012-brainstorm-ingestion/spec.md#fr-009
@app.command()
def plan(
    cwd: str | None = typer.Option(None, "--cwd", help="Directory to scan"),
    mode: str = typer.Option("init", "--mode", help="init | refine"),
    out: str = typer.Option(
        ".livespec-plan.json", "--out", help="Plan JSON output path"
    ),
) -> None:
    """Build a deterministic IngestionPlan and write it as JSON."""
    if mode not in {"init", "refine"}:
        typer.echo(f"Error: --mode must be 'init' or 'refine', got {mode!r}", err=True)
        raise typer.Exit(1)
    cwd_path = _resolve_cwd(cwd)
    report = validate_all(cwd_path)
    if not report.ok:
        typer.echo("Refusing to plan: validation failed. Run validate first.", err=True)
        raise typer.Exit(2)
    p = build_plan(cwd_path, mode, report)  # type: ignore[arg-type]
    Path(out).write_text(plan_to_json(p), encoding="utf-8")
    typer.echo(
        f"Plan written to {out} — "
        f"{len(p.flow_ops)} feature(s), {len(p.mockup_ops)} mockup(s), "
        f"{len(p.screen_ops)} screen(s), {len(p.skipped_slugs)} skipped.",
    )
    raise typer.Exit(0)


# @spec FR-007: apply subcommand — .specs/features/012-brainstorm-ingestion/spec.md#fr-007
@app.command()
def apply(
    plan_path: str = typer.Argument(..., help="Path to plan JSON"),
) -> None:
    """Apply an IngestionPlan; atomic in init mode, per-file in refine mode."""
    p = plan_from_json(Path(plan_path).read_text(encoding="utf-8"))
    try:
        report = apply_plan(p)
    except Exception as exc:
        typer.echo(f"Error during apply: {exc}", err=True)
        raise typer.Exit(1)  # noqa: B904
    typer.echo(
        json.dumps(
            {
                "mode": report.mode,
                "written": report.written,
                "copied": report.copied,
                "skipped": report.skipped,
            },
            indent=2,
        )
    )
    raise typer.Exit(0)
