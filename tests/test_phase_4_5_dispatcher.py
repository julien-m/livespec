# LiveSpec traceability anchors
# @spec(AC-001)
# @spec(AC-002)
# @spec(AC-003)
# @spec(AC-007)
# @spec(FR-001)
# @spec(FR-006)
# @spec(FR-007)
# @spec(FR-008)

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
    last_capture_kwargs: ClassVar[list[dict[str, Any]]] = []

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

    def capture_screenshot(self, screen: str, **kwargs: Any) -> UICapabilityResult:
        FakeHandler.last_screen_calls.append((self.name, screen))
        FakeHandler.last_capture_kwargs.append(kwargs)
        return UICapabilityResult(
            success=True,
            output_path=self.project_dir / f"{screen}.png",
            metadata={"runner": self.name, "kwargs": kwargs},
        )

    def run_flow(self, **kwargs: Any) -> UICapabilityResult:  # pragma: no cover - unused
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


def test_dispatcher_skips_unknown_runner(tmp_path: Path, caplog: Any) -> None:
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


def test_dispatcher_blocked_when_detect_returns_false(tmp_path: Path, caplog: Any) -> None:
    surfaces = [Surface(id="ios", runner="xcuitest")]
    registry = {
        "xcuitest": _make_handler("xcuitest", detect_value=False, preflight="missing tooling")
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


# ---------------------------------------------------------------------------
# Runner config wiring (Feature 038)
# ---------------------------------------------------------------------------
# @spec FR-001: dispatcher passes runnerConfig kwargs — .specs/features/038-runner-config-wiring/spec.md#fr-001  # noqa: E501


def test_dispatcher_passes_xcuitest_runner_config(tmp_path: Path) -> None:
    """xcuitest surfaces propagate scheme/destination as test_scheme/destination kwargs."""
    FakeHandler.last_capture_kwargs = []
    surfaces = [
        Surface(
            id="ios",
            runner="xcuitest",
            platform="ios",
            runner_config={
                "scheme": "STRAPT",
                "destination": "platform=iOS Simulator,name=iPhone 16",
                "project": "STRAPT.xcodeproj",
            },
        )
    ]
    registry = {"xcuitest": _make_handler("xcuitest")}
    dispatcher = _build_dispatcher(tmp_path, surfaces, registry)
    dispatcher.run(["home"])
    assert len(FakeHandler.last_capture_kwargs) == 1
    kwargs = FakeHandler.last_capture_kwargs[0]
    assert kwargs.get("test_scheme") == "STRAPT"
    assert kwargs.get("destination") == "platform=iOS Simulator,name=iPhone 16"
    assert kwargs.get("project") == "STRAPT.xcodeproj"


def test_dispatcher_passes_maestro_runner_config(tmp_path: Path) -> None:
    """maestro surfaces propagate avdName/platform as kwargs."""
    FakeHandler.last_capture_kwargs = []
    surfaces = [
        Surface(
            id="android",
            runner="maestro",
            platform="android",
            runner_config={
                "avdName": "Pixel_8_API_35",
                "platform": "android",
                "failFast": True,
            },
        )
    ]
    registry = {"maestro": _make_handler("maestro")}
    dispatcher = _build_dispatcher(tmp_path, surfaces, registry)
    dispatcher.run(["home"])
    kwargs = FakeHandler.last_capture_kwargs[0]
    assert kwargs.get("avd_name") == "Pixel_8_API_35"
    assert kwargs.get("platform") == "android"
    assert kwargs.get("fail_fast") is True


def test_dispatcher_drops_unknown_runner_config_keys(tmp_path: Path) -> None:
    """Unknown runnerConfig keys are silently dropped so future fields don't break dispatch."""
    FakeHandler.last_capture_kwargs = []
    surfaces = [
        Surface(
            id="ios",
            runner="xcuitest",
            runner_config={"scheme": "S", "futureKey": "x", "another": 42},
        )
    ]
    registry = {"xcuitest": _make_handler("xcuitest")}
    dispatcher = _build_dispatcher(tmp_path, surfaces, registry)
    dispatcher.run(["home"])
    kwargs = FakeHandler.last_capture_kwargs[0]
    assert kwargs == {"test_scheme": "S"}


def test_surface_from_dict_normalizes_string_runner_config() -> None:
    """Legacy `runnerConfig: <string>` is coerced to {"_path": value}."""
    raw = {
        "id": "web",
        "runner": "playwright",
        "runnerConfig": "apps/web/playwright.config.ts",
    }
    surface = Surface.from_dict(raw)
    assert surface.runner_config == {"_path": "apps/web/playwright.config.ts"}


def test_surface_from_dict_preserves_dict_runner_config() -> None:
    """Structured `runnerConfig: { ... }` reaches the dispatcher untouched."""
    raw = {
        "id": "ios",
        "runner": "xcuitest",
        "runnerConfig": {"scheme": "App", "destination": "platform=iOS Simulator,name=iPhone 16"},
    }
    surface = Surface.from_dict(raw)
    assert surface.runner_config == {
        "scheme": "App",
        "destination": "platform=iOS Simulator,name=iPhone 16",
    }


# ---------------------------------------------------------------------------
# Empty-attachment detection (Strapt regression: xcodebuild exits 0 but
# UITest target produces zero XCTAttachment.image entries).
# ---------------------------------------------------------------------------


class _EmptyAttachmentXcuitestHandler(FakeHandler):
    """Simulates xcodebuild test exit 0 with no PNG attachments produced."""

    def __init__(self, project_dir: Path | str) -> None:
        super().__init__(project_dir, name="xcuitest")

    def capture_screenshot(self, screen: str, **kwargs: Any) -> UICapabilityResult:
        return UICapabilityResult(
            success=True,
            output_path=None,
            metadata={"exit_code": 0, "exported_paths": []},
        )


def test_dispatcher_blocks_when_xcuitest_returns_zero_attachments(tmp_path: Path) -> None:
    """When xcodebuild succeeds but no XCTAttachment is added, dispatcher
    must surface a BLOCKED status pointing to the LSSampleUITests template.
    Otherwise visual diffs would silently no-op (Strapt regression).
    """
    surfaces = [Surface(id="ios", runner="xcuitest")]
    registry = {"xcuitest": _EmptyAttachmentXcuitestHandler}
    dispatcher = _build_dispatcher(tmp_path, surfaces, registry)
    results = dispatcher.run(["home"])
    assert len(results) == 1
    assert results[0].status == "blocked"
    assert results[0].error is not None
    assert "XCTAttachment" in results[0].error
    assert "LSSampleUITests" in results[0].error or "scaffold" in results[0].error
