"""``livespec run`` — subprocess wrapper + manual recorder for run artifacts.

# @spec FR-006: artifact emitter
#   — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-006
"""

from pathlib import Path

import typer

from ..command_registry import normalize_command_name
from ..exceptions import ExpectationsInvalid, ExpectationsMissing, OverrideMalformed
from ..expectations import load_expectations
from ..run_artifact import find_latest_artifact, record_from_streams, record_subprocess
from ..verify_output import evaluate, render_human

run_app = typer.Typer(name="run", help="Record LiveSpec command run artifacts.")
WRAP_COMMAND_ARGUMENT = typer.Argument(
    ...,
    help="Command name or alias (e.g. 'spec-status', 'status', or '/spec.status').",
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
    help="Command name or alias.",
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
    command = normalize_command_name(command)
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
    command = normalize_command_name(command)
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


@run_app.command("finalize")
def finalize_cmd(
    command: str = RECORD_COMMAND_OPTION,
    exit_code: int = RECORD_EXIT_CODE_OPTION,
    flags: str = RECORD_FLAGS_OPTION,
    stdout_file: Path | None = STDOUT_FILE_OPTION,
    stderr_file: Path | None = STDERR_FILE_OPTION,
    duration_ms: int = DURATION_MS_OPTION,
    cwd: Path | None = RUN_CWD_OPTION,
    runs_dir: Path | None = RUNS_DIR_OPTION,
) -> None:
    """Record captured streams, then verify them against expectations.

    # @spec FR-005: mandatory run finalization
    #   — .specs/features/048-command-validation-hardening/spec.md#fr-005
    # @spec FR-004: alias-compatible finalization
    #   — .specs/features/049-command-naming-normalization/spec.md#fr-004
    """
    effective_cwd = cwd if cwd is not None else Path.cwd()
    normalized_command = normalize_command_name(command)
    stdout = stdout_file.read_text(encoding="utf-8") if stdout_file else ""
    stderr = stderr_file.read_text(encoding="utf-8") if stderr_file else ""
    flag_list = flags.split() if flags else []
    artifact = record_from_streams(
        normalized_command,
        cwd=effective_cwd,
        flags=flag_list,
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        duration_ms=duration_ms,
        runs_dir=runs_dir,
    )
    target_runs_dir = runs_dir or (effective_cwd / ".specs" / ".runs")
    artifact_path = find_latest_artifact(normalized_command, target_runs_dir)
    livespec_root = _detect_livespec_root()
    try:
        expectations = load_expectations(
            normalized_command,
            effective_cwd,
            livespec_root,
        )
    except (ExpectationsInvalid, ExpectationsMissing, OverrideMalformed) as exc:
        typer.echo(f"finalize blocked: {exc}", err=True)
        raise typer.Exit(2) from exc
    report = evaluate(expectations, artifact, artifact_path=artifact_path)
    typer.echo(render_human(report))
    raise typer.Exit(report.exit_code)


def _detect_livespec_root() -> Path:
    """Resolve the LiveSpec checkout root by walking parents of this module."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "commands").is_dir() and (parent / "validator").is_dir():
            return parent
    return here.parents[2]


# Export the Typer sub-app for registration from the top-level CLI module.
__all__ = ["run_app"]
