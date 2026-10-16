"""One wall-clock envelope and bounded cleanup for managed validation."""

# @spec FR-001: Shared lifecycle deadline — .specs/features/095-test-time-budgets/spec.md#fr-001
# @spec FR-003: Bounded owned process cleanup — .specs/features/095-test-time-budgets/spec.md#fr-003
from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path

from .test_budgets import BudgetPolicy, load_budget_policy


class BudgetExpired(TimeoutError):
    """The managed lifecycle exhausted its finite wall-clock allowance."""


@dataclass
class ExecutionDeadline:
    """Invocation-local clock; nested operations inherit the same absolute end."""

    policy: BudgetPolicy
    argv: list[str]
    seconds: float
    started: float = field(default_factory=time.monotonic)
    outer_end: float | None = None
    timed_out: bool = False
    granularity: str = "command-only"

    @property
    def end(self) -> float:
        """Absolute finish time, including bounded owned-process cleanup."""
        own_end = self.started + self.seconds
        return min(own_end, self.outer_end) if self.outer_end is not None else own_end

    @property
    def effective_seconds(self) -> float:
        """Budget available at entry, distinct from the policy maximum used by tests."""
        return max(0.0, self.end - self.started)

    @property
    def reserve(self) -> float:
        """Reserve at most 200ms inside the envelope for termination escalation."""
        return min(0.2, self.effective_seconds / 10)

    def remaining(self) -> float:
        """Remaining work allowance, excluding the cleanup reserve."""
        return max(0.0, self.end - self.reserve - time.monotonic())

    def evidence(self) -> dict[str, object]:
        """Describe effective bounds, exception and outcome without certification claims."""
        exception = self.policy.matching(self.argv)
        return {
            "scope": self.argv,
            "command_seconds": self.effective_seconds,
            "declared_command_seconds": self.seconds,
            "individual_seconds": self.policy.frozen(self.argv, self.seconds)["defaults"],
            "test_exceptions": self.policy.frozen(self.argv, self.seconds)["exceptions"],
            "elapsed_seconds": time.monotonic() - self.started,
            "enforcement": self.granularity,
            "exception_id": exception.id if exception else None,
            "exception_reason": exception.reason if exception else None,
            "timed_out": self.timed_out,
        }


_CURRENT: ContextVar[ExecutionDeadline | None] = ContextVar("execution_deadline", default=None)


def current_deadline() -> ExecutionDeadline | None:
    """Return the current command's shared scope, if any."""
    return _CURRENT.get()


def _expired(_signum: int, _frame: object) -> None:
    scope = _CURRENT.get()
    if scope:
        scope.timed_out = True
    detail = (
        f"scope={scope.argv!r} limit={scope.effective_seconds}s "
        f"elapsed={time.monotonic() - scope.started:.3f}s enforcement={scope.granularity}"
        if scope
        else "no active scope"
    )
    raise BudgetExpired(f"managed validation command budget exceeded: {detail}")


@contextmanager
def command_scope(
    root: Path, argv: list[str], timeout: float | None = None
) -> Generator[ExecutionDeadline, None, None]:
    """Bound Python preparation as well as subprocesses, preserving prior alarm state."""
    parent = _CURRENT.get()
    policy = parent.policy if parent else load_budget_policy(root)
    maximum = policy.command_limit(argv, timeout)
    if parent:
        maximum = min(maximum, parent.seconds)
    scope = ExecutionDeadline(
        policy, argv, maximum, started=time.monotonic(), outer_end=parent.end if parent else None
    )
    if threading.current_thread() is not threading.main_thread() or not hasattr(
        signal, "setitimer"
    ):
        raise ValueError("managed validation requires a POSIX main-thread deadline watchdog")
    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.getitimer(signal.ITIMER_REAL)
    previous_at = time.monotonic()
    token = _CURRENT.set(scope)
    signal.signal(signal.SIGALRM, _expired)
    signal.setitimer(signal.ITIMER_REAL, max(0.000001, scope.remaining()))
    try:
        if maximum <= scope.reserve:
            _expired(0, None)
        yield scope
    finally:
        masked = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
        try:
            signal.setitimer(signal.ITIMER_REAL, 0)
            if signal.SIGALRM in signal.sigpending():
                signal.sigwait({signal.SIGALRM})
            _CURRENT.reset(token)
            signal.signal(signal.SIGALRM, previous_handler)
            if scope.timed_out and parent:
                parent.timed_out = True
            remaining = previous_timer[0] - (time.monotonic() - previous_at)
            if parent and remaining <= 0:
                remaining = parent.end - time.monotonic()
            if previous_timer[0] and remaining > 0:
                signal.setitimer(signal.ITIMER_REAL, remaining, previous_timer[1])
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, masked)


