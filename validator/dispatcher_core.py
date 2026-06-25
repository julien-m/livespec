"""Focused dispatch helpers for Phase 4.5 UI surfaces."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from validator.runner_dispatcher_impl import Surface, VisualPhaseResult
from validator.ui_runner_protocol import RunnerHandler, UICapabilityResult

logger = logging.getLogger("validator.ui_runner_dispatcher")


def dispatch_surface(
    project_dir: Path,
    surface: Surface,
    screens: list[str],
    registry: dict[str, type[RunnerHandler]],
) -> list[VisualPhaseResult]:
    """Dispatch one surface to the matching runner handler."""
    handler_cls = registry.get(surface.runner)
    if handler_cls is None:
        return [_unknown_runner(surface)]
    handler = _build_handler(project_dir, surface, handler_cls)
    if not handler.detect():
        return [_blocked_preflight(surface, handler)]
    return _capture_surface_screens(surface, screens or [""], handler)


def _unknown_runner(surface: Surface) -> VisualPhaseResult:
    """Return the skipped row for an unsupported runner."""
    logger.info("Skipping surface %s: runner %s is not handled", surface.id, surface.runner)
    return VisualPhaseResult(
        surface_id=surface.id,
        runner=surface.runner,
        screen="",
        status="skipped",
        metadata={"reason": "unknown_runner"},
    )


def _build_handler(
    project_dir: Path,
    surface: Surface,
    handler_cls: type[RunnerHandler],
) -> RunnerHandler:
    """Instantiate a runner handler for a project-relative surface path."""
    handler_factory: Any = handler_cls
    return handler_factory((project_dir / surface.path).resolve())


def _blocked_preflight(surface: Surface, handler: RunnerHandler) -> VisualPhaseResult:
    """Return the blocked row for a failed handler preflight."""
    message = handler.preflight_message() or f"{surface.runner} preflight failed"
    logger.error("BLOCKED at step preflight - tooling_missing - %s", message)
    return VisualPhaseResult(
        surface_id=surface.id,
        runner=surface.runner,
        screen="",
        status="blocked",
        error=message,
    )


def _capture_surface_screens(
    surface: Surface,
    target_screens: list[str],
    handler: RunnerHandler,
) -> list[VisualPhaseResult]:
    """Capture all requested screens for one preflight-passing surface."""
    capture_kwargs = _runner_config_to_kwargs(surface)
    shared = _shared_native_outcomes(surface, target_screens, handler, capture_kwargs)
    if isinstance(shared, list):
        return shared
    return [
        _capture_one_screen(surface, screen, handler, capture_kwargs, shared)
        for screen in target_screens
    ]


def _shared_native_outcomes(
    surface: Surface,
    target_screens: list[str],
    handler: RunnerHandler,
    capture_kwargs: dict[str, Any],
) -> dict[str, UICapabilityResult] | list[VisualPhaseResult]:
    """Run native multi-screen handlers once when they emit all attachments."""
    if surface.runner not in ("xcuitest", "maestro") or len(target_screens) <= 1:
        return {}
    try:
        shared_outcome = handler.capture_screenshot(target_screens[0], **capture_kwargs)
    except Exception as exc:
        logger.error("BLOCKED at step phase_4.5 - runtime_error - %s: %s", surface.runner, exc)
        return [_error_row(surface, screen, exc) for screen in target_screens]
    return {screen: shared_outcome for screen in target_screens}


def _capture_one_screen(
    surface: Surface,
    screen: str,
    handler: RunnerHandler,
    capture_kwargs: dict[str, Any],
    cached_outcomes: dict[str, UICapabilityResult],
) -> VisualPhaseResult:
    """Capture one screen and normalize the runner outcome."""
    if screen in cached_outcomes:
        outcome = cached_outcomes[screen]
    else:
        try:
            outcome = handler.capture_screenshot(screen, **capture_kwargs)
        except Exception as exc:
            logger.error("BLOCKED at step phase_4.5 - runtime_error - %s: %s", surface.runner, exc)
            return _error_row(surface, screen, exc)
    return _result_row(surface, screen, outcome)


def _error_row(surface: Surface, screen: str, exc: Exception) -> VisualPhaseResult:
    """Return an error row for a runner exception."""
    return VisualPhaseResult(
        surface_id=surface.id,
        runner=surface.runner,
        screen=screen,
        status="error",
        error=str(exc),
    )


def _result_row(surface: Surface, screen: str, outcome: UICapabilityResult) -> VisualPhaseResult:
    """Map one runner outcome to a visual phase result row."""
    status, error = _status_and_error(surface, outcome)
    return VisualPhaseResult(
        surface_id=surface.id,
        runner=surface.runner,
        screen=screen,
        status=status,
        baseline_path=outcome.output_path,
        error=error,
        metadata=outcome.metadata,
    )


def _status_and_error(surface: Surface, outcome: UICapabilityResult) -> tuple[str, str | None]:
    """Derive dispatcher status while preserving the empty-attachment guard."""
    exported_paths = _exported_paths(outcome)
    cached = bool(outcome.metadata.get("cached")) if outcome.metadata else False
    if (
        outcome.success
        and outcome.output_path is None
        and surface.runner == "xcuitest"
        and not exported_paths
        and not cached
    ):
        return "blocked", _empty_attachment_error()
    return ("ok" if outcome.success else "fail"), outcome.error


def _exported_paths(outcome: UICapabilityResult) -> list[Any]:
    """Return exported path metadata as a list."""
    exported_paths_raw: Any = outcome.metadata.get("exported_paths", []) if outcome.metadata else []
    return exported_paths_raw if isinstance(exported_paths_raw, list) else []


def _empty_attachment_error() -> str:
    """Return the actionable diagnostic for empty XCUITest attachments."""
    return (
        "xcodebuild test ran but produced zero screenshot attachments. Wire your "
        "UITests target to capture XCUIScreen.main.screenshot() and "
        "add(XCTAttachment) per screen identifier (lifetime = .keepAlways). "
        "Reference: livespec/ui-runners/xcuitest-template/LSSampleUITests.swift "
        "in the LiveSpec install, or run `livespec ui-runner scaffold --target ios`."
    )


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
        "outputPath": "output_path",
        "output_path": "output_path",
        "featureSlug": "feature_slug",
        "feature_slug": "feature_slug",
        "runId": "run_id",
        "run_id": "run_id",
    },
    "tauri": {
        "outputPath": "output_path",
        "output_path": "output_path",
        "featureSlug": "feature_slug",
        "feature_slug": "feature_slug",
        "runId": "run_id",
        "run_id": "run_id",
    },
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
    """Translate surface.runner_config into capture_screenshot kwargs."""
    mapping = _RUNNER_CONFIG_KEYS.get(surface.runner, {})
    kwargs: dict[str, Any] = {}
    for source_key, target_key in mapping.items():
        if source_key in surface.runner_config:
            kwargs[target_key] = surface.runner_config[source_key]
    if "platform" not in kwargs and surface.platform is not None and "platform" in mapping.values():
        kwargs["platform"] = surface.platform
    return kwargs
