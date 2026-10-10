"""Emit goal CLI results and persist closed JSON documents."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from .goal_json import JsonObject, copy_json_object
from .outcome import exit_code_for
from .run_artifacts import ArchiveResult


def write_json_text_atomically(path: Path, text: str) -> None:
    """Replace a JSON text file through a sibling temporary file.

    Args:
        path: Final JSON path.
        text: Complete serialized JSON document.

    Side effects:
        Writes and renames one sibling temporary file.
    """
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def read_json_object(path: Path) -> JsonObject:
    """Read one closed JSON object.

    Args:
        path: Explicit readable JSON file.

    Returns:
        An isolated JSON object.

    Raises:
        OSError: If the file cannot be read.
        json.JSONDecodeError: If JSON is malformed or not an object.
    """
    parsed: object = json.loads(path.read_text(encoding="utf-8"))
    document = copy_json_object(parsed)
    if document is None:
        raise json.JSONDecodeError("JSON root must be an object", path.as_posix(), 0)
    return document


def archive_blocked(reason: str, *, json_out: bool) -> typer.Exit:
    """Emit a blocked archive result and return exit 2.

    Args:
        reason: One-line blocked reason.
        json_out: Whether to include a machine-readable stdout envelope.

    Returns:
        A ``typer.Exit(2)`` for the caller to raise.

    Side effects:
        Writes the stable diagnostic to stderr and optionally stdout.
    """
    if json_out:
        typer.echo(json.dumps({"outcome": "blocked", "reason": reason}))
    typer.echo(f"goal archive blocked: {reason}", err=True)
    return typer.Exit(2)


def emit_archive_result(result: ArchiveResult, *, json_out: bool) -> None:
    """Emit an archive result and apply its stable exit mapping.

    Args:
        result: Completed archive domain result.
        json_out: Whether to emit the JSON representation.

    Raises:
        typer.Exit: With 1 for drift/error or 2 for blocked.

    Side effects:
        Writes the stable archive result to stdout or stderr.
    """
    if result.outcome == "blocked" or result.path is None:
        raise archive_blocked(result.blocked_reason or "unknown reason", json_out=json_out)
    if json_out:
        typer.echo(json.dumps({"archived": result.path.as_posix(), "outcome": result.outcome}))
    else:
        typer.echo(f"archived: {result.path.as_posix()} | outcome:{result.outcome}")
    final_exit = exit_code_for(result.outcome)
    if final_exit != 0:
        raise typer.Exit(final_exit)


__all__ = [
    "archive_blocked",
    "emit_archive_result",
    "read_json_object",
    "write_json_text_atomically",
]
