"""Tauri / Rust UI runner — in-scope per Manager override (visual-gate-fix cycle).

# @spec FR-200: Tauri runner module + capability detection — feature TBD
# @spec FR-201: Runtime path guard wired before every capture — feature TBD

The runner is intentionally a thin shim around ``tauri-driver`` (the WebDriver
proxy for Tauri webviews). It exposes the same surface as the existing
Playwright / XCUITest / Maestro handlers so the dispatcher and visual gate can
treat all four uniformly.

Runtime contract:
* ``detect()`` returns True only when **both** a Tauri app is found in the
  project (``src-tauri/Cargo.toml``) **and** ``tauri-driver`` is on ``PATH``.
* ``capture_screenshot()`` always runs the design-screens guard before
  delegating to the WebDriver layer. When the host capability is missing it
  returns a ``UICapabilityResult`` carrying the structured
  ``capability_reason`` so callers can surface ``EXIT_CAPABILITY_UNSUPPORTED``.
* The module is import-safe on Linux/CI (no Tauri binary loaded at import).

The implementation deliberately does not exec a real ``tauri-driver`` here;
unit tests inject ``capture_fn`` to exercise the surface deterministically.
The integration path is wired but left as a no-op-on-error so a missing
external binary surfaces as a clean diagnostic instead of a crash.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from validator.ui_runner_protocol import (
    RuntimeOutputMisplacedError,
    assert_output_not_in_design_screens,
)
from validator.ui_runner_web import UICapabilityResult

TauriCapability = Literal["available", "tauri_app_missing", "tauri_driver_missing"]
DEFAULT_TIMEOUT_SECONDS = 300
TAURI_APP_MARKER = Path("src-tauri") / "Cargo.toml"
TAURI_DRIVER_BIN = "tauri-driver"


@dataclass(frozen=True)
class TauriCapabilityStatus:
    """Result of :meth:`TauriRunnerHandler.detect_capability`."""

    state: TauriCapability
    app_path: Path | None
    driver_path: str | None
    reason: str

    @property
    def available(self) -> bool:
        return self.state == "available"


@dataclass
class TauriRunnerHandler:
    """Tauri / Rust UI runner handler.

    The handler matches the ``RunnerHandler`` protocol used by the dispatcher
    (``detect``, ``preflight_message``, ``capture_screenshot``, ``run_flow``,
    ``compare_baseline``). Capture delegation is injected via
    ``capture_fn`` to keep the unit tests hermetic; production wiring would
    replace it with a real ``tauri-driver`` WebDriver session.
    """

    project_dir: Path
    capture_fn: Callable[[str, Path], bool] | None = None

    def __post_init__(self) -> None:
        self.project_dir = Path(self.project_dir).resolve()

    # ------------------------------------------------------------------
    # Capability detection
    # ------------------------------------------------------------------

    def detect_capability(self) -> TauriCapabilityStatus:
        """Inspect host + project for a usable Tauri runner."""
        app_marker = self.project_dir / TAURI_APP_MARKER
        if not app_marker.exists():
            return TauriCapabilityStatus(
                state="tauri_app_missing",
                app_path=None,
                driver_path=None,
                reason=(
                    f"No Tauri app detected — expected {TAURI_APP_MARKER} "
                    f"under {self.project_dir}."
                ),
            )
        driver = shutil.which(TAURI_DRIVER_BIN)
        if driver is None:
            return TauriCapabilityStatus(
                state="tauri_driver_missing",
                app_path=app_marker,
                driver_path=None,
                reason=(
                    f"{TAURI_DRIVER_BIN!r} not found on PATH. Install via "
                    "`cargo install tauri-driver` or its platform equivalent."
                ),
            )
        return TauriCapabilityStatus(
            state="available",
            app_path=app_marker,
            driver_path=driver,
            reason="ok",
        )

    def detect(self) -> bool:
        """Return True when the host can run the Tauri capture flow."""
        return self.detect_capability().available

    def preflight_message(self) -> str:
        """Return an actionable diagnostic when :meth:`detect` is False."""
        return self.detect_capability().reason

    # ------------------------------------------------------------------
    # Capture surface
    # ------------------------------------------------------------------

    def capture_screenshot(
        self,
        screen: str = "main",
        output_path: Path | None = None,
        feature_slug: str | None = None,
        run_id: str | None = None,
        **_unused: Any,
    ) -> UICapabilityResult:
        """Capture one screen via ``tauri-driver``.

        Output-path contract (mirrors the web runner):
          * Explicit ``output_path`` → guard runs.
          * Otherwise ``feature_slug`` + ``run_id`` → canonical
            ``.specs/features/<slug>/run/<run_id>/tauri/<screen>.png``.
          * No context supplied → BLOCKED with
            ``guard='missing_output_context'`` (we refuse to silently dump
            into ``.specs/_runs/tauri`` because that hides feature drift).

        When ``capture_fn`` is not provided, the runner returns
        ``capability_state='no_capture_implementation'`` so the CLI mapper
        translates it into ``EXIT_CAPABILITY_UNSUPPORTED`` instead of
        producing a phantom PASS. The pre-fix ``_noop_capture_fn`` default
        is forbidden in production paths.
        """
        if output_path is None:
            if feature_slug and run_id:
                output_path = (
                    self.project_dir
                    / ".specs"
                    / "features"
                    / feature_slug
                    / "run"
                    / run_id
                    / "tauri"
                    / f"{screen}.png"
                )
            else:
                return UICapabilityResult(
                    success=False,
                    error=(
                        "Tauri runner refuses to default to .specs/_runs/tauri/ "
                        "(C6 strict). Provide output_path, or feature_slug+run_id "
                        "to derive .specs/features/<slug>/run/<run_id>/tauri/."
                    ),
                    metadata={
                        "guard": "missing_output_context",
                        "target": "tauri",
                    },
                )
        try:
            assert_output_not_in_design_screens(output_path)
        except RuntimeOutputMisplacedError as exc:
            return UICapabilityResult(
                success=False,
                error=str(exc),
                metadata={"guard": "runtime_under_design_screens"},
            )

        capability = self.detect_capability()
        if not capability.available:
            return UICapabilityResult(
                success=False,
                error=capability.reason,
                metadata={
                    "capability_state": capability.state,
                    "capability_reason": capability.reason,
                    "target": "tauri",
                },
            )

        if self.capture_fn is None:
            # No real WebDriver wiring + tauri-driver present is still
            # CAPABILITY_UNSUPPORTED: we will not emit a fake PASS via a
            # _noop_capture_fn. Callers wire a real capture_fn in production.
            return UICapabilityResult(
                success=False,
                error=(
                    "Tauri capture implementation is not wired. Inject a "
                    "capture_fn(screen, output_path) -> bool that drives "
                    "`tauri-driver`. The runner refuses to silently no-op."
                ),
                metadata={
                    "capability_state": "no_capture_implementation",
                    "capability_reason": "missing_capture_fn",
                    "target": "tauri",
                },
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            ok = self.capture_fn(screen, output_path)
        except Exception as exc:  # pragma: no cover - defensive boundary
            return UICapabilityResult(
                success=False,
                error=f"Tauri capture failed: {exc}",
                metadata={"target": "tauri", "screen": screen},
            )
        return UICapabilityResult(
            success=ok,
            output_path=output_path if ok else None,
            metadata={"target": "tauri", "screen": screen},
        )

    # ------------------------------------------------------------------
    # Flow / compare surface
    # ------------------------------------------------------------------

    def run_flow(self, **kwargs: Any) -> UICapabilityResult:
        """Run the default Tauri capture flow over a single screen.

        Forwards ``output_path`` / ``feature_slug`` / ``run_id`` from the
        dispatcher so canonical run-path threading is honoured (otherwise
        the flow silently drops the canonical destination and falls back
        to the missing_output_context guard).
        """
        screen = str(kwargs.get("screen", "main"))
        raw_output_path = kwargs.get("output_path")
        output_path = (
            Path(raw_output_path) if isinstance(raw_output_path, (str, Path)) else None
        )
        feature_slug = kwargs.get("feature_slug")
        run_id = kwargs.get("run_id")
        return self.capture_screenshot(
            screen,
            output_path=output_path,
            feature_slug=feature_slug if isinstance(feature_slug, str) else None,
            run_id=run_id if isinstance(run_id, str) else None,
        )

    def compare_baseline(
        self,
        baseline: Path | str,
        screenshot: Path | str,
        threshold: float = 0.05,
    ) -> UICapabilityResult:
        """Delegate to the design-alignment hashing helper for byte equality.

        The full pixelmatch path is owned by the design-alignment core; this
        helper covers the no-runner-installed case so consumers always get a
        structured outcome.
        """
        baseline_path = Path(baseline)
        screenshot_path = Path(screenshot)
        if not baseline_path.exists() or not screenshot_path.exists():
            return UICapabilityResult(
                success=False,
                error=(
                    "Baseline or screenshot missing — "
                    f"baseline_exists={baseline_path.exists()}, "
                    f"screenshot_exists={screenshot_path.exists()}"
                ),
                metadata={"target": "tauri", "threshold": threshold},
            )
        from validator.registry_links import sha256_of

        match = sha256_of(baseline_path) == sha256_of(screenshot_path)
        return UICapabilityResult(
            success=match,
            output_path=screenshot_path,
            metadata={
                "target": "tauri",
                "threshold": threshold,
                "method": "sha256_eq",
            },
        )


def detect_tauri_runner(project_dir: Path | str) -> bool:
    """Module-level helper mirroring ``detect_xcuitest_runner`` / ``detect_maestro_runner``."""
    return TauriRunnerHandler(Path(project_dir)).detect()


__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "TAURI_APP_MARKER",
    "TAURI_DRIVER_BIN",
    "TauriCapability",
    "TauriCapabilityStatus",
    "TauriRunnerHandler",
    "detect_tauri_runner",
]
