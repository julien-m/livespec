"""Pipeline state management CLI — init, update, read, next."""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import typer

from .exceptions import SpecsRootNotFoundError
from .specs_utils import find_specs_root

pipeline_app = typer.Typer(name="pipeline", help="Manage pipeline.md state for a feature.")

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

# @spec(FR-001): clarify phase between spec-review and plan, no new command (069-clarify-gate)
# @spec(FR-001): analyze phase after plan-review, before preflight (070-analyze-gate)
PHASE_ORDER = [
    "specify",
    "spec-review",
    "clarify",
    "plan",
    "plan-review",
    "analyze",
    "preflight",
    "implement",
    "test",
]

PHASE_MAP = {
    "specify": "Specify",
    "spec-review": "Spec Review",
    "clarify": "Clarify",
    "plan": "Plan",
    "plan-review": "Plan Review",
    "analyze": "Analyze",
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
        raise typer.Exit(1)

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


def _insert_phase_row(content: str, slug: str, new_row: str) -> str | None:
    """Insert ``new_row`` for ``slug`` at its canonical PHASE_ORDER position.

    Backward-compat: a pipeline.md generated before ``slug`` was added to
    PHASE_ORDER has no row for it. Rather than failing, self-heal the file by
    inserting the row before the first present phase that comes later in
    PHASE_ORDER (or after the last phase row when none follow). General by
    construction — works for any newly added phase slug. Returns ``None`` when
    the file has no recognizable phase table.
    """
    order_index = PHASE_ORDER.index(slug)
    later_displays = {PHASE_MAP[s] for s in PHASE_ORDER[order_index + 1 :]}

    lines = content.splitlines()
    phase_rows: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if cells and cells[0] in _REVERSE_PHASE_MAP:
            phase_rows.append((i, cells[0]))

    if not phase_rows:
        return None

    insert_at: int | None = None
    for i, display in phase_rows:
        if display in later_displays:
            insert_at = i
            break
    if insert_at is None:
        insert_at = phase_rows[-1][0] + 1

    lines.insert(insert_at, new_row)
    result = "\n".join(lines)
    if content.endswith("\n"):
        result += "\n"
    return result


def _single_line(value: str) -> str:
    """Collapse user-provided command text so pipeline headers stay parseable."""
    return " ".join(value.split())


def _format_flags(flags: str | None) -> str:
    """Return the normalized pipeline Flags value."""
    if flags is None:
        return "none"
    normalized = _single_line(flags)
    return f"`{normalized}`" if normalized else "none"


# ──────────────────────────────────────────────────────────────────────────────
# Commands
# ──────────────────────────────────────────────────────────────────────────────


@pipeline_app.command()
def init(
    feature: str = typer.Option(
        ..., "--feature", help="Feature directory name (e.g. 001-my-feature)"
    ),
    description: str | None = typer.Option(
        None, "--description", help="Original feature description for resume prompts"
    ),
    flags: str | None = typer.Option(
        None, "--flags", help='Normalized active flags, for example "--auto --mono"'
    ),
) -> None:
    """Create pipeline.md for a feature with all phases set to Pending.

    Exit codes:
      0 — pipeline.md created successfully
      1 — feature directory not found or .specs/ missing
    """
    feature_dir = _resolve_feature_dir(feature)
    pipeline_path = feature_dir / "pipeline.md"

    now = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M")
    rows = "\n".join(f"| {PHASE_MAP[slug]} | Pending | — |" for slug in PHASE_ORDER)
    description_line = (
        f"**Feature Description:** {_single_line(description)}\n"
        if description is not None and _single_line(description)
        else ""
    )
    header = (
        f"# Pipeline — {feature}\n\n"
        f"**Started:** {now}\n"
        f"**Flags:** {_format_flags(flags)}\n"
        f"{description_line}\n"
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
    status: str = typer.Option(
        ..., "--status", help="Status slug (e.g. pending, in_progress, done)"
    ),
    timestamp: bool = typer.Option(
        False, "--timestamp", help="Write current UTC timestamp in Completed At column"
    ),
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
    ts = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M") if timestamp else "—"
    new_row = f"| {display_phase} | {display_status} | {ts} |"

    content = pipeline_path.read_text(encoding="utf-8")

    # Flexible whitespace pattern — handles AI-generated padded tables
    pattern = re.compile(r"\|[^|]*\b" + re.escape(display_phase) + r"\b[^|]*\|[^|]*\|[^|]*\|")
    new_content = re.sub(pattern, new_row, content, count=1)

    if new_content == content:
        if phase in _parse_pipeline(content):
            # Row already present and identical to the target — idempotent no-op.
            typer.echo(f"Updated {display_phase} → {display_status}")
            return
        # Row absent (legacy pipeline.md predating this phase) — self-heal by
        # inserting it at the canonical PHASE_ORDER position instead of blocking.
        inserted = _insert_phase_row(content, phase, new_row)
        if inserted is None:
            typer.echo(
                f"Error: phase '{display_phase}' not found in {pipeline_path}",
                err=True,
            )
            raise typer.Exit(1)
        new_content = inserted

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
