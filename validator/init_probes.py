"""Bound initialization subprocesses by one deadline and reap their process groups."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from .init_profile import InitError, ObservedProfile

# Version checks must stay cheap; every call also consumes the total run deadline.
VERSION_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class ProbeResult:
    """Actual argv, output, exit and elapsed time of a bounded invocation."""

    argv: tuple[str, ...]
    stdout: str
    stderr: str
    exit_code: int
    duration: float
    timed_out: bool = False

    @property
    def passed(self) -> bool:
        """Return whether this invocation completed with exit zero."""
        return self.exit_code == 0 and not self.timed_out


def _kill_group(process: subprocess.Popen[str]) -> None:
    # All children inherit a new process group. Kill remaining grandchildren too,
    # including children that kept running after their immediate parent exited.
    # A completed group has no remaining process to cancel.
    with suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGKILL)


# @spec FR-002: Genuine bounded argv checks
#   — .specs/features/080-autonomous-from-code-recovery/spec.md#fr-002
def run_command(
    argv: tuple[str, ...], project: Path, deadline: float, *, cap: float | None = None
) -> ProbeResult:
    """Execute argv with closed stdin, a shared deadline and descendant cleanup.

    Args:
        argv: Explicit arguments; shell expansion is never performed.
        project: Working directory of the selected project.
        deadline: Monotonic absolute deadline shared by every external call.
        cap: Optional stricter timeout for this invocation.
    Returns:
        Captured real outputs, duration and success/failure details.
    Raises:
        InitError: The total deadline was exhausted before starting a process.
    """
    start = time.monotonic()
    remaining = deadline - start
    if remaining <= 0:
        raise InitError(f"total initialization deadline exhausted before {argv[0]}")
    timeout = min(remaining, cap) if cap is not None else remaining
    try:
        # A new session makes the entire ordinary descendant tree cancellable.
        process = subprocess.Popen(
            argv,
            cwd=project,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    except OSError as error:
        return ProbeResult(argv, "", str(error), 127, time.monotonic() - start)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_group(process)
        stdout, stderr = process.communicate()
    finally:
        _kill_group(process)
    code = process.returncode if process.returncode is not None else 1
    return ProbeResult(argv, stdout, stderr, code, time.monotonic() - start, timed_out)


def require_success(result: ProbeResult, step: str) -> None:
    """Raise a contextual failure for an unsuccessful bounded invocation."""
    if not result.passed:
        reason = "timeout" if result.timed_out else f"exit {result.exit_code}"
        raise InitError(
            f"{step}: {' '.join(result.argv)}: {reason}: "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )


def run_probes(profile: ObservedProfile, project: Path, deadline: float) -> tuple[ProbeResult, ...]:
    """Execute only observed tools' version checks under the shared deadline."""
    return tuple(
        run_command((tool, "--version"), project, deadline, cap=VERSION_TIMEOUT_SECONDS)
        for tool in profile.tools
    )