def _stop(proc: subprocess.Popen[str], deadline: ExecutionDeadline) -> tuple[str, str]:
    """Terminate the owned session even when a descendant retains stdout/stderr."""
    diagnostics = _signal_group(proc.pid, signal.SIGTERM)
    allowance = max(0.001, min(deadline.reserve / 2, deadline.end - time.monotonic()))
    try:
        output = proc.communicate(timeout=allowance)
    except subprocess.TimeoutExpired:
        output = None
    diagnostics += _signal_group(proc.pid, signal.SIGKILL)
    if output is not None:
        return output[0], output[1] + diagnostics
    try:
        stdout, stderr = proc.communicate(timeout=max(0.001, deadline.end - time.monotonic()))
        return stdout, stderr + diagnostics
    except subprocess.TimeoutExpired as exc:
        for stream in (proc.stdout, proc.stderr):
            if stream:
                stream.close()
        return _text(exc.stdout), _text(exc.stderr) + diagnostics


def arm_finalization(scope: ExecutionDeadline) -> None:
    """Cleanup/publication may consume only the reserve inside the original deadline."""
    remaining = scope.end - time.monotonic()
    if remaining <= 0:
        raise BudgetExpired("command budget exhausted before evidence publication")
    signal.setitimer(signal.ITIMER_REAL, remaining)


def disarm_deadline_alarm() -> None:
    """Drain an owned pending alarm before returning an already-expired outcome."""
    masked = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
    try:
        signal.setitimer(signal.ITIMER_REAL, 0)
        if signal.SIGALRM in signal.sigpending():
            signal.sigwait({signal.SIGALRM})
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, masked)


def _signal_group(pid: int, signum: int) -> str:
    """A kernel cleanup denial is an explicit gap, never a successful termination claim."""
    try:
        os.killpg(pid, signum)
    except ProcessLookupError:
        pass
    except PermissionError as exc:
        return f"\nCleanup gap: cannot signal owned process group {pid}: {exc}"
    return ""


def _text(value: str | bytes | None) -> str:
    return value.decode(errors="replace") if isinstance(value, bytes) else value or ""


def run_owned(argv: list[str], root: Path, env: dict[str, str]) -> tuple[int, str, str]:
    """Run one owned process group and return exit 124 on any deadline expiry."""
    scope = current_deadline()
    if scope is None:
        raise ValueError("run_owned requires a managed command scope")
    if scope.remaining() <= 0:
        scope.timed_out = True
        return 124, "", "Command budget exhausted before spawn"
    try:
        proc = subprocess.Popen(
            argv,
            cwd=root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    except FileNotFoundError:
        return 127, "", f"command not found: {argv[0]}"
    try:
        while scope.remaining() > 0:
            try:
                stdout, stderr = proc.communicate(timeout=min(0.1, scope.remaining()))
                if proc.returncode == 124 or "LIVESPEC_TEST_TIMEOUT " in stderr:
                    break
                return proc.returncode or 0, stdout, stderr
            except subprocess.TimeoutExpired:
                if proc.poll() == 124:
                    break
    except BudgetExpired:
        pass
    except BaseException:
        signal.setitimer(signal.ITIMER_REAL, 0)
        _stop(proc, scope)
        raise
    scope.timed_out = True
    signal.setitimer(signal.ITIMER_REAL, 0)
    stdout, stderr = _stop(proc, scope)
    arm_finalization(scope)
    return (
        124,
        stdout,
        stderr + f"\nTIMEOUT scope={scope.argv!r} limit={scope.seconds}s "
        f"elapsed={time.monotonic() - scope.started:.3f}s",
    )
