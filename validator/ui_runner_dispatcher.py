"""Phase 4.5 runner-aware dispatcher (Feature 037).

Reads `.specs/surfaces.yaml`, iterates each surface in stable order, resolves a
concrete `RunnerHandler` via the registry, runs the `detect()` preflight gate,
and invokes `capture_screenshot()` per screen. Native runner failures emit
`BLOCKED at step preflight - tooling_missing - ...` lines; unknown runners are
skipped with an informational log entry.
"""

# @spec FR-001: Phase 4.5 reads surfaces.yaml + iterates — .specs/features/037-test-multi-runner-integration/spec.md#fr-001  # noqa: E501
# @spec FR-002: Runner registry maps runner→handler — .specs/features/037-test-multi-runner-integration/spec.md#fr-002  # noqa: E501
# @spec FR-003: No Playwright artefacts for non-playwright runners — .specs/features/037-test-multi-runner-integration/spec.md#fr-003  # noqa: E501
# @spec FR-011: detect() gate + preflight_message — .specs/features/037-test-multi-runner-integration/spec.md#fr-011  # noqa: E501
# @spec FR-014: VisualPhaseResult aggregation — .specs/features/037-test-multi-runner-integration/spec.md#fr-014  # noqa: E501
# @spec FR-015: Skip unknown/manual runners — .specs/features/037-test-multi-runner-integration/spec.md#fr-015  # noqa: E501

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]

from validator.ui_runner_protocol import RunnerHandler, UICapabilityResult

logger = logging.getLogger(__name__)

# Runner priority used to break ties when surface ids collide; keeps Playwright
# first so mixed-project reports preserve pre-refactor ordering.
_RUNNER_PRIORITY: dict[str, int] = {
    "playwright": 0,
    "xcuitest": 1,
    "maestro": 2,
    "tauri": 3,
}


@dataclass(frozen=True)
class Surface:
    """One row read from `.specs/surfaces.yaml`."""

    id: str
    runner: str
    path: str = "."
    test_dir: str = "tests/e2e"
    platform: str | None = None
    kind: str | None = None
    runner_config: dict[str, Any] = field(default_factory=lambda: cast(dict[str, Any], {}))

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Surface:
        # runnerConfig accepts either a structured map (preferred for native
        # runners: scheme/project/destination/appId/flowsDir/...) or a legacy
        # string (Playwright config path). Strings are coerced to {"_path": value}
        # so the dispatcher always sees a dict — handlers that need the legacy
        # path read it via runner_config["_path"].
        raw_config: Any = raw.get("runnerConfig", {}) or {}
        if isinstance(raw_config, str):
            normalized_config: dict[str, Any] = {"_path": raw_config}
        elif isinstance(raw_config, dict):
            normalized_config = cast(dict[str, Any], raw_config)
        else:
            normalized_config = {}
        return cls(
            id=str(raw.get("id", "")),
            runner=str(raw.get("runner", "")).lower(),
            path=str(raw.get("path", ".")),
            test_dir=str(raw.get("testDir", raw.get("test_dir", "tests/e2e"))),
            platform=raw.get("platform"),
            kind=raw.get("kind"),
            runner_config=normalized_config,
        )


@dataclass
class VisualPhaseResult:
    """Single row in the Phase 5 `Visual Baselines (per surface)` table."""

    surface_id: str
    runner: str
    screen: str
    status: str
    baseline_path: Path | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=lambda: cast(dict[str, Any], {}))


def _resolve_registry() -> dict[str, type[RunnerHandler]]:
    """Lazy-import handlers so platform-specific code stays cold on Linux CI."""
    from validator.ui_runner_maestro import MaestroRunnerHandler
    from validator.ui_runner_tauri import TauriRunnerHandler
    from validator.ui_runner_web import WebRunnerHandler
    from validator.ui_runner_xcuitest import XCUITestRunnerHandler

    return {
        "playwright": cast(type[RunnerHandler], WebRunnerHandler),
        "xcuitest": cast(type[RunnerHandler], XCUITestRunnerHandler),
        "maestro": cast(type[RunnerHandler], MaestroRunnerHandler),
        "tauri": cast(type[RunnerHandler], TauriRunnerHandler),
    }


