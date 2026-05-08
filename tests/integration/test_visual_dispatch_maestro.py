"""Integration test: Phase 4.5 dispatcher routes an Android surface to Maestro.

Subprocess calls (`adb`, `maestro`) are monkeypatched; the test asserts that
`run_flow` and `capture_screenshot` are invoked in order on the real handler.
"""

# @spec AC-002: Maestro dispatch — .specs/features/037-test-multi-runner-integration/spec.md#ac-002
# @spec FR-002: registry routing — .specs/features/037-test-multi-runner-integration/spec.md#fr-002

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

from validator.ui_runner_dispatcher import Phase4_5Dispatcher, Surface
from validator.ui_runner_web import UICapabilityResult


def test_maestro_dispatch_invokes_capture(tmp_path: Path) -> None:
    """AC-002: dispatcher routes maestro surfaces to MaestroRunnerHandler."""
    project = tmp_path / "project"
    project.mkdir()
    (project / "build.gradle").write_text("// stub", encoding="utf-8")
    (project / "maestro").mkdir()
    (project / "maestro" / "home.yaml").write_text("appId: com.x\n", encoding="utf-8")
    feature_dir = project / ".specs" / "features" / "042"
    feature_dir.mkdir(parents=True)
    surfaces = [Surface(id="android", runner="maestro", platform="android")]

    captured: list[str] = []

    def fake_capture(self: Any, screen: str = "main", **_: Any) -> UICapabilityResult:
        captured.append(screen)
        return UICapabilityResult(success=True, output_path=Path(f"{screen}.png"))

    with (
        patch(
            "validator.ui_runner_maestro.MaestroRunnerHandler.detect",
            return_value=True,
        ),
        patch(
            "validator.ui_runner_maestro.MaestroRunnerHandler.capture_screenshot",
            new=fake_capture,
        ),
    ):
        dispatcher = Phase4_5Dispatcher(
            project_dir=project,
            feature_dir=feature_dir,
            surfaces=surfaces,
        )
        results = dispatcher.run(["home"])

    assert captured == ["home"]
    assert results[0].runner == "maestro"
    assert results[0].status == "ok"


def test_maestro_blocked_when_detect_false(tmp_path: Path) -> None:
    """AC-013: detect()=False on Maestro emits BLOCKED preflight line."""
    project = tmp_path / "project"
    project.mkdir()
    feature_dir = project / ".specs" / "features" / "042"
    feature_dir.mkdir(parents=True)
    surfaces = [Surface(id="android", runner="maestro", platform="android")]

    with (
        patch(
            "validator.ui_runner_maestro.MaestroRunnerHandler.detect",
            return_value=False,
        ),
        patch(
            "validator.ui_runner_maestro.MaestroRunnerHandler.preflight_message",
            return_value="no Android emulator available — start one with 'emulator -avd <name>'",
        ),
    ):
        dispatcher = Phase4_5Dispatcher(
            project_dir=project,
            feature_dir=feature_dir,
            surfaces=surfaces,
        )
        results = dispatcher.run(["home"])

    assert results[0].status == "blocked"
    assert results[0].error is not None
    assert "no Android emulator available" in results[0].error
