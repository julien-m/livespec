# LiveSpec traceability anchors
# @spec(AC-001)
# @spec(AC-002)
# @spec(AC-003)
# @spec(FR-001)
# @spec(FR-006)
# @spec(FR-007)

"""Phase 4.5 runner-aware dispatcher (Feature 037).

Reads `.specs/surfaces.yaml`, iterates each surface in stable order, resolves a
concrete `RunnerHandler` via the registry, runs the `detect()` preflight gate,
and invokes `capture_screenshot()` per screen. Native runner failures emit
`BLOCKED at step preflight - tooling_missing - ...` lines; unknown runners are
skipped with an informational log entry.
"""

# @spec(FR-001)
# @spec(FR-002)
# @spec(FR-003)
# @spec(FR-011)
# @spec(FR-014)
# @spec(FR-015)

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]  # PyYAML is a runtime dependency without stubs.

from validator.ui_runner_protocol import RunnerHandler

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
        """Build a Surface from one surfaces.yaml entry."""
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
            logger.info("INFO: surfaces.yaml missing — using legacy single playwright surface")
            return [self._legacy_single_surface()]
        try:
            parsed: Any = yaml.safe_load(surfaces_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:  # pragma: no cover - defensive
            logger.warning("WARNING: surfaces.yaml is invalid (%s) — using legacy fallback", exc)
            return [self._legacy_single_surface()]
        raw: dict[str, Any] = cast(dict[str, Any], parsed) if isinstance(parsed, dict) else {}
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
        """Dispatch one surface through its registered runner handler."""
        from validator.dispatcher_core import dispatch_surface

        return dispatch_surface(self.project_dir, surface, screens, registry)


__all__ = ["Phase4_5Dispatcher", "Surface", "VisualPhaseResult"]
