"""Phase 4.5 dispatcher unit tests with in-memory fake handlers.

These tests pin the routing contract: each registered runner key resolves to
its handler, unknown runners are skipped, and detect()=False triggers a
BLOCKED preflight line.
"""

# @spec FR-001: surfaces.yaml iteration — .specs/features/037-test-multi-runner-integration/spec.md#fr-001  # noqa: E501
# @spec FR-002: registry routing — .specs/features/037-test-multi-runner-integration/spec.md#fr-002  # noqa: E501
# @spec FR-003: no Playwright artefacts on native runners — .specs/features/037-test-multi-runner-integration/spec.md#fr-003  # noqa: E501
# @spec FR-011: detect() preflight gate — .specs/features/037-test-multi-runner-integration/spec.md#fr-011  # noqa: E501
# @spec FR-014: aggregated VisualPhaseResult rows — .specs/features/037-test-multi-runner-integration/spec.md#fr-014  # noqa: E501
# @spec FR-015: unknown runner skip — .specs/features/037-test-multi-runner-integration/spec.md#fr-015  # noqa: E501

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, ClassVar

from validator.ui_runner_dispatcher import (
    Phase4_5Dispatcher,
    Surface,
    VisualPhaseResult,
)
from validator.ui_runner_web import UICapabilityResult


class FakeHandler:
    """Programmable in-memory handler for dispatcher tests."""

    last_screen_calls: ClassVar[list[tuple[str, str]]] = []

    def __init__(
        self,
        project_dir: Path | str,
        *,
        name: str = "fake",
        detect_value: bool = True,
        preflight: str = "",
    ) -> None:
        self.project_dir = Path(project_dir)
        self.name = name
        self.detect_value = detect_value
        self.preflight = preflight

    def detect(self) -> bool:
        return self.detect_value

    def preflight_message(self) -> str:
        return self.preflight

    def capture_screenshot(self, screen: str) -> UICapabilityResult:
        FakeHandler.last_screen_calls.append((self.name, screen))
        return UICapabilityResult(
            success=True,
            output_path=self.project_dir / f"{screen}.png",
            metadata={"runner": self.name},
        )

    def run_flow(self) -> UICapabilityResult:  # pragma: no cover - unused
        return UICapabilityResult(success=True)


def _make_handler(name: str, *, detect_value: bool = True, preflight: str = "") -> Any:
    """Return a class-like factory the dispatcher can instantiate per surface."""

    class _Bound(FakeHandler):
        def __init__(self, project_dir: Path | str) -> None:
            super().__init__(
                project_dir,
                name=name,
                detect_value=detect_value,
                preflight=preflight,
            )

    return _Bound


def _build_dispatcher(
    tmp_path: Path,
    surfaces: list[Surface],
    registry: dict[str, Any],
) -> Phase4_5Dispatcher:
    feature_dir = tmp_path / ".specs" / "features" / "test"
    feature_dir.mkdir(parents=True, exist_ok=True)
    return Phase4_5Dispatcher(
        project_dir=tmp_path,
        feature_dir=feature_dir,
        surfaces=surfaces,
        registry_factory=lambda: registry,
    )


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


def test_dispatcher_routes_playwright(tmp_path: Path) -> None:
    FakeHandler.last_screen_calls = []
    surfaces = [Surface(id="web", runner="playwright")]
    registry = {"playwright": _make_handler("playwright")}
    dispatcher = _build_dispatcher(tmp_path, surfaces, registry)
    results = dispatcher.run(["home"])
    assert len(results) == 1
    assert results[0].runner == "playwright"
    assert results[0].status == "ok"
    assert ("playwright", "home") in FakeHandler.last_screen_calls


def test_dispatcher_routes_xcuitest(tmp_path: Path) -> None:
    FakeHandler.last_screen_calls = []
    surfaces = [Surface(id="ios", runner="xcuitest", platform="watchos")]
    registry = {"xcuitest": _make_handler("xcuitest")}
    dispatcher = _build_dispatcher(tmp_path, surfaces, registry)
    results = dispatcher.run(["watch-home"])
    assert results[0].runner == "xcuitest"
    assert results[0].status == "ok"
    assert ("xcuitest", "watch-home") in FakeHandler.last_screen_calls


def test_dispatcher_routes_maestro(tmp_path: Path) -> None:
    FakeHandler.last_screen_calls = []
    surfaces = [Surface(id="android", runner="maestro", platform="android")]
    registry = {"maestro": _make_handler("maestro")}
    dispatcher = _build_dispatcher(tmp_path, surfaces, registry)
    results = dispatcher.run(["home"])
    assert results[0].runner == "maestro"
    assert results[0].status == "ok"
    assert ("maestro", "home") in FakeHandler.last_screen_calls


# ---------------------------------------------------------------------------
# Skip + BLOCKED + mixed
# ---------------------------------------------------------------------------


def test_dispatcher_skips_unknown_runner(
    tmp_path: Path, caplog: Any
) -> None:
    surfaces = [Surface(id="legacy", runner="tauri")]
    registry: dict[str, Any] = {}
    dispatcher = _build_dispatcher(tmp_path, surfaces, registry)
    with caplog.at_level(logging.INFO, logger="validator.ui_runner_dispatcher"):
        results = dispatcher.run(["home"])
    assert results[0].status == "skipped"
    assert any(
        "Skipping surface legacy: runner tauri is not handled" in rec.getMessage()
        for rec in caplog.records
    )


