"""Small real subprocesses prove bounded preparation and owned-descendant cleanup."""

from __future__ import annotations

import os
import signal
import sys
import time
from pathlib import Path

import pytest

from validator.execution_deadline import BudgetExpired, command_scope, run_owned


# @spec AC-001: Whole lifecycle shared cap — .specs/features/095-test-time-budgets/spec.md#ac-001
def test_preparation_and_nested_work_share_one_deadline(tmp_path: Path) -> None:
    before = time.monotonic()
    previous = signal.getsignal(signal.SIGALRM)
    with pytest.raises(BudgetExpired), command_scope(tmp_path, ["validation"], 0.25) as outer:
        time.sleep(0.06)
        with command_scope(tmp_path, ["coverage"]) as inner:
            assert inner.end == outer.end
            time.sleep(1)
    assert signal.getsignal(signal.SIGALRM) == previous
    assert outer.timed_out and time.monotonic() - before < 0.8


def test_term_ignoring_descendant_and_inherited_pipe_are_bounded(tmp_path: Path) -> None:
    pid_file = tmp_path / "child.pid"
    child = (
        "import os,signal,time;from pathlib import Path;"
        "signal.signal(signal.SIGTERM,signal.SIG_IGN);"
        "Path('child.pid').write_text(str(os.getpid()));time.sleep(20)"
    )
    code = (
        f"import subprocess,sys;subprocess.Popen([sys.executable,'-c',{child!r}]);"
        "raise SystemExit(124)"
    )
    before = time.monotonic()
    with command_scope(tmp_path, [sys.executable, "-c", code], 0.5) as scope:
        status, _, stderr = run_owned([sys.executable, "-c", code], tmp_path, dict(os.environ))
        assert scope.timed_out
    # @spec AC-003: Owned execution stops on expiry
    # — .specs/features/095-test-time-budgets/spec.md#ac-003
    assert status == 124 and "TIMEOUT" in stderr
    assert time.monotonic() - before < 1.2
    # A killed descendant can briefly remain a zombie: it must never keep executing.
    if pid_file.exists():
        pid = int(pid_file.read_text())
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        import subprocess

        state = subprocess.run(
            ["ps", "-o", "stat=", "-p", str(pid)],
            capture_output=True,
            text=True,
            timeout=1,
            check=False,
        )
        assert not state.stdout.strip() or state.stdout.strip().startswith("Z")


def test_normal_result_retains_stdout_and_status(tmp_path: Path) -> None:
    argv = [sys.executable, "-c", "print('normal')"]
    with command_scope(tmp_path, argv, 1) as scope:
        result = run_owned(argv, tmp_path, dict(os.environ))
    assert result == (0, "normal\n", "")
    assert scope.evidence()["timed_out"] is False


def test_nested_evidence_reports_remaining_without_invalidating_declared_tests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prior work shrinks effective time, while a valid test declaration keeps its maximum."""
    from validator import execution_deadline
    from validator.execution_test_budget import resolve_test_budget
    from validator.test_budgets import BudgetException, BudgetPolicy

    clock = [1000.0]
    policy = BudgetPolicy(
        exceptions=(
            BudgetException(
                id="capacity",
                command=("coverage",),
                test="slow",
                category="benchmark",
                reason="Required capacity proof",
                command_seconds=300.0,
                test_seconds=250.0,
            ),
        )
    )
    monkeypatch.setattr(execution_deadline, "load_budget_policy", lambda _root: policy)
    monkeypatch.setattr(execution_deadline.time, "monotonic", lambda: clock[0])
    with command_scope(tmp_path, ["validation"]) as parent:
        clock[0] += 100
        with command_scope(tmp_path, ["coverage"]) as nested:
            assert nested.end == parent.end
            assert nested.evidence()["command_seconds"] == 200
            assert nested.evidence()["declared_command_seconds"] == 300
            assert nested.reserve == min(0.2, nested.effective_seconds / 10)
            frozen = nested.policy.frozen(nested.argv, nested.seconds)
            assert resolve_test_budget(frozen, "slow", "unit")["test_seconds"] == 250
