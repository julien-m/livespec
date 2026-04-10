"""Commit context bridge CLI for LiveSpec.

Manages a JSON context file (.specs/hooks/.commit-context.json) that bridges
the Python pipeline orchestrator with the Claude agent's commit hook invocation.

ADR canonical path (confirmed from system/spec-system.md and system/hooks.md):
    .specs/stacks/decisions/ADR-*.md

Schema v1:
    {
        "version": 1,
        "feature_name": "NNN-feature-name",
        "spec_path": "/absolute/path/to/spec.md",
        "plan_path": "/absolute/path/to/plan.md",
        "adr_paths": "/absolute/path/ADR-001.md,/absolute/path/ADR-002.md"
    }

    adr_paths is empty string "" when no ADRs exist (NOT null, NOT omitted).
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from .exceptions import SpecsRootNotFoundError
from .specs_utils import find_specs_root

commit_context_app = typer.Typer(name="commit-context", help="Commit context bridge for LiveSpec pipelines.")

_CONTEXT_FILE = ".commit-context.json"


def _get_context_path(specs_root: Path) -> Path:
    """Return the path to the commit context JSON file."""
    return specs_root / "hooks" / _CONTEXT_FILE


@commit_context_app.command()
def write(
    feature: str = typer.Option(..., "--feature", help="Feature directory name (e.g. 001-my-feature)"),
) -> None:
    """Write commit context JSON for the given feature.

    Resolves spec_path, plan_path, and adr_paths from .specs/ layout.
    Creates .specs/hooks/ directory if missing.

    Exit codes: 0 = success, 1 = .specs/ or feature directory missing.
    """
    try:
        specs_root = find_specs_root()
    except SpecsRootNotFoundError:
        typer.echo("Error: .specs/ directory not found", err=True)
        raise typer.Exit(1)  # noqa: B904

    feature_dir = specs_root / "features" / feature
    if not feature_dir.is_dir():
        typer.echo(f"Error: feature directory not found: {feature_dir}", err=True)
        raise typer.Exit(1)

    spec_path = feature_dir / "spec.md"
    plan_path = feature_dir / "plan.md"

    # Glob ADRs from canonical path
    adr_paths_list = sorted(specs_root.glob("stacks/decisions/ADR-*.md"))
    adr_paths_str = ",".join(str(p.resolve()) for p in adr_paths_list)

    data = {
        "version": 1,
        "feature_name": feature,
        "spec_path": str(spec_path.resolve()),
        "plan_path": str(plan_path.resolve()),
        "adr_paths": adr_paths_str,
    }

    hooks_dir = specs_root / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    context_path = _get_context_path(specs_root)
    context_path.write_text(json.dumps(data, indent=None))

    typer.echo("Context written")
    raise typer.Exit(0)


@commit_context_app.command()
def read() -> None:
    """Read commit context JSON and print to stdout.

    Exit codes: 0 = success, 1 = file missing.
    """
    try:
        specs_root = find_specs_root()
    except SpecsRootNotFoundError:
        typer.echo("Error: .specs/ directory not found", err=True)
        raise typer.Exit(1)  # noqa: B904

    context_path = _get_context_path(specs_root)
    if not context_path.exists():
        typer.echo("Error: .commit-context.json not found", err=True)
        raise typer.Exit(1)

    typer.echo(context_path.read_text())
    raise typer.Exit(0)


@commit_context_app.command()
def clear() -> None:
    """Remove commit context JSON if it exists (idempotent).

    Exit codes: 0 = success or file absent, 1 = removal failure.
    """
    try:
        specs_root = find_specs_root()
    except SpecsRootNotFoundError:
        # If no .specs/ root, file obviously doesn't exist — idempotent exit 0
        raise typer.Exit(0)  # noqa: B904

    context_path = _get_context_path(specs_root)
    if not context_path.exists():
        raise typer.Exit(0)

    try:
        context_path.unlink()
    except OSError as exc:
        typer.echo(f"Error: failed to remove {context_path}: {exc}", err=True)
        raise typer.Exit(1)  # noqa: B904

    typer.echo("Context cleared")
    raise typer.Exit(0)
