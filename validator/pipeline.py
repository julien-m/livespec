"""Pipeline state management CLI — init, update, read, next."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import typer

from .specs_utils import find_specs_root
from .exceptions import SpecsRootNotFoundError

pipeline_app = typer.Typer(name="pipeline", help="Manage pipeline.md state for a feature.")

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

PHASE_ORDER = ["specify", "spec-review", "plan", "plan-review", "preflight", "implement", "test"]

PHASE_MAP = {
    "specify": "Specify",
    "spec-review": "Spec Review",
    "plan": "Plan",
    "plan-review": "Plan Review",
    "preflight": "Preflight",
    "implement": "Implement",
    "test": "Test",
}

STATUS_MAP = {
    "pending": "Pending",
    "in_progress": "In Progress",
    "done": "Done",
    "skipped": "Skipped",
    "blocked": "Blocked",
}

DONE_STATUSES = {"Done", "Skipped"}

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

_REVERSE_PHASE_MAP = {v: k for k, v in PHASE_MAP.items()}


def _resolve_feature_dir(feature: str) -> Path:
    """Return .specs/features/<feature>/ or exit 1 if not found."""
    try:
        specs_root = find_specs_root()
    except SpecsRootNotFoundError:
        typer.echo("Error: .specs/ directory not found", err=True)
        raise typer.Exit(1)  # noqa: B904

    feature_dir = specs_root / "features" / feature
    if not feature_dir.is_dir():
        typer.echo(f"Error: feature directory not found: {feature_dir}", err=True)
        raise typer.Exit(1)  # noqa: B904

    return feature_dir


def _pipeline_path(feature: str) -> tuple[Path, Path]:
    """Return (feature_dir, pipeline_path). Exits 1 if feature dir missing."""
    feature_dir = _resolve_feature_dir(feature)
    return feature_dir, feature_dir / "pipeline.md"


def _parse_pipeline(content: str) -> dict[str, str]:
    """Parse pipeline.md table rows into {slug: display_status} dict."""
    result: dict[str, str] = {}
    display_to_slug = _REVERSE_PHASE_MAP

    for line in content.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if len(cells) < 2:
            continue
        phase_display = cells[0]
        status_display = cells[1]
        if phase_display in display_to_slug:
            result[display_to_slug[phase_display]] = status_display
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Commands
# ──────────────────────────────────────────────────────────────────────────────


@pipeline_app.command()
def init(
    feature: str = typer.Option(..., "--feature", help="Feature directory name (e.g. 001-my-feature)"),
) -> None:
    """Create pipeline.md for a feature with all phases set to Pending.

    Exit codes:
      0 — pipeline.md created successfully
      1 — feature directory not found or .specs/ missing
    """
    feature_dir = _resolve_feature_dir(feature)
    pipeline_path = feature_dir / "pipeline.md"

    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    rows = "\n".join(f"| {PHASE_MAP[slug]} | Pending | — |" for slug in PHASE_ORDER)
    header = (
        f"# Pipeline — {feature}\n\n"
        f"**Started:** {now}\n"
        f"**Flags:** none\n\n"
        f"| Phase | Status | Completed At |\n"
        f"|-------|--------|--------------|"
    )
    content = f"{header}\n{rows}\n"

    pipeline_path.write_text(content, encoding="utf-8")
    typer.echo(f"Created: {pipeline_path}")


@pipeline_app.command()
def update(
    feature: str = typer.Option(..., "--feature", help="Feature directory name"),
    phase: str = typer.Option(..., "--phase", help="Phase slug (e.g. specify, plan-review)"),
    status: str = typer.Option(..., "--status", help="Status slug (e.g. pending, in_progress, done)"),
    timestamp: bool = typer.Option(False, "--timestamp", help="Write current UTC timestamp in Completed At column"),
) -> None:
    """Update a phase status in pipeline.md.

    Exit codes:
      0 — updated successfully
      1 — phase not found in file, unknown phase/status slug, or file missing
    """
    # Validate phase slug
    if phase not in PHASE_MAP:
        typer.echo(f"Error: unknown phase '{phase}'. Valid: {', '.join(PHASE_ORDER)}", err=True)
        raise typer.Exit(1)

    # Validate status slug
    if status not in STATUS_MAP:
        typer.echo(f"Error: unknown status '{status}'. Valid: {', '.join(STATUS_MAP)}", err=True)
        raise typer.Exit(1)

    _, pipeline_path = _pipeline_path(feature)

    if not pipeline_path.exists():
        typer.echo(f"Error: pipeline.md not found: {pipeline_path}", err=True)
        raise typer.Exit(1)

    display_phase = PHASE_MAP[phase]
    display_status = STATUS_MAP[status]
    ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if timestamp else "—"
    new_row = f"| {display_phase} | {display_status} | {ts} |"

    content = pipeline_path.read_text(encoding="utf-8")

    # Flexible whitespace pattern — handles AI-generated padded tables
    pattern = re.compile(
        r"\|[^|]*\b" + re.escape(display_phase) + r"\b[^|]*\|[^|]*\|[^|]*\|"
    )
    new_content = re.sub(pattern, new_row, content, count=1)

    if new_content == content:
        typer.echo(
            f"Error: phase '{display_phase}' not found in {pipeline_path}",
            err=True,
        )
        raise typer.Exit(1)

    # Atomic write: write to .tmp then rename
    tmp_path = pipeline_path.with_suffix(".md.tmp")
    tmp_path.write_text(new_content, encoding="utf-8")
    tmp_path.rename(pipeline_path)

    typer.echo(f"Updated {display_phase} → {display_status}")


@pipeline_app.command()
def read(
    feature: str = typer.Option(..., "--feature", help="Feature directory name"),
) -> None:
    """Read pipeline.md and output JSON mapping phase slugs to status display values.

    Exit codes:
      0 — success (JSON printed to stdout)
      1 — pipeline.md missing or parse failure
    """
    _, pipeline_path = _pipeline_path(feature)

    if not pipeline_path.exists():
        typer.echo(f"Error: pipeline.md not found: {pipeline_path}", err=True)
        raise typer.Exit(1)

    content = pipeline_path.read_text(encoding="utf-8")
    data = _parse_pipeline(content)

    if not data:
        typer.echo("Error: could not parse pipeline.md — no phase rows found", err=True)
        raise typer.Exit(1)

    typer.echo(json.dumps(data, indent=2))


@pipeline_app.command()
def next(
    feature: str = typer.Option(..., "--feature", help="Feature directory name"),
) -> None:
    """Print the slug of the next non-done phase.

    Exit codes:
      0 — next phase found (slug printed to stdout)
      1 — pipeline.md missing or parse failure
      2 — all phases are Done/Skipped (pipeline complete — treat as success)
    """
    _, pipeline_path = _pipeline_path(feature)

    if not pipeline_path.exists():
        typer.echo(f"Error: pipeline.md not found: {pipeline_path}", err=True)
        raise typer.Exit(1)

    content = pipeline_path.read_text(encoding="utf-8")
    data = _parse_pipeline(content)

    if not data:
        typer.echo("Error: could not parse pipeline.md — no phase rows found", err=True)
        raise typer.Exit(1)

    for slug in PHASE_ORDER:
        status = data.get(slug, "Pending")
        if status not in DONE_STATUSES:
            typer.echo(slug)
            raise typer.Exit(0)

    # All phases are Done/Skipped — pipeline complete
    sys.exit(2)
