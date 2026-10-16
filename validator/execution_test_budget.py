"""Stdlib-only immutable child-side individual test budgets."""

# @spec FR-002: Category and complete-test bounds
# — .specs/features/095-test-time-budgets/spec.md#fr-002
from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import cast

_ORIGINAL_STDERR = os.dup(2)


def read_budget() -> dict[str, object] | None:
    """Freeze parent-prepared policy before importing collected tests."""
    raw = os.environ.get("LIVESPEC_TEST_BUDGET")
    return cast("dict[str, object]", json.loads(raw)) if raw else None


def resolve_test_budget(policy: dict[str, object], test: str, category: str) -> dict[str, object]:
    """Resolve an exact exception against the already validated frozen policy."""
    defaults = cast("dict[str, float]", policy["defaults"])
    result: dict[str, object] = {
        "scope": test,
        "category": category,
        "test_seconds": defaults[category],
    }
    for exception in cast("list[dict[str, object]]", policy["exceptions"]):
        if exception["test"] == test:
            seconds = cast("float", exception["test_seconds"])
            if seconds > cast("float", policy["command_seconds"]):
                raise ValueError("test exception exceeds enclosing declared command budget")
            result.update(
                test_seconds=seconds,
                category=exception["category"],
                exception_id=exception["id"],
                exception_reason=exception["reason"],
            )
    return result


def hard_timeout(budget: dict[str, object], started: float) -> None:
    """A hung fixture cannot catch or swallow the timeout as a normal test failure."""
    record = {**budget, "elapsed_seconds": time.monotonic() - started, "timed_out": True}
    os.write(_ORIGINAL_STDERR, ("\nLIVESPEC_TEST_TIMEOUT " + json.dumps(record) + "\n").encode())
    os._exit(124)


@contextmanager
def test_watchdog(budget: dict[str, object]) -> Generator[None, None, None]:
    """Cover setup, body and teardown with a hard watchdog owned by the runner."""
    timer = threading.Timer(
        cast("float", budget["test_seconds"]), hard_timeout, (budget, time.monotonic())
    )
    timer.daemon = True
    timer.start()
    try:
        yield
    finally:
        timer.cancel()
