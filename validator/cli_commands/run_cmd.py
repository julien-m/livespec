"""``livespec run`` — subprocess wrapper + manual recorder for run artifacts.

# @spec FR-006: artifact emitter — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-006
"""

from __future__ import annotations

from pathlib import Path

import typer

from ..run_artifact import record_from_streams, record_subprocess

run_app = typer.Typer(name="run", help="Record LiveSpec command run artifacts.")


@run_app.command("wrap")
def wrap_cmd(
    command: str = typer.Argument(..., help="Logical command name (e.g. 'status')."),
    argv: list[str] = typer.Argument(
        ...,
        help="Subprocess to run (e.g. -- python -m mytool ...).",
    ),
    cwd: Path = typer.Option(
        Path.cwd(),
        "--cwd",
        help="Working directory (defaults to current).",
    ),
    runs_dir: Path | None = typer.Option(
        None,
        "--runs-dir",
        help="Override artifact directory (defaults to <cwd>/.specs/.runs).",
    ),
) -> None:
    """Run ``argv`` as a subprocess and write a RunArtifact for it."""
    if not argv:
        typer.echo("Error: argv is empty (use -- to separate)", err=True)
        raise typer.Exit(2)
    artifact = record_subprocess(
        command,
        argv,
        cwd=cwd,
        runs_dir=runs_dir,
    )
    typer.echo(f"recorded {command} -> exit={artifact.exit_code} ({artifact.timestamp})")
    raise typer.Exit(artifact.exit_code)


@run_app.command("record")
def record_cmd(
    command: str = typer.Option(..., "--command", help="Logical command name."),
    exit_code: int = typer.Option(0, "--exit-code", help="Captured exit code."),
    flags: str = typer.Option("", "--flags", help="Space-separated flags string."),
    stdout_file: Path | None = typer.Option(
        None, "--stdout-file", help="Path to a file holding captured stdout."
    ),
    stderr_file: Path | None = typer.Option(
        None, "--stderr-file", help="Path to a file holding captured stderr."
    ),
    duration_ms: int = typer.Option(0, "--duration-ms", help="Duration in ms."),
    cwd: Path = typer.Option(Path.cwd(), "--cwd", help="Working directory."),
    runs_dir: Path | None = typer.Option(
        None, "--runs-dir", help="Override artifact directory."
    ),
) -> None:
    """Write an artifact from already-captured streams (manual API)."""
    stdout = stdout_file.read_text(encoding="utf-8") if stdout_file else ""
    stderr = stderr_file.read_text(encoding="utf-8") if stderr_file else ""
    flag_list = flags.split() if flags else []
    artifact = record_from_streams(
        command,
        cwd=cwd,
        flags=flag_list,
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        duration_ms=duration_ms,
        runs_dir=runs_dir,
    )
    typer.echo(f"recorded {command} -> exit={artifact.exit_code} ({artifact.timestamp})")


__all__ = ["run_app"]
