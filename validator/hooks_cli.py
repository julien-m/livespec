"""CLI surface for hook + integration resolution.

Exposes two sub-applications wired into ``validator.cli``:

* ``livespec hooks resolve --event <before|after> --command <cmd> [--feature <slug>]``
  — runtime adapter on top of :func:`validator.hook_resolver.render_chain_for_stdout`.
  Invoked by ``commands/*.md`` via the Bash tool through the directive in
  ``system/anti-drift-block.md``.

* ``livespec integrations list``
  — diagnostic table of discovered Level 0 integrations.

Absence-tolerance contract: ``hooks resolve`` ALWAYS exits 0 — empty stdout
when nothing applies. Errors that prevent resolution (unknown command,
malformed YAML) print a single stderr line and still exit 0 (no stacktrace).
"""

from __future__ import annotations

import sys
import traceback

import typer

from validator.command_registry import normalize_command_name
from validator.hook_resolver import render_chain_for_stdout
from validator.integrations import (
    discover_integrations,
    valid_command_names,
)

hooks_app = typer.Typer(name="hooks", help="LiveSpec hook resolution surface.")
integrations_app = typer.Typer(
    name="integrations", help="User-level Markdown integrations (Level 0)."
)


@hooks_app.command("resolve")
def hooks_resolve(
    event: str = typer.Option(
        ..., "--event", help="Hook event: 'before' or 'after'."
    ),
    command: str = typer.Option(
        ..., "--command", help="LiveSpec command name or alias."
    ),
    feature: str | None = typer.Option(
        None,
        "--feature",
        help="Feature slug (e.g. 042-foo) for template variable substitution.",
    ),
) -> None:
    """Resolve the injection chain for ``before|after`` of ``<command>`` and print to stdout.

    Exit codes:
        0 — always (absence-tolerance). Empty stdout means nothing to inject.

    On unknown command or unknown event, prints a single warning to stderr
    and still exits 0 so that callers (LLM-driven slash commands) never
    crash mid-execution.
    """
    if event not in ("before", "after"):
        typer.echo(f'⚠ unknown event "{event}" — must be "before" or "after"', err=True)
        raise typer.Exit(0)

    command = normalize_command_name(command)
    valid_cmds = valid_command_names()
    if command not in valid_cmds:
        typer.echo(
            f'⚠ unknown command "{command}" — must be one of: {", ".join(sorted(valid_cmds))}',
            err=True,
        )
        raise typer.Exit(0)

    try:
        rendered = render_chain_for_stdout(event, command, feature)
    except Exception as exc:
        # Surface a single concise stderr line; never leak a stacktrace.
        msg = str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__
        typer.echo(f"⚠ hook resolution failed: {msg}", err=True)
        if sys.flags.dev_mode:
            traceback.print_exc(file=sys.stderr)
        raise typer.Exit(0) from None

    if rendered:
        typer.echo(rendered)
    raise typer.Exit(0)


@integrations_app.command("list")
def integrations_list() -> None:
    """Print a table of all discovered Level 0 integrations."""
    try:
        results = discover_integrations()
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from None

    if not results:
        typer.echo("No user integrations found in ~/.config/livespec/.")
        raise typer.Exit(0)

    typer.echo(f"{'NAME':<20} {'PHASE':<8} {'MODE':<10} {'ORDER':<6} COMMANDS  PATH")
    for i in results:
        typer.echo(
            f"{i.name:<20} {i.phase:<8} {i.mode:<10} {i.order:<6} "
            f"{','.join(i.commands)}  {i.path}"
        )
    raise typer.Exit(0)


__all__ = ["hooks_app", "integrations_app"]
