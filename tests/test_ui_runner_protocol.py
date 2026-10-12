"""Verify the production runner registry only routes to RunnerHandler-conformant handlers."""

# @spec FR-002: Runner registry uniform handler API — .specs/features/037-test-multi-runner-integration/spec.md#fr-002  # noqa: E501

from __future__ import annotations

import inspect
from collections.abc import Callable
from pathlib import Path

import pytest

from validator.runner_dispatcher_impl import _resolve_registry
from validator.ui_runner_maestro import MaestroRunnerHandler
from validator.ui_runner_protocol import RunnerHandler
from validator.ui_runner_tauri import TauriRunnerHandler
from validator.ui_runner_web import WebRunnerHandler
from validator.ui_runner_xcuitest import XCUITestRunnerHandler

# The registry casts each class to RunnerHandler, so static typing cannot catch drift here.
EXPECTED_ROUTES: dict[str, Callable[[Path], object]] = {
    "playwright": WebRunnerHandler,
    "xcuitest": XCUITestRunnerHandler,
    "maestro": MaestroRunnerHandler,
    "tauri": TauriRunnerHandler,
}


def test_registry_routes_each_runner_to_its_handler() -> None:
    assert _resolve_registry() == EXPECTED_ROUTES


@pytest.mark.parametrize("runner", sorted(EXPECTED_ROUTES))
def test_registered_handler_accepts_the_dispatcher_calls(tmp_path: Path, runner: str) -> None:
    assert _resolve_registry()[runner] is EXPECTED_ROUTES[runner]
    handler = EXPECTED_ROUTES[runner](tmp_path)
    assert isinstance(handler, RunnerHandler)
    assert handler.project_dir == tmp_path
    # dispatcher_core calls capture_screenshot(screen, **runnerConfig) and compare_baseline.
    inspect.signature(handler.capture_screenshot).bind("home")
    inspect.signature(handler.compare_baseline).bind("baseline.png", "shot.png", threshold=0.1)
