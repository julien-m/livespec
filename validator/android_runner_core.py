"""Android Maestro runner helpers."""

from __future__ import annotations

import os
import subprocess
import time
import warnings
from contextlib import suppress
from pathlib import Path
from typing import Any

from validator.runner_maestro_impl import (
    _ADB_NO_DEVICES_ERROR,
    _ANDROID_SDK_SKIP_ERROR,
    _AVD_BOOT_TIMEOUT_ERROR,
    _MAESTRO_MISSING_ERROR,
    _NO_FLOWS_ERROR,
    _WEAROS_EXPERIMENTAL_WARNING,
    AVD_BOOT_POLL_INTERVAL,
    AVD_BOOT_TIMEOUT_SECONDS,
    SCREENCAP_REMOTE_PATH,
    UICapabilityResult,
)

STDOUT_SNIPPET_LIMIT = 200


def _truncate_stdout(stdout: str) -> str:
    """Return a bounded stdout preview for metadata payloads."""
    return stdout[:STDOUT_SNIPPET_LIMIT]


def check_android_sdk() -> bool:
    """Return True when Android SDK is available through env vars."""
    return any(
        (path := os.environ.get(var)) and Path(path).exists()
        for var in ("ANDROID_HOME", "ANDROID_SDK_ROOT")
    )


