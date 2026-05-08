"""Verify each concrete handler conforms to the RunnerHandler Protocol."""

# @spec FR-002: Runner registry uniform handler API — .specs/features/037-test-multi-runner-integration/spec.md#fr-002  # noqa: E501

from __future__ import annotations

from pathlib import Path

from validator.ui_runner_maestro import MaestroRunnerHandler
from validator.ui_runner_protocol import RunnerHandler
from validator.ui_runner_web import WebRunnerHandler
from validator.ui_runner_xcuitest import XCUITestRunnerHandler


def test_web_handler_conforms(tmp_path: Path) -> None:
    handler = WebRunnerHandler(tmp_path)
    assert isinstance(handler, RunnerHandler)


def test_xcuitest_handler_conforms(tmp_path: Path) -> None:
    handler = XCUITestRunnerHandler(tmp_path)
    assert isinstance(handler, RunnerHandler)


def test_maestro_handler_conforms(tmp_path: Path) -> None:
    handler = MaestroRunnerHandler(tmp_path)
    assert isinstance(handler, RunnerHandler)
