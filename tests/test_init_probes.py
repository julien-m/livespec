"""Real subprocess deadlines include sequential calls and ordinary descendants."""

import time
from pathlib import Path

import pytest

from tests.init_clock_support import FakeClock, install_deadline_seams
from validator.init_probes import run_command
from validator.init_profile import InitError


def test_ac003_failed_and_missing_tools_are_observed(tmp_path: Path) -> None:
    failed = run_command(
        ("/bin/sh", "-c", "echo rejected >&2; exit 7"), tmp_path, time.monotonic() + 2
    )
    missing = run_command((str(tmp_path / "absent"), "--version"), tmp_path, time.monotonic() + 2)
    assert failed.exit_code == 7 and "rejected" in failed.stderr and not failed.passed
    assert missing.exit_code == 127 and not missing.passed


def test_ac003_global_remaining_budget(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Sequential calls share one deadline: each real wait is bounded by what remains."""
    clock = FakeClock()
    timeouts = install_deadline_seams(monkeypatch, clock)
    deadline = clock.now + 30.15
    first = run_command(("/bin/sh", "-c", "exit 0"), tmp_path, deadline)
    clock.now += 30.0  # the first call consumed 30 s of the shared budget
    started = time.perf_counter()
    second = run_command(("/bin/sleep", "30"), tmp_path, deadline)
    elapsed = time.perf_counter() - started
    capped = run_command(("/bin/sleep", "30"), tmp_path, deadline, cap=0.05)
    assert first.passed and timeouts[0] == pytest.approx(30.15)
    # Only the remaining 0.15 s was granted, so a 30 s child is cut and its group reaped.
    assert timeouts[1] == pytest.approx(0.15)
    assert second.timed_out and not second.passed and elapsed < 10
    # A stricter per-call cap wins over the larger remaining budget.
    assert capped.timed_out and timeouts[-2] == pytest.approx(0.05)
    clock.now = deadline
    with pytest.raises(InitError, match="deadline exhausted"):
        run_command(("/bin/echo", "late"), tmp_path, deadline)


def test_ac003_timeout_cancels_descendant_late_write(tmp_path: Path) -> None:
    result = run_command(
        ("/bin/sh", "-c", "(sleep .4; echo bad > late) & wait"), tmp_path, time.monotonic() + 0.1
    )
    assert result.timed_out
    time.sleep(0.5)
    assert not (tmp_path / "late").exists()