# Map surfaces.yaml runnerConfig keys to handler.capture_screenshot kwargs.
# Centralised so adding a new runner key is a one-line change instead of
# touching every dispatcher call site.
_RUNNER_CONFIG_KEYS: dict[str, dict[str, str]] = {
    "xcuitest": {
        "scheme": "test_scheme",
        "destination": "destination",
        "project": "project",
        "workspace": "workspace",
        "platform": "platform",
        "launchArguments": "launch_arguments",
        "launch_arguments": "launch_arguments",
        "onlyTesting": "only_testing",
        "only_testing": "only_testing",
        # Visual-gate canonical run path inputs.
        "outputPath": "output_path",
        "output_path": "output_path",
        "featureSlug": "feature_slug",
        "feature_slug": "feature_slug",
        "runId": "run_id",
        "run_id": "run_id",
    },
    "maestro": {
        "avdName": "avd_name",
        "avd_name": "avd_name",
        "platform": "platform",
        "failFast": "fail_fast",
        "fail_fast": "fail_fast",
        "timeout": "timeout",
        # Visual-gate canonical run path inputs.
        "outputPath": "output_path",
        "output_path": "output_path",
        "featureSlug": "feature_slug",
        "feature_slug": "feature_slug",
        "runId": "run_id",
        "run_id": "run_id",
    },
    # Tauri handler accepts output_path overrides plus an optional capture_fn
    # injection (used by tests / programmatic callers).
    "tauri": {
        "outputPath": "output_path",
        "output_path": "output_path",
        "featureSlug": "feature_slug",
        "feature_slug": "feature_slug",
        "runId": "run_id",
        "run_id": "run_id",
    },
    # Playwright handler (C6 strict): accept canonical run-path inputs +
    # explicit legacy opt-in. The handler refuses to default to
    # .specs/design/screens/ unless legacyDesignScreens=true is set.
    "playwright": {
        "outputPath": "output_path",
        "output_path": "output_path",
        "featureSlug": "feature_slug",
        "feature_slug": "feature_slug",
        "runId": "run_id",
        "run_id": "run_id",
        "legacyDesignScreens": "legacy_design_screens",
        "legacy_design_screens": "legacy_design_screens",
    },
}


def _runner_config_to_kwargs(surface: Surface) -> dict[str, Any]:
    """Translate surface.runner_config into kwargs for handler.capture_screenshot.

    Unknown keys are dropped silently so a surfaces.yaml carrying extra fields
    (project, comments, future runner extensions) does not crash the dispatcher.

    Falls back to surface-level `platform` when `runnerConfig.platform` is absent —
    legacy v8/v12 manifests declare platform at the surface root, not under runnerConfig.
    """
    mapping = _RUNNER_CONFIG_KEYS.get(surface.runner, {})
    kwargs: dict[str, Any] = {}
    for source_key, target_key in mapping.items():
        if source_key in surface.runner_config:
            kwargs[target_key] = surface.runner_config[source_key]
    if (
        "platform" not in kwargs
        and surface.platform is not None
        and "platform" in mapping.values()
    ):
        kwargs["platform"] = surface.platform
    return kwargs


def _stable_sort_key(surface: Surface) -> tuple[str, int]:
    # Surface ids drive the primary order so mixed-surface reports stay stable
    # even when new runner types are added; runner priority only breaks ties.
    return (surface.id, _RUNNER_PRIORITY.get(surface.runner, 99))