def test_dispatcher_blocked_when_detect_returns_false(
    tmp_path: Path, caplog: Any
) -> None:
    surfaces = [Surface(id="ios", runner="xcuitest")]
    registry = {
        "xcuitest": _make_handler(
            "xcuitest", detect_value=False, preflight="missing tooling"
        )
    }
    dispatcher = _build_dispatcher(tmp_path, surfaces, registry)
    with caplog.at_level(logging.ERROR, logger="validator.ui_runner_dispatcher"):
        results = dispatcher.run(["home"])
    assert results[0].status == "blocked"
    assert results[0].error == "missing tooling"
    blocked_lines = [
        rec.getMessage()
        for rec in caplog.records
        if "BLOCKED at step preflight - tooling_missing" in rec.getMessage()
    ]
    assert blocked_lines, "Expected BLOCKED line in logs"
    assert "missing tooling" in blocked_lines[0]


def test_no_playwright_artifacts_for_native_runners(tmp_path: Path) -> None:
    """Native dispatch path must NOT produce docker-compose.visual.yml."""
    FakeHandler.last_screen_calls = []
    surfaces = [Surface(id="ios", runner="xcuitest")]
    registry = {"xcuitest": _make_handler("xcuitest")}
    dispatcher = _build_dispatcher(tmp_path, surfaces, registry)
    dispatcher.run(["home"])
    assert not (tmp_path / "docker-compose.visual.yml").exists()
    assert not list(tmp_path.glob("**/toHaveScreenshot*"))


def test_mixed_surfaces_iterate_independently(tmp_path: Path) -> None:
    """Mixed playwright + xcuitest surfaces yield independent rows."""
    FakeHandler.last_screen_calls = []
    surfaces = [
        Surface(id="web", runner="playwright"),
        Surface(id="ios", runner="xcuitest"),
    ]
    registry = {
        "playwright": _make_handler("playwright"),
        "xcuitest": _make_handler("xcuitest"),
    }
    dispatcher = _build_dispatcher(tmp_path, surfaces, registry)
    results = dispatcher.run(["home"])
    assert len(results) == 2
    runners = {r.runner for r in results}
    assert runners == {"playwright", "xcuitest"}


def test_mixed_surfaces_iterate_in_stable_order(tmp_path: Path) -> None:
    """Surface id order is primary; runner priority only breaks same-id ties."""
    FakeHandler.last_screen_calls = []
    surfaces = [
        Surface(id="z", runner="maestro"),
        Surface(id="a", runner="xcuitest"),
        Surface(id="m", runner="playwright"),
    ]
    registry = {
        "maestro": _make_handler("maestro"),
        "xcuitest": _make_handler("xcuitest"),
        "playwright": _make_handler("playwright"),
    }
    feature_dir = tmp_path / ".specs" / "features" / "x"
    feature_dir.mkdir(parents=True, exist_ok=True)
    dispatcher = Phase4_5Dispatcher(
        project_dir=tmp_path,
        feature_dir=feature_dir,
        surfaces=surfaces,
        registry_factory=lambda: registry,
    )
    results = dispatcher.run(["home"])
    assert [r.surface_id for r in results] == ["a", "m", "z"]
    assert [r.runner for r in results] == ["xcuitest", "playwright", "maestro"]


# ---------------------------------------------------------------------------
# Surfaces loader
# ---------------------------------------------------------------------------


def test_load_surfaces_from_yaml(tmp_path: Path) -> None:
    specs = tmp_path / ".specs"
    specs.mkdir()
    (specs / "surfaces.yaml").write_text(
        """
surfaces:
  - id: web
    runner: playwright
    path: .
    testDir: tests/e2e
  - id: ios
    runner: xcuitest
    platform: watchos
    path: ./apps/ios
    testDir: apps/ios/AppWatchTests
""",
        encoding="utf-8",
    )
    feature_dir = specs / "features" / "test"
    feature_dir.mkdir(parents=True)
    dispatcher = Phase4_5Dispatcher(
        project_dir=tmp_path,
        feature_dir=feature_dir,
        registry_factory=lambda: {},
    )
    runners = [s.runner for s in dispatcher.surfaces]
    assert runners == ["xcuitest", "playwright"]
    assert dispatcher.surfaces[0].platform == "watchos"
    assert dispatcher.surfaces[0].test_dir == "apps/ios/AppWatchTests"


def test_legacy_fallback_when_yaml_missing(tmp_path: Path) -> None:
    feature_dir = tmp_path / ".specs" / "features" / "test"
    feature_dir.mkdir(parents=True)
    dispatcher = Phase4_5Dispatcher(
        project_dir=tmp_path,
        feature_dir=feature_dir,
        registry_factory=lambda: {},
    )
    assert len(dispatcher.surfaces) == 1
    assert dispatcher.surfaces[0].runner == "playwright"
    assert dispatcher.surfaces[0].id == "default"


# ---------------------------------------------------------------------------
# Result data shape
# ---------------------------------------------------------------------------


def test_visual_phase_result_records_baseline_path(tmp_path: Path) -> None:
    FakeHandler.last_screen_calls = []
    surfaces = [Surface(id="web", runner="playwright")]
    registry = {"playwright": _make_handler("playwright")}
    dispatcher = _build_dispatcher(tmp_path, surfaces, registry)
    results = dispatcher.run(["home"])
    assert isinstance(results[0], VisualPhaseResult)
    assert results[0].baseline_path == tmp_path / "home.png"