def check_maestro() -> bool:
    """Return True when the Maestro CLI is on PATH."""
    try:
        result = subprocess.run(
            ["which", "maestro"], capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def list_avds() -> list[str]:
    """Return available AVD names from avdmanager."""
    try:
        result = subprocess.run(
            ["avdmanager", "list", "avd"], capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    return [
        line.strip()[len("Name:") :].strip()
        for line in result.stdout.splitlines()
        if line.strip().startswith("Name:")
    ]


def get_running_emulator() -> str | None:
    """Return the serial of the first running emulator."""
    try:
        result = subprocess.run(
            ["adb", "devices"], capture_output=True, text=True, timeout=15, check=False
        )
    except (OSError, FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return _first_emulator_serial(result.stdout)


def _first_emulator_serial(devices_output: str) -> str | None:
    """Extract the first `emulator-*` serial in device state."""
    for line in devices_output.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0].startswith("emulator-") and parts[1] == "device":
            return parts[0]
    return None


def boot_avd(avd_name: str) -> None:
    """Start an AVD in headless mode."""
    subprocess.Popen(
        ["emulator", "-avd", avd_name, "-no-window"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_for_boot(
    serial: str,
    timeout: int = AVD_BOOT_TIMEOUT_SECONDS,
    poll_interval: float = AVD_BOOT_POLL_INTERVAL,
) -> bool:
    """Wait for an emulator serial to report boot_completed=1."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _is_boot_completed(serial):
            return True
        time.sleep(poll_interval)
    return False


def _is_boot_completed(serial: str) -> bool:
    """Return True when adb reports boot_completed for one serial."""
    try:
        result = subprocess.run(
            ["adb", "-s", serial, "shell", "getprop", "sys.boot_completed"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and result.stdout.strip() == "1"


def boot_avd_and_wait(avd_name: str, timeout: int = AVD_BOOT_TIMEOUT_SECONDS) -> bool:
    """Boot an AVD and wait until adb can use it."""
    boot_avd(avd_name)
    time.sleep(2)
    serial = _wait_for_emulator_serial(timeout)
    if serial is None:
        return False
    remaining = int(time.monotonic() + max(timeout, 10) - time.monotonic())
    return wait_for_boot(serial, timeout=max(remaining, 10))


def _wait_for_emulator_serial(timeout: int) -> str | None:
    """Poll adb until an emulator serial appears."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        serial = get_running_emulator()
        if serial:
            return serial
        time.sleep(2)
    return None


def select_avd(avds: list[str], preferred: str) -> str | None:
    """Select an AVD by exact match, then deterministic substring match."""
    if preferred in avds:
        return preferred
    matches = sorted(avd for avd in avds if preferred in avd)
    return matches[0] if matches else None


def find_flows(project_dir: Path) -> list[Path]:
    """Return Maestro flow YAML files from the project."""
    for candidate in (project_dir / ".specs" / "maestro", project_dir / "maestro"):
        if candidate.is_dir():
            flows = sorted(candidate.glob("*.yaml"))
            if flows:
                return flows
    return []


def find_maestro_screenshots(maestro_output_dir: Path) -> list[Path]:
    """Return PNG screenshots emitted by Maestro."""
    return sorted(maestro_output_dir.glob("*.png")) if maestro_output_dir.exists() else []


def capture_adb_screenshot(serial: str, output_path: Path) -> bool:
    """Capture a screenshot via adb and pull it to the output path."""
    if not _run_adb_screencap(serial):
        return False
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pulled = _pull_adb_screencap(serial, output_path)
    _remove_remote_screencap(serial)
    return pulled and output_path.exists()


def _run_adb_screencap(serial: str) -> bool:
    """Run adb screencap on the device."""
    try:
        result = subprocess.run(
            ["adb", "-s", serial, "shell", "screencap", "-p", SCREENCAP_REMOTE_PATH],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _pull_adb_screencap(serial: str, output_path: Path) -> bool:
    """Pull the remote screencap file to the local output path."""
    try:
        result = subprocess.run(
            ["adb", "-s", serial, "pull", SCREENCAP_REMOTE_PATH, str(output_path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _remove_remote_screencap(serial: str) -> None:
    """Remove the temporary remote screencap file best-effort."""
    with suppress(OSError, subprocess.TimeoutExpired):
        subprocess.run(
            ["adb", "-s", serial, "shell", "rm", SCREENCAP_REMOTE_PATH],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


def resolve_baseline_path(project_dir: Path, screen: str, avd_name: str | None = None) -> Path:
    """Resolve a per-device or flat design-screens baseline path."""
    base = project_dir / ".specs" / "design" / "screens"
    return base / avd_name / f"{screen}.png" if avd_name else base / f"{screen}.png"


def parse_maestro_result(output: str, returncode: int) -> bool:
    """Return True when Maestro output represents a successful flow."""
    return returncode == 0 and "flow failed" not in output.lower()


def run_flow(
    handler: Any, avd_name: str | None, platform: str, fail_fast: bool, timeout: int
) -> UICapabilityResult:
    """Run all Maestro flows and aggregate their results."""
    blocked = _maestro_preflight_result(handler)
    if blocked is not None:
        return blocked
    if platform.lower() == "wearos":
        warnings.warn(_WEAROS_EXPERIMENTAL_WARNING, UserWarning, stacklevel=2)
    flows = find_flows(handler.project_dir)
    if not flows:
        return UICapabilityResult(
            success=False,
            error=_NO_FLOWS_ERROR,
            metadata={"flows_dir": str(handler.project_dir / ".specs" / "maestro")},
        )
    serial_result = _ensure_emulator(handler, avd_name, validate_override=True)
    if isinstance(serial_result, UICapabilityResult):
        return serial_result
    return _run_flow_files(handler.project_dir, flows, serial_result, fail_fast, timeout)


def _maestro_preflight_result(handler: Any) -> UICapabilityResult | None:
    """Return the SDK or Maestro preflight result when unavailable."""
    if not handler._check_android_sdk():
        return UICapabilityResult(
            success=False, error=_ANDROID_SDK_SKIP_ERROR, metadata={"skipped": True}
        )
    if not handler._check_maestro():
        return UICapabilityResult(
            success=False, error=_MAESTRO_MISSING_ERROR, metadata={"skipped": False}
        )
    return None


def _ensure_emulator(
    handler: Any, avd_name: str | None, *, validate_override: bool
) -> str | UICapabilityResult:
    """Return a running emulator serial, booting an AVD when needed."""
    serial = handler._get_running_emulator()
    if serial is not None:
        return serial
    effective_avd = avd_name or "Pixel_8_API_35"
    if avd_name and validate_override:
        matched = handler._select_avd(handler._list_avds(), preferred=avd_name)
        if matched is None:
            return UICapabilityResult(
                success=False,
                error=f"AVD '{avd_name}' not found.",
                metadata={"available_avds": handler._list_avds()},
            )
        effective_avd = matched
    if not handler._boot_avd_and_wait(effective_avd):
        return UICapabilityResult(
            success=False,
            error=_AVD_BOOT_TIMEOUT_ERROR.format(timeout=AVD_BOOT_TIMEOUT_SECONDS),
            metadata={"avd": effective_avd},
        )
    return handler._get_running_emulator() or UICapabilityResult(
        success=False, error=_ADB_NO_DEVICES_ERROR, metadata={"avd": effective_avd}
    )


def _run_flow_files(
    project_dir: Path, flows: list[Path], serial: str, fail_fast: bool, timeout: int
) -> UICapabilityResult:
    """Run each Maestro flow and return aggregate metadata."""
    rows: list[dict[str, Any]] = []
    all_passed = True
    for flow_path in flows:
        row, failed = _run_one_flow(project_dir, flow_path, timeout)
        rows.append(row)
        all_passed = all_passed and not failed
        stop = _flow_stop_result(flow_path, row, failed, fail_fast, rows)
        if stop is not None:
            return stop
    failed_flows = [row["flow"] for row in rows if not row.get("passed")]
    return UICapabilityResult(
        success=all_passed,
        error=f"Flows failed: {', '.join(failed_flows)}" if failed_flows else None,
        metadata={
            "flow_results": rows,
            "serial": serial,
            "total_flows": len(flows),
            "passed_flows": len(flows) - len(failed_flows),
        },
    )


def _flow_stop_result(
    flow_path: Path,
    row: dict[str, Any],
    failed: bool,
    fail_fast: bool,
    rows: list[dict[str, Any]],
) -> UICapabilityResult | None:
    """Return an early stop result for timeout or fail-fast failures."""
    if failed and "timed out" in str(row.get("error", "")):
        return UICapabilityResult(
            success=False,
            error=f"Flow '{flow_path.stem}' {row['error']}",
            metadata={"flow_results": rows},
        )
    if failed and fail_fast:
        return UICapabilityResult(
            success=False,
            error=f"Flow '{flow_path.stem}' failed (fail_fast=True)",
            metadata={"flow_results": rows},
        )
    return None


def _run_one_flow(project_dir: Path, flow_path: Path, timeout: int) -> tuple[dict[str, Any], bool]:
    """Run one Maestro flow and return `(row, failed)`."""
    try:
        result = subprocess.run(
            ["maestro", "test", str(flow_path)],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "flow": flow_path.stem,
            "passed": False,
            "error": f"timed out after {exc.timeout}s",
        }, True
    except OSError as exc:
        return {"flow": flow_path.stem, "passed": False, "error": str(exc)}, True
    output = result.stdout + result.stderr
    passed = parse_maestro_result(output, result.returncode)
    return {
        "flow": flow_path.stem,
        "passed": passed,
        "exit_code": result.returncode,
        "stdout_snippet": _truncate_stdout(output),
    }, not passed


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
    from validator.android_capture_core import capture_screenshot as capture

    return capture(
        handler, screen, avd_name, platform, fail_fast, timeout, output_path, feature_slug, run_id
    )