@dataclass
class Phase4_5Dispatcher:
    """Runner-aware dispatcher for Phase 4.5."""

    project_dir: Path
    feature_dir: Path
    surfaces: list[Surface] = field(default_factory=lambda: cast(list[Surface], []))
    registry_factory: Callable[[], dict[str, type[RunnerHandler]]] | None = None

    def __post_init__(self) -> None:
        self.project_dir = Path(self.project_dir).resolve()
        self.feature_dir = Path(self.feature_dir).resolve()
        if not self.surfaces:
            self.surfaces = self._load_surfaces()
        else:
            self.surfaces = sorted(self.surfaces, key=_stable_sort_key)

    # ------------------------------------------------------------------
    # Surfaces loading
    # ------------------------------------------------------------------

    def _load_surfaces(self) -> list[Surface]:
        """Load surfaces.yaml or fall back to a synthetic Playwright surface."""
        surfaces_path = self.project_dir / ".specs" / "surfaces.yaml"
        if not surfaces_path.exists():
            logger.info(
                "INFO: surfaces.yaml missing — using legacy single playwright surface"
            )
            return [self._legacy_single_surface()]
        try:
            parsed: Any = yaml.safe_load(surfaces_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:  # pragma: no cover - defensive
            logger.warning("WARNING: surfaces.yaml is invalid (%s) — using legacy fallback", exc)
            return [self._legacy_single_surface()]
        raw: dict[str, Any] = (
            cast(dict[str, Any], parsed) if isinstance(parsed, dict) else {}
        )
        entries_raw = raw.get("surfaces", [])
        entries = cast(list[Any], entries_raw) if isinstance(entries_raw, list) else []
        loaded: list[Surface] = []
        for entry in entries:
            if isinstance(entry, dict):
                loaded.append(Surface.from_dict(cast(dict[str, Any], entry)))
        if not loaded:
            return [self._legacy_single_surface()]
        return sorted(loaded, key=_stable_sort_key)

    def _legacy_single_surface(self) -> Surface:
        return Surface(
            id="default",
            runner="playwright",
            path=".",
            test_dir="tests/e2e",
        )

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def _registry(self) -> dict[str, type[RunnerHandler]]:
        if self.registry_factory is not None:
            return self.registry_factory()
        return _resolve_registry()

    def run(self, screens: list[str]) -> list[VisualPhaseResult]:
        """Execute Phase 4.5 across every surface and return aggregated results."""
        all_results: list[VisualPhaseResult] = []
        registry = self._registry()
        for surface in self.surfaces:
            all_results.extend(self._dispatch(surface, screens, registry))
        return all_results

    def _dispatch(
        self,
        surface: Surface,
        screens: list[str],
        registry: dict[str, type[RunnerHandler]],
    ) -> list[VisualPhaseResult]:
        handler_cls = registry.get(surface.runner)
        if handler_cls is None:
            logger.info(
                "Skipping surface %s: runner %s is not handled",
                surface.id,
                surface.runner,
            )
            return [
                VisualPhaseResult(
                    surface_id=surface.id,
                    runner=surface.runner,
                    screen="",
                    status="skipped",
                    metadata={"reason": "unknown_runner"},
                )
            ]

        surface_path = (self.project_dir / surface.path).resolve()
        # Concrete handlers all accept a project_dir constructor argument; the
        # Protocol cannot encode this for instantiation, so we call directly.
        handler_factory: Any = handler_cls
        handler: RunnerHandler = handler_factory(surface_path)

        if not handler.detect():
            message = handler.preflight_message() or f"{surface.runner} preflight failed"
            logger.error(
                "BLOCKED at step preflight - tooling_missing - %s", message
            )
            return [
                VisualPhaseResult(
                    surface_id=surface.id,
                    runner=surface.runner,
                    screen="",
                    status="blocked",
                    error=message,
                )
            ]

        # Translate surfaces.yaml runnerConfig keys into capture_screenshot kwargs.
        # This is what wires `runnerConfig.scheme` → xcodebuild `-scheme`, etc.
        capture_kwargs = _runner_config_to_kwargs(surface)

        results: list[VisualPhaseResult] = []
        target_screens = screens or [""]
        # Performance: native runners (xcuitest, maestro) build the test target
        # and run ALL test methods every time `capture_screenshot` is called —
        # i.e. ONE call already produces attachments for every screen. Calling
        # it once per requested screen would mean N x rebuild + N x run with
        # the same outcome. We invoke the handler once and replay the same
        # outcome across the screen list, then let `_parse_xcresult` (already
        # called inside the handler) populate per-screen artefacts.
        if surface.runner in ("xcuitest", "maestro") and len(target_screens) > 1:
            try:
                shared_outcome: UICapabilityResult = handler.capture_screenshot(
                    target_screens[0], **capture_kwargs
                )
            except Exception as exc:  # pragma: no cover
                logger.error(
                    "BLOCKED at step phase_4.5 - runtime_error - %s: %s",
                    surface.runner,
                    exc,
                )
                return [
                    VisualPhaseResult(
                        surface_id=surface.id,
                        runner=surface.runner,
                        screen=s,
                        status="error",
                        error=str(exc),
                    )
                    for s in target_screens
                ]
            outcomes_by_screen = {s: shared_outcome for s in target_screens}
        else:
            outcomes_by_screen = {}

        for screen in target_screens:
            if screen in outcomes_by_screen:
                outcome = outcomes_by_screen[screen]
            else:
                try:
                    outcome = handler.capture_screenshot(screen, **capture_kwargs)
                except Exception as exc:  # pragma: no cover - defensive boundary
                    logger.error(
                        "BLOCKED at step phase_4.5 - runtime_error - %s: %s",
                        surface.runner,
                        exc,
                    )
                    results.append(
                        VisualPhaseResult(
                            surface_id=surface.id,
                            runner=surface.runner,
                            screen=screen,
                            status="error",
                            error=str(exc),
                        )
                    )
                    continue
            # Detect "test target ran but produced zero attachments" — xcodebuild
            # exits 0 but the UITest target didn't add any XCTAttachment.image()
            # calls, so the dispatcher has nothing to compare. Flag this as
            # BLOCKED with actionable guidance instead of silently passing.
            exported_paths_raw: Any = (
                outcome.metadata.get("exported_paths", []) if outcome.metadata else []
            )
            exported_paths: list[Any] = (
                cast(list[Any], exported_paths_raw)
                if isinstance(exported_paths_raw, list)
                else []
            )
            cached = bool(outcome.metadata.get("cached")) if outcome.metadata else False
            empty_attachments = (
                outcome.success
                and outcome.output_path is None
                and surface.runner == "xcuitest"
                and len(exported_paths) == 0
                and not cached
            )
            if empty_attachments:
                status = "blocked"
                error = (
                    "xcodebuild test ran but produced zero screenshot attachments. "
                    "Wire your UITests target to capture XCUIScreen.main.screenshot() "
                    "and add(XCTAttachment) per screen identifier (lifetime = .keepAlways). "
                    "Reference: livespec/ui-runners/xcuitest-template/LSSampleUITests.swift "
                    "in the LiveSpec install, or run `livespec ui-runner scaffold --target ios`."
                )
            else:
                status = "ok" if outcome.success else "fail"
                error = outcome.error
            results.append(
                VisualPhaseResult(
                    surface_id=surface.id,
                    runner=surface.runner,
                    screen=screen,
                    status=status,
                    baseline_path=outcome.output_path,
                    error=error,
                    metadata=outcome.metadata,
                )
            )
        return results


__all__ = ["Phase4_5Dispatcher", "Surface", "VisualPhaseResult"]
