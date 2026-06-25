"""iOS simulator, destination, and project helpers."""

from __future__ import annotations

import json
import os
import platform
import re
import subprocess
from pathlib import Path
from typing import Any, cast

from validator.runner_xcuitest_impl import SIMULATOR_BOOT_TIMEOUT_SECONDS


def check_macos() -> bool:
    """Return True when running on macOS."""
    return platform.system() == "Darwin"


def get_toolchain_path() -> str | None:
    """Return the path to xcodebuild, or None if unavailable."""
    try:
        result = subprocess.run(
            ["xcrun", "--find", "xcodebuild"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, FileNotFoundError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def check_xcode_license() -> bool:
    """Return True when xcodebuild reports an accepted license."""
    try:
        result = subprocess.run(
            ["xcodebuild", "-license", "check"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, FileNotFoundError):
        return False
    combined = (result.stdout + result.stderr).lower()
    if "license" in combined and ("not been accepted" in combined or "not accepted" in combined):
        return False
    return result.returncode == 0


def list_simulators() -> dict[str, Any]:
    """Return parsed `xcrun simctl list devices --json` output."""
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "list", "devices", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, FileNotFoundError, subprocess.TimeoutExpired):
        return {}
    if result.returncode != 0:
        return {}
    try:
        return cast(dict[str, Any], json.loads(result.stdout))
    except json.JSONDecodeError:
        return {}


def find_simulator_udid(destination_name: str, platform_filter: str = "iOS") -> str | None:
    """Find the UDID for a named simulator matching a platform filter."""
    for devices in _runtime_devices(platform_filter).values():
        for device in devices:
            if device.get("name", "").lower() == destination_name.lower():
                return cast(str, device.get("udid"))
    return None


def _runtime_devices(platform_filter: str) -> dict[str, list[dict[str, Any]]]:
    """Return simulator devices whose runtime key matches the platform filter."""
    devices_data = list_simulators()
    devices = cast(dict[str, list[dict[str, Any]]], devices_data.get("devices", {}))
    return {key: value for key, value in devices.items() if platform_filter.lower() in key.lower()}


def boot_simulator(udid: str, timeout: int = SIMULATOR_BOOT_TIMEOUT_SECONDS) -> bool:
    """Boot a simulator when needed and wait until it is ready."""
    if _simulator_is_booted(udid):
        return True
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "boot", udid],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if result.returncode != 0 and "already booted" not in result.stderr.lower():
        return False
    return wait_simulator_ready(udid, timeout)


def _simulator_is_booted(udid: str) -> bool:
    """Return True when simctl lists the UDID as booted."""
    for devices in cast(
        dict[str, list[dict[str, Any]]], list_simulators().get("devices", {})
    ).values():
        for device in devices:
            if device.get("udid") == udid:
                return device.get("state", "").lower() == "booted"
    return False


def wait_simulator_ready(udid: str, timeout: int = SIMULATOR_BOOT_TIMEOUT_SECONDS) -> bool:
    """Wait for a simulator to reach ready state."""
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "bootstatus", udid, "-b"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def filter_destinations_by_platform(
    destinations: list[dict[str, Any]], platform_name: str = "ios"
) -> list[dict[str, Any]]:
    """Filter destination dictionaries to those matching the given platform."""
    platform_map = {"ios": "ios simulator", "watchos": "watchos simulator"}
    match = platform_map.get(platform_name.lower(), platform_name.lower())
    return [dest for dest in destinations if match in dest.get("platform", "").lower()]


def autodetect_destination(
    platform_name: str = "ios", devices_data: dict[str, Any] | None = None
) -> str | None:
    """Pick the first available simulator destination for a platform."""
    devices_source = devices_data if devices_data is not None else list_simulators()
    devices = cast(dict[str, list[dict[str, Any]]], devices_source.get("devices", {}))
    runtime_match, label, wants_watch = _platform_destination_parts(platform_name)
    runtime_keys = sorted((key for key in devices if runtime_match in key), reverse=True)
    for runtime_key in runtime_keys:
        name = _first_available_device_name(devices[runtime_key], wants_watch)
        if name:
            return f"platform={label},name={name}"
    return None


def _platform_destination_parts(platform_name: str) -> tuple[str, str, bool]:
    """Return runtime marker, destination label, and watch-name filter."""
    if platform_name.lower() == "watchos":
        return "watchOS", "watchOS Simulator", True
    return "iOS", "iOS Simulator", False


def _first_available_device_name(devices: list[dict[str, Any]], wants_watch: bool) -> str | None:
    """Return the first available device name matching watch/non-watch intent."""
    for device in devices:
        name = str(device.get("name", ""))
        if device.get("isAvailable", False) and bool("watch" in name.lower()) == wants_watch:
            return name
    return None


def friendly_destination_id(destination: str) -> str:
    """Derive a stable screenshot folder name from an xcodebuild destination."""
    parts = _destination_parts(destination)
    if parts.get("id"):
        parts.update(_device_parts_for_udid(parts["id"]))
    if parts.get("name"):
        return _named_destination_id(parts)
    return _sanitize(destination) or "destination"


def _destination_parts(destination: str) -> dict[str, str]:
    """Parse comma-separated xcodebuild destination qualifiers."""
    parts: dict[str, str] = {}
    for item in (part.strip() for part in destination.split(",") if part.strip()):
        if "=" in item:
            key, value = item.split("=", 1)
            parts[key] = value
    return parts


def _device_parts_for_udid(udid: str) -> dict[str, str]:
    """Resolve simulator name/platform/version for a pinned UDID."""
    for runtime_key, devices in cast(
        dict[str, list[dict[str, Any]]], list_simulators().get("devices", {})
    ).items():
        match = next((device for device in devices if device.get("udid") == udid), None)
        if match is not None:
            return _parts_from_runtime(runtime_key, str(match.get("name", "")))
    return {}


def _parts_from_runtime(runtime_key: str, name: str) -> dict[str, str]:
    """Build destination id parts from one simctl runtime key."""
    platform_label = _platform_label_from_runtime(runtime_key)
    version_match = re.search(r"(?:iOS|watchOS|tvOS|visionOS)-(\d+)-(\d+)", runtime_key)
    parts = {"name": name, "platform": platform_label}
    if version_match:
        parts["OS"] = f"{version_match.group(1)}.{version_match.group(2)}"
    return parts


def _platform_label_from_runtime(runtime_key: str) -> str:
    """Return a human platform label for a simctl runtime key."""
    key = runtime_key.lower()
    if "watchos" in key:
        return "watchOS Simulator"
    if "tvos" in key:
        return "tvOS Simulator"
    if "visionos" in key or "xros" in key:
        return "visionOS Simulator"
    return "iOS Simulator"


def _named_destination_id(parts: dict[str, str]) -> str:
    """Render sanitized destination id from parsed destination parts."""
    platform_prefix = re.sub(r"_simulator$", "", _sanitize(parts.get("platform", "simulator")))
    rendered = [platform_prefix or "simulator", _sanitize(parts["name"])]
    if parts.get("variant"):
        rendered.append(_sanitize(parts["variant"]))
    if parts.get("OS"):
        rendered.append(_sanitize(parts["OS"]))
    return "_".join(rendered)


def _sanitize(value: str) -> str:
    """Return a filesystem-safe lowercase identifier."""
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def find_xcodeproj(project_dir: Path) -> Path | None:
    """Return the first .xcworkspace or .xcodeproj under a project root."""
    if not project_dir.exists():
        return None
    workspaces = sorted(project_dir.glob("*.xcworkspace"))
    if workspaces:
        return workspaces[0]
    projects = sorted(project_dir.glob("*.xcodeproj"))
    return projects[0] if projects else None


def list_shared_schemes(xcodeproj: Path) -> list[str]:
    """Read shared Xcode scheme names."""
    schemes_dir = xcodeproj / "xcshareddata" / "xcschemes"
    return (
        sorted(path.stem for path in schemes_dir.glob("*.xcscheme")) if schemes_dir.is_dir() else []
    )


def autodetect_scheme(xcodeproj: Path, platform_name: str | None = None) -> str | None:
    """Pick the most likely shared scheme for a platform."""
    schemes = list_shared_schemes(xcodeproj)
    if not schemes:
        return None
    if platform_name == "watchos":
        return next((scheme for scheme in schemes if "watch" in scheme.lower()), None)
    if platform_name == "ios":
        return next((scheme for scheme in schemes if "watch" not in scheme.lower()), schemes[0])
    return schemes[0]


def build_xcodebuild_command(
    destination: str,
    test_scheme: str | None,
    xcresult_path: Path,
    project: str | None = None,
    workspace: str | None = None,
    only_testing: str | None = None,
) -> list[str]:
    """Assemble the xcodebuild test command."""
    command = [
        "xcodebuild",
        "test",
        "-destination",
        destination,
        "-resultBundlePath",
        str(xcresult_path),
        "CODE_SIGN_IDENTITY=",
        "CODE_SIGNING_REQUIRED=NO",
    ]
    if only_testing:
        command.extend(["-only-testing:" + only_testing])
    if workspace:
        command.extend(["-workspace", workspace])
    elif project:
        command.extend(["-project", project])
    if test_scheme:
        command.extend(["-scheme", test_scheme])
    return command


def build_env(launch_arguments: list[str] | None) -> dict[str, str] | None:
    """Build xcodebuild env with encoded XCUI_LAUNCH_ARGS when needed."""
    if not launch_arguments:
        return None
    env = os.environ.copy()
    env["XCUI_LAUNCH_ARGS"] = json.dumps(launch_arguments)
    return env


def extract_failed_tests(output: str) -> list[str]:
    """Parse xcodebuild output to find failing test names."""
    failed: list[str] = []
    for line in output.splitlines():
        if "failed (" in line.lower() and "test case" in line.lower():
            start, end = line.find("["), line.find("]")
            if start != -1 and end != -1:
                failed.append(line[start + 1 : end].replace(" ", "/"))
    return failed
