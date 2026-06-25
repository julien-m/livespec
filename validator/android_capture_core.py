"""Focused Android Maestro screenshot capture helpers."""

from __future__ import annotations

import subprocess
import warnings
from pathlib import Path
from typing import Any

from validator.android_runner_core import (
    _ensure_emulator,
    _maestro_preflight_result,
    find_flows,
    find_maestro_screenshots,
)
from validator.runner_maestro_impl import (
    _NO_FLOWS_ERROR,
    _WEAROS_EXPERIMENTAL_WARNING,
    UICapabilityResult,
)


def capture_screenshot(
    handler: Any,
    screen: str,
    avd_name: str | None,
    platform: str,
    fail_fast: bool,
    timeout: int,
    output_path: Path | None,
    feature_slug: str | None,
    run_id: str | None,
) -> UICapabilityResult:
    """Run Maestro flows and collect screenshots into the canonical output path."""
    output_path = _resolve_capture_output(
        handler.project_dir, screen, output_path, feature_slug, run_id
    )
    blocked = _guard_capture_output(output_path)
    if blocked is not None:
        return blocked
    blocked = _capture_preflight(handler, platform)
    if blocked is not None:
        return blocked
    flows = find_flows(handler.project_dir)
    if not flows:
        return UICapabilityResult(success=False, error=_NO_FLOWS_ERROR)
    serial = _ensure_emulator(handler, avd_name, validate_override=False)
    if isinstance(serial, UICapabilityResult):
        return serial
    if output_path is None:
        return _missing_output_context_result()
    return _capture_flow_screens(handler, flows, serial, fail_fast, timeout, output_path)


def _resolve_capture_output(
    project_dir: Path,
    screen: str,
    output_path: Path | None,
    feature_slug: str | None,
    run_id: str | None,
) -> Path | None:
    """Resolve explicit or canonical Android screenshot output."""
    if output_path is not None:
        return output_path
    if feature_slug and run_id:
        return project_dir / ".specs" / "features" / feature_slug / "run" / run_id / "android"
    return None


def _guard_capture_output(output_path: Path | None) -> UICapabilityResult | None:
    """Reject runtime screenshots that would overwrite design screens."""
    if output_path is None:
        return None
    from validator.ui_runner_protocol import (
        RuntimeOutputMisplacedError,
        assert_output_not_in_design_screens,
    )

    try:
        assert_output_not_in_design_screens(output_path)
    except RuntimeOutputMisplacedError as exc:
        return UICapabilityResult(
            success=False, error=str(exc), metadata={"guard": "runtime_under_design_screens"}
        )
    return None


def _capture_preflight(handler: Any, platform: str) -> UICapabilityResult | None:
    """Return capture blockers before running Maestro."""
    blocked = _maestro_preflight_result(handler)
    if blocked is not None:
        return blocked
    if platform.lower() == "wearos":
        warnings.warn(_WEAROS_EXPERIMENTAL_WARNING, UserWarning, stacklevel=2)
    return None


def _missing_output_context_result() -> UICapabilityResult:
    """Return the C6 strict missing-output guard result."""
    return UICapabilityResult(
        success=False,
        error=(
            "Maestro runner refuses to write into .specs/design/screens/ "
            "by default (C6 strict). Provide output_path or feature_slug+run_id."
        ),
        metadata={"guard": "missing_output_context", "target": "android"},
    )


def _capture_flow_screens(
    handler: Any, flows: list[Path], serial: str, fail_fast: bool, timeout: int, output_path: Path
) -> UICapabilityResult:
    """Run flows, copy Maestro screenshots, and fall back to adb captures."""
    output_dir = output_path.parent if output_path.suffix.lower() == ".png" else output_path
    output_dir.mkdir(parents=True, exist_ok=True)
    screenshots: list[Path] = []
    for flow_path in flows:
        error = _run_capture_flow_process(handler.project_dir, flow_path, timeout)
        if error is not None:
            if fail_fast:
                return UICapabilityResult(success=False, error=error)
            continue
        screenshots.extend(_collect_flow_screenshots(handler, flow_path, serial, output_dir))
    return _capture_screens_result(screenshots, serial, len(flows))


def _run_capture_flow_process(project_dir: Path, flow_path: Path, timeout: int) -> str | None:
    """Run one Maestro capture flow and return an error message on failure."""
    try:
        subprocess.run(
            ["maestro", "test", str(flow_path)],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return f"Failed to execute maestro: {exc}"
    return None


def _collect_flow_screenshots(
    handler: Any, flow_path: Path, serial: str, output_dir: Path
) -> list[Path]:
    """Collect screenshots for one completed Maestro flow."""
    copied = _copy_maestro_screenshots(flow_path, output_dir)
    if copied:
        return copied
    fallback_path = output_dir / f"{flow_path.stem}.png"
    return [fallback_path] if handler._capture_adb_screenshot(serial, fallback_path) else []


def _copy_maestro_screenshots(flow_path: Path, output_dir: Path) -> list[Path]:
    """Copy screenshots from Maestro's home directory for one flow."""
    import shutil

    copied: list[Path] = []
    for src in find_maestro_screenshots(Path.home() / ".maestro" / "tests"):
        dest = output_dir / f"{flow_path.stem}_{src.name}"
        try:
            shutil.copy2(src, dest)
        except OSError:
            continue
        copied.append(dest)
    return copied


def _capture_screens_result(
    screenshots: list[Path], serial: str, total_flows: int
) -> UICapabilityResult:
    """Return aggregate capture metadata."""
    return UICapabilityResult(
        success=True,
        output_path=screenshots[0] if screenshots else None,
        metadata={
            "screenshots": [str(path) for path in screenshots],
            "serial": serial,
            "total_flows": total_flows,
        },
    )


def compare_baseline(
    project_dir: Path, baseline: str, screenshot: str, threshold: float
) -> UICapabilityResult:
    """Compare two PNGs with the project pixelmatch helper."""
    from validator.web_runner_core import compare_pixel_baseline

    result = compare_pixel_baseline(project_dir, baseline, screenshot, threshold)
    return UICapabilityResult(
        success=result.success,
        output_path=result.output_path,
        error=result.error,
        metadata=result.metadata,
    )
