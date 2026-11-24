"""Inspect the project recovery policy without selecting a mission or writing state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal, TypedDict

import typer
import yaml

from validator.cli_resolvers import detect_specs_root

POLICY_RELPATH = ".specs/recovery-policy.yaml"
POLICY_SCHEMA = 1

recovery_app = typer.Typer(name="recovery", help="Inspect the project recovery policy.")


class RecoveryPolicy(TypedDict):
    """JSON result compatible with the format-23 recovery policy inspector."""

    schema: int
    policy: Literal["original", "amended"]
    source: str | None
    problem: str | None


def _marker_problem(marker: Path) -> str | None:
    if marker.is_symlink() or not marker.is_file():
        return "recovery-policy.yaml must be a regular file"
    try:
        document: object = yaml.safe_load(marker.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return "recovery-policy.yaml cannot be read as YAML"
    if not isinstance(document, dict):
        return "recovery-policy.yaml must contain a mapping"
    schema: object = document.get("schema")
    stop_rules: object = document.get("stop_rules")
    if type(schema) is not int or schema != POLICY_SCHEMA or stop_rules != "amended":
        return "recovery-policy.yaml must hold schema: 1 and stop_rules: amended"
    return None


def _read_policy(project: Path) -> RecoveryPolicy:
    marker = project / POLICY_RELPATH
    if not marker.exists() and not marker.is_symlink():
        return {"schema": POLICY_SCHEMA, "policy": "original", "source": None, "problem": None}
    problem = _marker_problem(marker)
    return {
        "schema": POLICY_SCHEMA,
        "policy": "original" if problem else "amended",
        "source": POLICY_RELPATH,
        "problem": problem,
    }


@recovery_app.callback()
def recovery_group() -> None:
    """Inspect the project recovery policy."""


# @spec FR-004: Inspect format-23 policy without certification
#   — .specs/features/122-review-led-delivery/spec.md#fr-004
@recovery_app.command("policy")
def policy_command(
    project: Annotated[Path | None, typer.Option("--project", help="Project directory.")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Print the policy as JSON.")] = False,
) -> None:
    """Read the format-23 marker without mutating the project."""
    root = detect_specs_root(project)
    if root is None:
        typer.echo("Error: no LiveSpec project found", err=True)
        raise typer.Exit(1)
    result = _read_policy(root)
    if as_json:
        typer.echo(json.dumps(result, sort_keys=True))
    else:
        typer.echo(result["policy"])
        if result["problem"] is not None:
            typer.echo(result["problem"], err=True)


def register(app: typer.Typer) -> None:
    """Expose policy inspection through the public CLI."""
    app.add_typer(recovery_app, name="recovery")
