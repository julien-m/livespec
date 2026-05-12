"""``livespec run`` — subprocess wrapper + manual recorder for run artifacts.

# @spec FR-006: artifact emitter
#   — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-006
"""

from pathlib import Path

import typer

from ..run_artifact import record_from_streams, record_subprocess

run_app = typer.Typer(name="run", help="Record LiveSpec command run artifacts.")
WRAP_COMMAND_ARGUMENT = typer.Argument(
    ...,
    help="Logical command name (e.g. 'status').",
)
WRAP_ARGV_ARGUMENT = typer.Argument(
    None,
    help="Subprocess to run (use -- to separate). Required.",
)
RUN_CWD_OPTION = typer.Option(
    None,
    "--cwd",
    help="Working directory (defaults to current).",
)
RUNS_DIR_OPTION = typer.Option(
    None,
    "--runs-dir",
    help="Override artifact directory (defaults to <cwd>/.specs/.runs).",
)
RUN_SHELL_OPTION = typer.Option(
    False,
    "--shell",
    help="Run argv through `bash -c` (enables globs, pipes, vars).",
)
RECORD_COMMAND_OPTION = typer.Option(
    ...,
    "--command",
    help="Logical command name.",
)
RECORD_EXIT_CODE_OPTION = typer.Option(
    0,
    "--exit-code",
    help="Captured exit code.",
)
RECORD_FLAGS_OPTION = typer.Option(
    "",
    "--flags",
    help="Space-separated flags string.",
)
STDOUT_FILE_OPTION = typer.Option(
    None,
    "--stdout-file",
    help="Path to a file holding captured stdout.",
)
STDERR_FILE_OPTION = typer.Option(
    None,
    "--stderr-file",
    help="Path to a file holding captured stderr.",
)
DURATION_MS_OPTION = typer.Option(
    0,
    "--duration-ms",
    help="Duration in ms.",
)


@run_app.command("wrap")
def wrap_cmd(
    command: str = WRAP_COMMAND_ARGUMENT,
    argv: list[str] | None = WRAP_ARGV_ARGUMENT,
    cwd: Path | None = RUN_CWD_OPTION,
    runs_dir: Path | None = RUNS_DIR_OPTION,
    shell: bool = RUN_SHELL_OPTION,
) -> None:
    """Run ``argv`` as a subprocess and write a RunArtifact for it.

    Usage: ``livespec run wrap <command> [--cwd D] [--runs-dir D] [--shell] -- <argv...>``
    """
    argv_list = list(argv) if argv else []
    if not argv_list:
        typer.echo("Error: argv is empty (use -- to separate)", err=True)
        raise typer.Exit(2)
    effective_cwd = cwd if cwd is not None else Path.cwd()
    if shell:
        # Shell mode delegates quoting, pipes, and globbing to bash; the wrapped
        # subprocess still reports a single exit code and merged shell semantics.
        argv_list = ["bash", "-c", " ".join(argv_list)]
    artifact = record_subprocess(
        command,
        argv_list,
        cwd=effective_cwd,
        runs_dir=runs_dir,
    )
    typer.echo(f"recorded {command} -> exit={artifact.exit_code} ({artifact.timestamp})")
    raise typer.Exit(artifact.exit_code)


@run_app.command("record")
def record_cmd(
    command: str = RECORD_COMMAND_OPTION,
    exit_code: int = RECORD_EXIT_CODE_OPTION,
    flags: str = RECORD_FLAGS_OPTION,
    stdout_file: Path | None = STDOUT_FILE_OPTION,
    stderr_file: Path | None = STDERR_FILE_OPTION,
    duration_ms: int = DURATION_MS_OPTION,
    cwd: Path | None = RUN_CWD_OPTION,
    runs_dir: Path | None = RUNS_DIR_OPTION,
) -> None:
    """Write an artifact from already-captured streams (manual API)."""
    effective_cwd = cwd if cwd is not None else Path.cwd()
    stdout = stdout_file.read_text(encoding="utf-8") if stdout_file else ""
    stderr = stderr_file.read_text(encoding="utf-8") if stderr_file else ""
    flag_list = flags.split() if flags else []
    artifact = record_from_streams(
        command,
        cwd=effective_cwd,
        flags=flag_list,
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        duration_ms=duration_ms,
        runs_dir=runs_dir,
    )
    typer.echo(f"recorded {command} -> exit={artifact.exit_code} ({artifact.timestamp})")


# Export the Typer sub-app for registration from the top-level CLI module.
__all__ = ["run_app"]
