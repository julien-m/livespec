"""CLI command for deterministic command contract audits."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from ..command_audit import audit_commands
from ..command_registry import CommandNamingPolicy

REPO_OPTION = typer.Option(
    Path("."),
    "--repo",
    help="Repository root containing commands/.",
)
JSON_OPTION = typer.Option(False, "--json", help="Emit JSON.")
NAMING_POLICY_OPTION = typer.Option(
    CommandNamingPolicy.HYPHENATED.value,
    "--naming-policy",
    help="Canonical naming policy: dotted or hyphenated.",
)


def register(app: typer.Typer) -> None:
    """Register ``livespec command-audit``."""
    app.command(
        name="command-audit",
        help="Audit command docs, expectations, routing references, and naming.",
    )(command_audit_command)


def command_audit_command(
    repo: Path = REPO_OPTION,
    json_out: bool = JSON_OPTION,
    naming_policy: str = NAMING_POLICY_OPTION,
) -> None:
    """Run the deterministic command audit."""
    try:
        policy = CommandNamingPolicy(naming_policy)
    except ValueError as exc:
        typer.echo("Error: --naming-policy must be dotted or hyphenated", err=True)
        raise typer.Exit(2) from exc

    report = audit_commands(repo.resolve(), naming_policy=policy)
    if json_out:
        typer.echo(json.dumps(report.to_dict(), indent=2))
    else:
        typer.echo(f"LiveSpec command audit: {len(report.entries)} commands")
        for entry in report.entries:
            verdict = "OK" if entry.passed else "FAIL"
            typer.echo(f"{verdict} {entry.command.name}: {entry.score}/5")
            for check in entry.checks:
                typer.echo(f"  - {check.name}: {check.status} ({check.detail})")
        typer.echo(f"summary: score={report.score}/5 failed={report.failed_count}")
    raise typer.Exit(0 if report.passed else 1)


__all__ = ["command_audit_command", "register"]
