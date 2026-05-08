"""Integration test: Phase 4.5 dispatcher routes a watchOS surface to XCUITest.

Drives the dispatcher with a real `XCUITestRunnerHandler` whose external
subprocess calls are monkeypatched, so the test runs on Linux CI.
"""

# @spec AC-001: XCUITest dispatch — .specs/features/037-test-multi-runner-integration/spec.md#ac-001
# @spec FR-002: registry routing — .specs/features/037-test-multi-runner-integration/spec.md#fr-002

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

from validator.ui_runner_dispatcher import Phase4_5Dispatcher, Surface
from validator.ui_runner_web import UICapabilityResult


def test_xcuitest_dispatch_invokes_capture_once_per_screen(tmp_path: Path) -> None:
    """AC-001: dispatcher calls XCUITestRunnerHandler.capture_screenshot once per screen."""
    project = tmp_path / "project"
    project.mkdir()
    (project / "App.xcodeproj").mkdir()
    (project / ".specs" / "features" / "042" / "baselines").mkdir(parents=True)

    feature_dir = project / ".specs" / "features" / "042"
    surfaces = [Surface(id="app-uitests", runner="xcuitest", platform="watchos")]

    captured_calls: list[str] = []

    def fake_capture(self: Any, screen: str = "main", **_: Any) -> UICapabilityResult:
        captured_calls.append(screen)
        out = feature_dir / "baselines" / f"{screen}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"\x89PNG\x00")
        return UICapabilityResult(success=True, output_path=out)

    with (
        patch(
            "validator.ui_runner_xcuitest.XCUITestRunnerHandler.detect",
            return_value=True,
        ),
        patch(
            "validator.ui_runner_xcuitest.XCUITestRunnerHandler.capture_screenshot",
            new=fake_capture,
        ),
    ):
        dispatcher = Phase4_5Dispatcher(
            project_dir=project,
            feature_dir=feature_dir,
            surfaces=surfaces,
        )
        results = dispatcher.run(["watch-home"])

    assert captured_calls == ["watch-home"]
    assert len(results) == 1
    assert results[0].runner == "xcuitest"
    assert results[0].status == "ok"


def test_xcuitest_dispatch_does_not_emit_playwright_artifacts(tmp_path: Path) -> None:
    """AC-004: native dispatch must NOT produce docker-compose.visual.yml."""
    project = tmp_path / "project"
    project.mkdir()
    (project / "App.xcodeproj").mkdir()
    feature_dir = project / ".specs" / "features" / "042"
    feature_dir.mkdir(parents=True)
    surfaces = [Surface(id="app-uitests", runner="xcuitest")]

    def fake_capture(self: Any, screen: str = "main", **_: Any) -> UICapabilityResult:
        return UICapabilityResult(success=True, output_path=None)

    with (
        patch(
            "validator.ui_runner_xcuitest.XCUITestRunnerHandler.detect",
            return_value=True,
        ),
        patch(
            "validator.ui_runner_xcuitest.XCUITestRunnerHandler.capture_screenshot",
            new=fake_capture,
        ),
    ):
        dispatcher = Phase4_5Dispatcher(
            project_dir=project,
            feature_dir=feature_dir,
            surfaces=surfaces,
        )
        dispatcher.run(["home"])

    assert not (project / "docker-compose.visual.yml").exists()
    assert not list(project.rglob("playwright.config.*"))
