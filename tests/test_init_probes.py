"""Real subprocess deadlines include sequential calls and ordinary descendants."""

import time
from pathlib import Path

import pytest

from validator.init_probes import run_command
from validator.init_profile import InitError


def test_ac003_failed_and_missing_tools_are_observed(tmp_path: Path) -> None:
    failed = run_command(
        ("/bin/sh", "-c", "echo rejected >&2; exit 7"), tmp_path, time.monotonic() + 2
    )
    missing = run_command((str(tmp_path / "absent"), "--version"), tmp_path, time.monotonic() + 2)
    assert failed.exit_code == 7 and "rejected" in failed.stderr and not failed.passed
    assert missing.exit_code == 127 and not missing.passed


def test_ac003_global_remaining_budget(tmp_path: Path) -> None:
    deadline = time.monotonic() + 0.35
    first = run_command(("/bin/sleep", "0.2"), tmp_path, deadline)
    second = run_command(("/bin/sleep", "1"), tmp_path, deadline)
    assert first.passed
    assert second.timed_out and second.duration < 0.3
    with pytest.raises(InitError, match="deadline exhausted"):
        run_command(("/bin/echo", "late"), tmp_path, deadline)


def test_ac003_timeout_cancels_descendant_late_write(tmp_path: Path) -> None:
    result = run_command(
        ("/bin/sh", "-c", "(sleep .4; echo bad > late) & wait"), tmp_path, time.monotonic() + 0.1
    )
    assert result.timed_out
    time.sleep(0.5)
    assert not (tmp_path / "late").exists()
