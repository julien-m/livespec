"""Integration test: Phase 4.5 dispatcher preserves Playwright behaviour (no regression).

The dispatcher MUST route `runner: playwright` surfaces to `WebRunnerHandler`
and MUST NOT alter the existing Playwright contract (Feature 010 baselines
keep the same shape).
"""

# @spec AC-003: Playwright path no regression — .specs/features/037-test-multi-runner-integration/spec.md#ac-003  # noqa: E501
# @spec SC-006: Feature 010 zero regression — .specs/features/037-test-multi-runner-integration/spec.md#sc-006  # noqa: E501

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

from validator.ui_runner_dispatcher import Phase4_5Dispatcher, Surface
from validator.ui_runner_web import UICapabilityResult


def test_playwright_dispatch_no_regression(tmp_path: Path) -> None:
    """AC-003: playwright surfaces still route to WebRunnerHandler.capture_screenshot."""
    project = tmp_path / "project"
    project.mkdir()
    (project / "package.json").write_text("{}", encoding="utf-8")
    (project / "playwright.config.ts").write_text("export default {};", encoding="utf-8")
    feature_dir = project / ".specs" / "features" / "042"
    feature_dir.mkdir(parents=True)
    surfaces = [Surface(id="web", runner="playwright")]

    captured: list[str] = []

    def fake_capture(self: Any, screen: str) -> UICapabilityResult:
        captured.append(screen)
        out = project / ".specs" / "design" / "screens" / f"{screen}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"PNG")
        return UICapabilityResult(success=True, output_path=out)

    with (
        patch(
            "validator.ui_runner_web.WebRunnerHandler.detect",
            return_value=True,
        ),
        patch(
            "validator.ui_runner_web.WebRunnerHandler.capture_screenshot",
            new=fake_capture,
        ),
    ):
        dispatcher = Phase4_5Dispatcher(
            project_dir=project,
            feature_dir=feature_dir,
            surfaces=surfaces,
        )
        results = dispatcher.run(["dashboard", "settings"])

    assert captured == ["dashboard", "settings"]
    assert all(r.runner == "playwright" for r in results)
    assert all(r.status == "ok" for r in results)


def test_playwright_legacy_fallback_when_surfaces_yaml_missing(tmp_path: Path) -> None:
    """AC-003: when surfaces.yaml is absent the dispatcher synthesises a playwright surface."""
    project = tmp_path / "project"
    project.mkdir()
    (project / "package.json").write_text("{}", encoding="utf-8")
    (project / "playwright.config.ts").write_text("export default {};", encoding="utf-8")
    feature_dir = project / ".specs" / "features" / "042"
    feature_dir.mkdir(parents=True)

    def fake_capture(self: Any, screen: str) -> UICapabilityResult:
        return UICapabilityResult(success=True, output_path=Path(f"{screen}.png"))

    with (
        patch(
            "validator.ui_runner_web.WebRunnerHandler.detect",
            return_value=True,
        ),
        patch(
            "validator.ui_runner_web.WebRunnerHandler.capture_screenshot",
            new=fake_capture,
        ),
    ):
        dispatcher = Phase4_5Dispatcher(
            project_dir=project,
            feature_dir=feature_dir,
        )
        # No surfaces.yaml on disk → expect a single legacy playwright surface
        assert len(dispatcher.surfaces) == 1
        assert dispatcher.surfaces[0].runner == "playwright"
        results = dispatcher.run(["home"])

    assert results[0].runner == "playwright"
    assert results[0].status == "ok"
