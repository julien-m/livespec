"""Deterministic deadline seams for bounded init subprocess tests (feature 080, AC-003)."""

from __future__ import annotations

import subprocess
from typing import Any

import pytest

from validator import init_probes


class FakeClock:
    """Monotonic clock that only moves when a test advances it."""

    def __init__(self, now: float = 1000.0) -> None:
        self.now = now

    def monotonic(self) -> float:
        """Return the controlled current time."""
        return self.now


def install_deadline_seams(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> list[float | None]:
    """Drive ``run_command`` budgets from ``clock`` and record every real wait timeout.

    Processes stay real; only the budget arithmetic is controlled, so assertions on the
    timeout handed to ``communicate`` do not depend on machine load.
    """
    timeouts: list[float | None] = []

    class RecordingPopen(subprocess.Popen[str]):
        def communicate(self, input: Any = None, timeout: float | None = None) -> tuple[Any, Any]:
            timeouts.append(timeout)
            return super().communicate(input, timeout)

    monkeypatch.setattr(init_probes, "time", clock)
    monkeypatch.setattr(init_probes.subprocess, "Popen", RecordingPopen)
    return timeouts
