"""Integration test: the default Phase 4.5 registry routes each runner to its real handler.

``tests/test_phase_4_5_dispatcher.py`` pins the dispatcher contract with fake
handlers injected through ``registry_factory``. This module keeps the only part
those unit tests cannot see: the production registry wiring. Device tooling is
out of scope, so ``detect`` and ``capture_screenshot`` are patched on the real
handler classes and the test asserts that the dispatcher reached that class.
"""

# @spec AC-001: XCUITest dispatch — .specs/features/037-test-multi-runner-integration/spec.md#ac-001
# @spec AC-002: Maestro dispatch — .specs/features/037-test-multi-runner-integration/spec.md#ac-002
# @spec AC-003: Playwright path no regression
#   .specs/features/037-test-multi-runner-integration/spec.md#ac-003
# @spec FR-002: registry routing — .specs/features/037-test-multi-runner-integration/spec.md#fr-002

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from validator.ui_runner_dispatcher import Phase4_5Dispatcher, Surface
from validator.ui_runner_web import UICapabilityResult


@pytest.mark.parametrize(
    ("runner", "handler_path", "platform"),
    [
        ("playwright", "validator.ui_runner_web.WebRunnerHandler", None),
        ("xcuitest", "validator.ui_runner_xcuitest.XCUITestRunnerHandler", "watchos"),
        ("maestro", "validator.ui_runner_maestro.MaestroRunnerHandler", "android"),
    ],
)
def test_default_registry_routes_runner_to_real_handler(
    tmp_path: Path, runner: str, handler_path: str, platform: str | None
) -> None:
    """Each surface runner reaches its production handler and yields an ``ok`` row."""
    feature_dir = tmp_path / ".specs" / "features" / "042"
    feature_dir.mkdir(parents=True)
    surfaces = [Surface(id=f"{runner}-surface", runner=runner, platform=platform)]
    captured: list[tuple[str, str]] = []

    def fake_capture(self: Any, screen: str = "main", **_: Any) -> UICapabilityResult:
        captured.append((type(self).__name__, screen))
        return UICapabilityResult(success=True, output_path=feature_dir / f"{screen}.png")

    with (
        patch(f"{handler_path}.detect", return_value=True),
        patch(f"{handler_path}.capture_screenshot", new=fake_capture),
    ):
        dispatcher = Phase4_5Dispatcher(
            project_dir=tmp_path, feature_dir=feature_dir, surfaces=surfaces
        )
        results = dispatcher.run(["home"])

    handler_name = handler_path.rsplit(".", 1)[1]
    assert captured == [(handler_name, "home")]
    assert [(r.runner, r.screen, r.status) for r in results] == [(runner, "home", "ok")]
