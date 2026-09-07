# @spec(FR-013)
# .specs/features/078-requirement-evidence-integrity/spec.md#fr-013
"""Bound child execution; preserve uncertainty about detached or backend workers."""

from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProcessCapture:
    """Observed output; process control only covers the original locally owned group."""

    exit_code: int
    stdout: str
    stderr: str
    duration_sec: float
    timed_out: bool = False
    argv: tuple[str, ...] = ()
    control_complete: bool = True
    control_scope: str = "observed_local_processes"


def run_process(
    argv: list[str], cwd: Path, timeout_sec: float, *, env: dict[str, str] | None = None
) -> ProcessCapture:
    """Never signal detached PIDs using imprecise creation timestamps or process names."""
    if timeout_sec <= 0:
        raise ValueError("timeout_sec must be positive")
    started = time.monotonic()
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    tracker = _Descendants(process.pid)
    stop = threading.Event()
    monitor = threading.Thread(target=tracker.monitor, args=(stop,), daemon=True)
    monitor.start()
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        timed_out = True
        stdout, stderr = _stop_timed_out(process, tracker)
    finally:
        stop.set()
        monitor.join(timeout=2)
        tracker.check_survivors()
    return ProcessCapture(
        process.returncode,
        stdout,
        stderr,
        time.monotonic() - started,
        timed_out,
        tuple(argv),
        tracker.complete and not monitor.is_alive(),
    )


def _stop_timed_out(
    process: subprocess.Popen[str],
    tracker: _Descendants,
) -> tuple[str, str]:
    """Stop only the Popen-owned original group and preserve incomplete-control evidence."""
    tracker.complete = False  # A deadline cannot attest unobserved detached/backend workers.
    tracker.observe()
    if tracker.detached:
        tracker.complete = False
    # Before communicate reaps it, Popen owns the original session leader's PID.
    # Only this original session's group is eligible; detached workers are not signalled.
    if process.returncode is None:
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
    process.kill()
    try:
        stdout, stderr = process.communicate(timeout=1)
    except subprocess.TimeoutExpired as exc:
        tracker.complete = False
        stdout, stderr = _partial_text(exc.stdout), _partial_text(exc.stderr)
        if process.stdout:
            process.stdout.close()
        if process.stderr:
            process.stderr.close()
        process.wait(timeout=1)
    return stdout, stderr


class _Descendants:
    """Observation is diagnostic, never permission to kill a detached process."""

    def __init__(self, root: int) -> None:
        self.root = root
        self.complete = True
        self.observed: set[int] = set()
        self.detached: set[int] = set()

    def check_survivors(self) -> None:
        for pid in self.observed:
            try:
                os.kill(pid, 0)  # Observation only; PID reuse can only conservatively reject proof.
            except ProcessLookupError:
                continue
            except PermissionError:
                pass
            self.complete = False

    def monitor(self, stop: threading.Event) -> None:
        while not stop.is_set():
            self.observe()
            stop.wait(0.05)

    def observe(self) -> None:
        try:
            captured = subprocess.run(
                ["ps", "-ax", "-o", "pid=,ppid=,pgid="],
                capture_output=True,
                text=True,
                timeout=1,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            self.complete = False
            return
        if captured.returncode:
            self.complete = False
            return
        rows = [
            tuple(map(int, line.split()))
            for line in captured.stdout.splitlines()
            if len(line.split()) == 3 and all(item.isdigit() for item in line.split())
        ]
        parents = {self.root}
        while parents:
            children = {pid for pid, parent, _group in rows if parent in parents}
            self.observed.update(children)
            self.detached.update(
                pid for pid, _, group in rows if pid in children and group != self.root
            )
            parents = children


def _partial_text(value: str | bytes | None) -> str:
    return value.decode(errors="replace") if isinstance(value, bytes) else value or ""
