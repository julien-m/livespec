"""iOS/watchOS UI runner support for XCUITest-based projects.

This module provides an orchestrator around xcrun/xcodebuild so the validator
can detect an Xcode project and invoke screenshot capture, flow execution, and
baseline comparison for iOS and watchOS simulators.
"""

# @spec FR-001: iOS/watchOS XCUITest manifest runner — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-001  # noqa: E501
# @spec FR-002: .xcresult parsing + HEIC→PNG — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-002  # noqa: E501
# @spec FR-003: Simulator boot orchestration — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-003  # noqa: E501
# @spec FR-004: watchOS destination filtering — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-004  # noqa: E501
# @spec FR-005: launch_arguments injection — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-005  # noqa: E501
# @spec FR-006: Xcode license detection — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-006

from __future__ import annotations

import json
import platform
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]

DEFAULT_COMPARE_THRESHOLD = 0.05
SCREENSHOT_TIMEOUT_SECONDS = 1200  # 20 min — first build of a large iOS app
FLOW_TIMEOUT_SECONDS = 1800        # 30 min — flow runs are longer than single captures
COMPARE_TIMEOUT_SECONDS = 60
SIMULATOR_BOOT_TIMEOUT_SECONDS = 120
XCRESULTTOOL_TIMEOUT_SECONDS = 60
STDOUT_SNIPPET_LIMIT = 200

_MACOS_SKIP_ERROR = "iOS UI runner requires macOS — skipped on non-macOS hosts"
_XCODE_MISSING_ERROR = (
    "Xcode not installed. Install from App Store or https://developer.apple.com/xcode/"
)
_LICENSE_ERROR = "Xcode license not accepted. Run: sudo xcodebuild -license accept"
_WATCHOS_RUNTIME_ERROR = (
    "watchOS simulator runtime not installed. Install via Xcode > Settings > Platforms."
)
_SIMULATOR_NOT_FOUND_ERROR = (
    "Simulator not found. Run: xcrun simctl list devices to see available simulators."
)


@dataclass
class UICapabilityResult:
    """Describe the outcome of one UI runner capability invocation.

    Attributes:
        success: Whether the delegated command completed successfully.
        output_path: Output artifact path when one is expected and available.
        error: Human-readable failure detail when the capability fails.
        metadata: Structured subprocess metadata for higher-level reporting.
    """

    success: bool
    output_path: Path | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=lambda: cast(dict[str, Any], {}))


def _truncate_stdout(stdout: str) -> str:
    """Return a bounded stdout preview for metadata payloads.

    Args:
        stdout: Full stdout emitted by the delegated command.

    Returns:
        At most the first 200 characters so result metadata stays compact.
    """
    return stdout[:STDOUT_SNIPPET_LIMIT]


def _resolve_project_path(project_dir: Path, candidate: str) -> Path:
    """Resolve absolute or project-relative artifact paths.

    Args:
        project_dir: Project root used for relative paths.
        candidate: User- or manifest-provided path string.

    Returns:
        An absolute filesystem path.
    """
    candidate_path = Path(candidate)
    if candidate_path.is_absolute():
        return candidate_path
    return project_dir / candidate_path


def xcuitest_runner_manifest_path() -> Path:
    """Return the filesystem path to the built-in iOS/watchOS runner manifest.

    Returns:
        Absolute path to `livespec/ui-runners/ios.yaml`.
    """
    return Path(__file__).resolve().parent.parent / "livespec" / "ui-runners" / "ios.yaml"


# @spec FR-003: Simulator boot orchestration — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-003  # noqa: E501
class XCUITestRunnerHandler:
    """Handle UI runner capabilities for XCUITest iOS/watchOS projects."""

    def __init__(self, project_dir: Path | str) -> None:
        """Initialize the handler.

        Args:
            project_dir: Project root containing Xcode project assets.
        """
        self.project_dir = Path(project_dir).resolve()

    # ------------------------------------------------------------------
    # Platform / toolchain guards
    # ------------------------------------------------------------------

    def _check_macos(self) -> bool:
        """Return True when running on macOS (Darwin)."""
        return platform.system() == "Darwin"

    # @spec FR-006: Xcode license detection — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-006  # noqa: E501
    def _get_toolchain_path(self) -> str | None:
        """Return path to xcodebuild, or None if not found."""
        try:
            result = subprocess.run(
                ["xcrun", "--find", "xcodebuild"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (OSError, FileNotFoundError):
            pass
        return None

    # @spec FR-006: Xcode license detection — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-006  # noqa: E501
    def _check_xcode_license(self) -> bool:
        """Return True if the Xcode license has been accepted.

        Runs `xcodebuild -license check` and inspects the output.
        Returns False when the license has not been accepted.
        """
        try:
            result = subprocess.run(
                ["xcodebuild", "-license", "check"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            combined = (result.stdout + result.stderr).lower()
            # Xcode outputs a message about the license not being accepted on stderr
            if "license" in combined and (
                "not been accepted" in combined or "not accepted" in combined
            ):
                return False
            return result.returncode == 0
        except (OSError, FileNotFoundError):
            return False

    # @spec FR-012: platform-aware preflight message — .specs/features/037-test-multi-runner-integration/spec.md#fr-012  # noqa: E501
    def preflight_message(self) -> str:
        """Return an actionable diagnostic for the dispatcher BLOCKED line.

        Returns:
            Empty string when the toolchain is ready; otherwise a human
            readable hint covering the missing piece (host OS, xcrun, etc.).
        """
        if not self._check_macos():
            return (
                f"XCUITest runner requires macOS host (current: {platform.system().lower()})"
            )
        if self._get_toolchain_path() is None:
            return "xcrun simctl not found — install Xcode CLI tools"
        if not self._check_xcode_license():
            return _LICENSE_ERROR
        return ""

    # ------------------------------------------------------------------
    # Project detection
    # ------------------------------------------------------------------

    def detect(self) -> bool:
        """Check whether the project is an Xcode/Swift project.

        Returns:
            `True` when the project contains a `.xcodeproj`, `.xcworkspace`,
            or `Package.swift` file, otherwise `False`.
        """
        # Check for Package.swift (Swift Package Manager projects)
        if (self.project_dir / "Package.swift").exists():
            return True
        # Check for .xcodeproj or .xcworkspace directories
        if not self.project_dir.exists():
            return False
        for entry in self.project_dir.iterdir():
            if entry.suffix in {".xcodeproj", ".xcworkspace"}:
                return True
        return False

    # ------------------------------------------------------------------
    # Simulator management
    # ------------------------------------------------------------------

    # @spec FR-003: Simulator boot orchestration — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-003  # noqa: E501
    def _list_simulators(self) -> dict[str, Any]:
        """Return parsed output of `xcrun simctl list devices --json`.

        Returns:
            Parsed JSON dict, or empty dict on error.
        """
        try:
            result = subprocess.run(
                ["xcrun", "simctl", "list", "devices", "--json"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if result.returncode == 0:
                return cast(dict[str, Any], json.loads(result.stdout))
        except (OSError, json.JSONDecodeError, subprocess.TimeoutExpired):
            pass
        return {}

    # @spec FR-003: Simulator boot orchestration — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-003  # noqa: E501
    def _find_simulator_udid(
        self, destination_name: str, platform_filter: str = "iOS"
    ) -> str | None:
        """Find the UDID for a named simulator matching the given platform.

        Args:
            destination_name: Simulator name (e.g. "iPhone 16").
            platform_filter: Platform string to match in runtime key (e.g. "iOS", "watchOS").

        Returns:
            UDID string, or None if not found.
        """
        devices_data = self._list_simulators()
        devices_by_runtime = devices_data.get("devices", {})
        for runtime_key, device_list in devices_by_runtime.items():
            if platform_filter.lower() not in runtime_key.lower():
                continue
            for device in device_list:
                if device.get("name", "").lower() == destination_name.lower():
                    return cast(str, device.get("udid"))
        return None

    # @spec FR-003: Simulator boot orchestration — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-003  # noqa: E501
    def _boot_simulator(self, udid: str, timeout: int = SIMULATOR_BOOT_TIMEOUT_SECONDS) -> bool:
        """Boot a simulator if it is not already booted.

        Args:
            udid: Simulator UDID.
            timeout: Maximum seconds to wait for boot.

        Returns:
            True if the simulator is booted (or was already booted), False on failure.
        """
        # Check current state first
        devices_data = self._list_simulators()
        for device_list in devices_data.get("devices", {}).values():
            for device in device_list:
                if device.get("udid") == udid:
                    if device.get("state", "").lower() == "booted":
                        return True  # Already booted — nothing to do
                    break

        # Boot the simulator
        try:
            result = subprocess.run(
                ["xcrun", "simctl", "boot", udid],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if result.returncode != 0 and "already booted" not in result.stderr.lower():
                return False
        except (OSError, subprocess.TimeoutExpired):
            return False

        return self._wait_simulator_ready(udid, timeout)

    # @spec FR-003: Simulator boot orchestration — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-003  # noqa: E501
    def _wait_simulator_ready(
        self, udid: str, timeout: int = SIMULATOR_BOOT_TIMEOUT_SECONDS
    ) -> bool:
        """Wait for a simulator to reach ready state.

        Args:
            udid: Simulator UDID.
            timeout: Maximum seconds to wait.

        Returns:
            True when the simulator is ready, False on timeout or error.
        """
        try:
            result = subprocess.run(
                ["xcrun", "simctl", "bootstatus", udid, "-b"],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            return result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    # ------------------------------------------------------------------
    # Platform filtering
    # ------------------------------------------------------------------

    # @spec FR-004: watchOS destination filtering — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-004  # noqa: E501
    def _filter_destinations_by_platform(
        self, destinations: list[dict[str, Any]], platform: str = "ios"
    ) -> list[dict[str, Any]]:
        """Filter a destinations list to those matching the given platform.

        Args:
            destinations: List of destination dicts from ios.yaml.
            platform: "ios" (default) or "watchos".

        Returns:
            Filtered list of matching destination dicts.
        """
        platform_lower = platform.lower()
        platform_map = {
            "ios": "ios simulator",
            "watchos": "watchos simulator",
        }
        match_str = platform_map.get(platform_lower, platform_lower)
        return [d for d in destinations if match_str in d.get("platform", "").lower()]

    # @spec FR-003: Simulator boot orchestration — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-003  # noqa: E501
    def _autodetect_destination(self, platform: str = "ios") -> str | None:
        """Pick the first available simulator destination for the given platform.

        Strapt-class robustness: when surfaces.yaml does not declare a destination,
        scan `xcrun simctl list devices available` and pick the first booted-or-shutdown
        device matching the platform (iPhone for ios, Apple Watch for watchos). This
        avoids the hardcoded "iPhone 16" trap on machines that only ship newer
        simulator runtimes.

        Args:
            platform: "ios" (default) or "watchos".

        Returns:
            Xcode destination string (e.g. "platform=iOS Simulator,name=iPhone 17"),
            or None if no matching simulator is available.
        """
        devices_data = self._list_simulators()
        runtimes = cast(dict[str, list[dict[str, Any]]], devices_data.get("devices", {}))

        platform_lower = platform.lower()

        def _watch_name(n: str) -> bool:
            return "watch" in n.lower()

        def _non_watch_name(n: str) -> bool:
            return "watch" not in n.lower()

        if platform_lower == "watchos":
            runtime_match = "watchOS"
            sim_label = "watchOS Simulator"
            name_filter = _watch_name
        else:
            runtime_match = "iOS"
            sim_label = "iOS Simulator"
            name_filter = _non_watch_name

        # Sort runtime keys descending so newest OS wins (e.g. iOS-26 before iOS-17)
        runtime_keys = sorted(
            (k for k in runtimes if runtime_match in k),
            reverse=True,
        )
        for runtime_key in runtime_keys:
            for device in runtimes[runtime_key]:
                if not device.get("isAvailable", False):
                    continue
                name = device.get("name", "")
                if name and name_filter(name):
                    return f"platform={sim_label},name={name}"
        return None

    def _normalize_destination_by_id(self, destination: str) -> str:
        """Rewrite ``id=<UUID>`` destinations to ``name=<name>,OS=<version>``.

        Downstream code derives the screenshot folder name from the destination
        string. Using a UDID makes folders unreadable and unstable — the UDID
        changes whenever the simulator is recreated, even though the device
        name is identical. When two simulators share the same name across
        runtime versions (the historical reason projects pinned by UDID), we
        disambiguate by appending ``OS=<version>`` so xcodebuild can still
        target the right device.

        Falls back to the original destination string when:
          * the destination does not contain ``id=<UUID>``,
          * the UDID cannot be resolved via ``xcrun simctl list``,
          * the matched device has no usable name.

        Args:
            destination: Xcode ``-destination`` value.

        Returns:
            A normalized destination string suitable for both xcodebuild and
            for folder-name derivation.
        """
        destination_parts = destination.split(",")
        udid: str | None = None
        retained_parts: list[str] = []
        for part in destination_parts:
            if part.startswith("id="):
                udid = part.removeprefix("id=")
                continue
            retained_parts.append(part)

        if udid is None:
            return destination

        devices_data = self._list_simulators()
        runtimes = cast(dict[str, list[dict[str, Any]]], devices_data.get("devices", {}))
        for runtime_key, devs in runtimes.items():
            for dev in devs:
                if dev.get("udid") != udid:
                    continue
                name = dev.get("name")
                if not name:
                    return destination

                runtime_suffix = runtime_key.rsplit(".", 1)[-1]
                runtime_parts = runtime_suffix.split("-")
                os_version = (
                    f"{runtime_parts[-2]}.{runtime_parts[-1]}"
                    if len(runtime_parts) >= 3
                    else None
                )
                parts = [
                    f"name={name}" if part.startswith("name=") else part
                    for part in retained_parts
                ]
                if all(not part.startswith("name=") for part in parts):
                    insert_at = 1 if parts and parts[0].startswith("platform=") else 0
                    parts.insert(insert_at, f"name={name}")
                if os_version:
                    parts.append(f"OS={os_version}")
                return ",".join(parts)
        return destination

    # ------------------------------------------------------------------
    # .xcresult bundle parsing
    # ------------------------------------------------------------------

    # @spec FR-002: .xcresult parsing + HEIC→PNG — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-002  # noqa: E501
    def _convert_heic_to_png(self, heic_path: Path, png_path: Path) -> bool:
        """Convert a HEIC image to PNG using the macOS `sips` utility.

        Args:
            heic_path: Path to the HEIC file.
            png_path: Destination path for the PNG output.

        Returns:
            True on success, False on failure.
        """
        try:
            result = subprocess.run(
                ["sips", "-s", "format", "png", str(heic_path), "--out", str(png_path)],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            return result.returncode == 0 and png_path.exists()
        except (OSError, subprocess.TimeoutExpired):
            return False

    def _extract_attachments_from_xcresult_json(
        self, data: Any, attachments: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """Recursively extract ActionTestAttachment nodes from xcresulttool JSON.

        Args:
            data: Parsed JSON structure.
            attachments: Accumulator list (used in recursive calls).

        Returns:
            List of attachment dicts.
        """
        if attachments is None:
            attachments = []
        if isinstance(data, dict):
            data_dict = cast(dict[str, Any], data)
            type_field = data_dict.get("_type")
            if (
                isinstance(type_field, dict)
                and cast(dict[str, Any], type_field).get("_name") == "ActionTestAttachment"
            ):
                attachments.append(data_dict)
            for value in data_dict.values():
                self._extract_attachments_from_xcresult_json(value, attachments)
        elif isinstance(data, list):
            for item in cast(list[Any], data):
                self._extract_attachments_from_xcresult_json(item, attachments)
        return attachments

    # @spec FR-002: .xcresult parsing + HEIC→PNG — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-002  # noqa: E501
    def _parse_xcresult(
        self, bundle_path: Path, output_dir: Path, destination_id: str
    ) -> list[Path]:
        """Extract screenshots from an .xcresult bundle.

        Runs `xcrun xcresulttool get` to get the JSON manifest, extracts all
        ActionTestAttachment nodes, exports each image, converts HEIC → PNG
        where needed, and writes PNGs to `output_dir/<destination_id>/`.

        Args:
            bundle_path: Path to the `.xcresult` directory.
            output_dir: Root output directory for screenshots.
            destination_id: Subdirectory name (e.g. "iPhone_16").

        Returns:
            List of exported PNG paths. May be partial if the bundle is corrupted.
        """
        dest_dir = output_dir / destination_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        exported: list[Path] = []

        # Xcode 26 introduced `xcresulttool export attachments` which dumps
        # every ActionTestAttachment for every test method in one shot, with
        # a manifest.json mapping `exportedFileName → suggestedHumanName`.
        # This is the only reliable way to extract attachments in Xcode 26+
        # since `--legacy export --type file --id <ref>` errors out with
        # "item missing for id" for ids obtained from the legacy graph dump.
        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                subprocess.run(
                    [
                        "xcrun",
                        "xcresulttool",
                        "export",
                        "attachments",
                        "--path",
                        str(bundle_path),
                        "--output-path",
                        tmp_dir,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=XCRESULTTOOL_TIMEOUT_SECONDS,
                    check=False,
                )
            except (subprocess.TimeoutExpired, OSError):
                # EC-002: corrupted bundle — return empty partial result.
                return exported

            manifest_path = Path(tmp_dir) / "manifest.json"
            if not manifest_path.exists():
                return exported

            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return exported

            # The manifest is a list of {testIdentifier: [{exportedFileName,
            # suggestedHumanReadableName, ...}, ...]}. We walk every test's
            # attachments and rename each file from <exportedFileName> to
            # `<screen>.png` using the user-supplied attachment name (which
            # is the screen identifier — see snapshot() in the template).
            attachments_iter = self._iter_manifest_attachments(manifest)
            for entry in attachments_iter:
                exported_file = Path(tmp_dir) / entry["exportedFileName"]
                if not exported_file.exists():
                    continue
                suffix = exported_file.suffix.lower()
                if suffix not in {".png", ".heic", ".jpg", ".jpeg"}:
                    continue
                screen_name = entry.get("attachmentName", exported_file.stem)
                # `attachmentName` is the user-supplied tag (e.g. "watch-home").
                # The suggestedHumanReadableName carries Xcode's full filename
                # (e.g. "watch-home_0_<uuid>.png") — we don't need that.
                png_path = dest_dir / f"{screen_name}.png"
                if suffix == ".heic":
                    if self._convert_heic_to_png(exported_file, png_path):
                        exported.append(png_path)
                else:
                    import shutil as _shutil

                    _shutil.copy2(exported_file, png_path)
                    exported.append(png_path)

        return exported

    def _iter_manifest_attachments(
        self, manifest: object
    ) -> list[dict[str, str]]:
        """Flatten `xcresulttool export attachments` manifest into one list.

        The manifest groups attachments per test method:
            [{"attachments": [{"exportedFileName": "<uuid>.png",
                               "suggestedHumanReadableName":
                                   "<screen>_<idx>_<uuid>.png",
                               ...}, ...]},
             ...]

        We derive the screen name from `suggestedHumanReadableName` by
        stripping the trailing `_<idx>_<uuid>.<ext>` suffix that Xcode
        appends. This recovers the user-set `attachment.name` from the
        Swift test (e.g. `"watch-home"`).

        Args:
            manifest: Parsed manifest.json content.

        Returns:
            Flat list of attachment dicts (`exportedFileName`, `screenName`).
            Entries lacking either field are dropped.
        """
        flat: list[dict[str, str]] = []
        if not isinstance(manifest, list):
            return flat
        for test_entry in cast(list[Any], manifest):
            if not isinstance(test_entry, dict):
                continue
            atts = cast(dict[str, Any], test_entry).get("attachments")
            if not isinstance(atts, list):
                continue
            for att in cast(list[Any], atts):
                if not isinstance(att, dict):
                    continue
                d = cast(dict[str, Any], att)
                exported_file = d.get("exportedFileName")
                if not isinstance(exported_file, str):
                    continue
                suggested = d.get("suggestedHumanReadableName")
                if isinstance(suggested, str):
                    screen_name = self._strip_attachment_suffix(suggested)
                else:
                    screen_name = exported_file.rsplit(".", 1)[0]
                flat.append(
                    {
                        "exportedFileName": exported_file,
                        "attachmentName": screen_name,
                    }
                )
        return flat

    @staticmethod
    def _strip_attachment_suffix(suggested_name: str) -> str:
        """Recover the user-set attachment name from Xcode's filename.

        Xcode generates `"<name>_<idx>_<uuid>.<ext>"` for each XCTAttachment.
        We strip the extension, then drop the trailing `_<idx>_<uuid>` and
        any `.tree` suffix added for paired tree dumps.

        Args:
            suggested_name: Xcode's `suggestedHumanReadableName`.

        Returns:
            The bare screen identifier (e.g. `"watch-home"` for
            `"watch-home_0_<uuid>.png"` or `"watch-home"` for
            `"watch-home.tree_0_<uuid>.txt"`).
        """
        # Drop extension
        stem = suggested_name.rsplit(".", 1)[0]
        # `<name>_<idx>_<uuid>` — split off the last two underscore segments
        # if they look like an index + UUID. The UUID always contains hyphens
        # in canonical 8-4-4-4-12 form, so check for that.
        parts = stem.split("_")
        if (
            len(parts) >= 3
            and parts[-1].count("-") >= 4
            and parts[-2].isdigit()
        ):
            stem = "_".join(parts[:-2])
        # Tree dumps share the screen name but with a `.tree` infix: strip it.
        if stem.endswith(".tree"):
            stem = stem[: -len(".tree")]
        return stem

    # ------------------------------------------------------------------
    # Public capabilities
    # ------------------------------------------------------------------

    # @spec FR-005: launch_arguments injection — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-005  # noqa: E501
    def capture_screenshot(
        self,
        screen: str = "main",
        destination: str | None = None,
        test_scheme: str | None = None,
        launch_arguments: list[str] | None = None,
        project: str | None = None,
        workspace: str | None = None,
        platform: str | None = None,
        only_testing: str | None = None,
    ) -> UICapabilityResult:
        """Run xcodebuild test, extract screenshots from .xcresult bundle.

        Args:
            screen: Screen identifier used for output naming.
            destination: Xcode destination string.
            test_scheme: Xcode scheme name (auto-detected if None).
            launch_arguments: Arguments passed as XCUI_LAUNCH_ARGS env var.
            project: Optional .xcodeproj path (relative to project_dir or absolute).
            workspace: Optional .xcworkspace path (takes precedence over project).
            platform: 'ios' or 'watchos' — used for scheme auto-detection.

        Returns:
            Result containing the list of exported PNG paths on success.
        """
        if not self._check_macos():
            return UICapabilityResult(
                success=False,
                error=_MACOS_SKIP_ERROR,
                metadata={"skipped": True},
            )

        if self._get_toolchain_path() is None:
            return UICapabilityResult(
                success=False,
                error=_XCODE_MISSING_ERROR,
                metadata={"command": "xcrun --find xcodebuild"},
            )

        if not self._check_xcode_license():
            return UICapabilityResult(
                success=False,
                error=_LICENSE_ERROR,
            )

        # Auto-detect scheme/project when surfaces.yaml didn't supply them — this
        # is what unblocks `livespec ui-runner dispatch` on projects whose
        # surfaces.yaml predates the runnerConfig wiring (e.g. v8 migrations).
        if test_scheme is None or (project is None and workspace is None):
            xcodeproj = self._find_xcodeproj()
            if xcodeproj is not None:
                if project is None and workspace is None:
                    rel = xcodeproj.relative_to(self.project_dir) if (
                        xcodeproj.is_relative_to(self.project_dir)
                    ) else xcodeproj
                    if xcodeproj.suffix == ".xcworkspace":
                        workspace = str(rel)
                    else:
                        project = str(rel)
                if test_scheme is None:
                    test_scheme = self._autodetect_scheme(xcodeproj, platform=platform)
            if test_scheme is None:
                return UICapabilityResult(
                    success=False,
                    error=(
                        "xcodebuild requires a -scheme. Either declare "
                        "`runnerConfig.scheme: <name>` in .specs/surfaces.yaml or share "
                        "a scheme via Xcode > Product > Scheme > Manage Schemes "
                        "(check 'Shared')."
                    ),
                    metadata={"project_dir": str(self.project_dir)},
                )

        # Auto-detect destination when surfaces.yaml didn't supply one. This avoids
        # the hardcoded "iPhone 16" trap on machines that only ship newer simulator
        # runtimes (iPhone 17+). Falls back to the legacy default if simctl is
        # unavailable so existing v12 manifests keep working.
        if destination is None:
            detected = self._autodetect_destination(platform=platform or "ios")
            if detected is not None:
                destination = detected
            else:
                destination = (
                    "platform=watchOS Simulator,name=Apple Watch"
                    if (platform or "").lower() == "watchos"
                    else "platform=iOS Simulator,name=iPhone 16"
                )

        # Rewrite "id=<UUID>" destinations to "name=<name>,OS=<version>" so the
        # screenshot folder name stays human-readable and stable across simulator
        # recreations. No-op when destination already uses name=, or when the
        # UDID cannot be resolved.
        destination = self._normalize_destination_by_id(destination)

        # Persist the .xcresult under the project so `livespec ui-runner inspect`
        # can read it after the dispatch returns. TemporaryDirectory would delete
        # it before the user has a chance to inspect the trees.
        bundles_dir = self.project_dir / ".specs" / ".test-bundles"
        bundles_dir.mkdir(parents=True, exist_ok=True)
        # Reuse a stable filename per (surface, screen) so subsequent runs
        # overwrite cleanly. We can't use the surface id here (handler doesn't
        # know it), but only_testing is the next-best disambiguator.
        bundle_name = (only_testing or "default").replace("/", "_") + ".xcresult"
        xcresult_path = bundles_dir / bundle_name
        hash_path = bundles_dir / f"{bundle_name}.hash"

        # Optimisation #1: Swift-content hash cache.
        # Hash every .swift file under the test target's directory. If the
        # hash matches the one we stored after the previous successful run,
        # skip xcodebuild entirely — the bundle on disk already reflects the
        # current source. Saves a full build + test cycle on iterations where
        # `inspect --patch` reported 0 changes.
        swift_hash = self._compute_swift_hash(only_testing)
        if (
            swift_hash is not None
            and xcresult_path.exists()
            and hash_path.exists()
            and hash_path.read_text(encoding="utf-8").strip() == swift_hash
        ):
            # Cache hit: skip xcodebuild but STILL extract attachments from
            # the existing bundle. Otherwise we'd return success with
            # exported_paths=[], leaving the .specs/design/screens/<dest>/
            # directory empty on repeat runs.
            destination_id = destination.replace("=", "_").replace(
                ",", "_"
            ).replace(" ", "_")
            cached_output_dir = self.project_dir / ".specs" / "design" / "screens"
            cached_paths = self._parse_xcresult(
                xcresult_path, cached_output_dir, destination_id
            )
            return UICapabilityResult(
                success=True,
                output_path=cached_paths[0] if cached_paths else None,
                metadata={
                    "command": "<cached — swift hash unchanged>",
                    "exit_code": 0,
                    "exported_paths": [str(p) for p in cached_paths],
                    "stdout_snippet": "",
                    "xcresult_path": str(xcresult_path),
                    "cached": True,
                },
            )

        if xcresult_path.exists():
            import shutil as _shutil

            _shutil.rmtree(xcresult_path)

        command = self._build_xcodebuild_command(
            destination=destination,
            test_scheme=test_scheme,
            xcresult_path=xcresult_path,
            project=project,
            workspace=workspace,
            only_testing=only_testing,
        )
        env = self._build_env(launch_arguments)

        # Optimisation #2: auto-retry on "Timed out while evaluating UI query".
        # SwiftUI accessibility hierarchies are flaky on first query; xcodebuild
        # sometimes reports this opaque error and exits non-zero. A second run
        # almost always succeeds because DerivedData is now warm and the
        # simulator has paged in the runtime. Retry up to RETRY_LIMIT times.
        RETRY_LIMIT = 3
        TIMEOUT_MARKER = "Failed to get matching snapshots: Timed out while evaluating UI query"
        result: subprocess.CompletedProcess[str] | None = None
        for attempt in range(1, RETRY_LIMIT + 1):
            if xcresult_path.exists() and attempt > 1:
                import shutil as _shutil

                _shutil.rmtree(xcresult_path)
            try:
                result = subprocess.run(
                    command,
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    timeout=SCREENSHOT_TIMEOUT_SECONDS,
                    env=env,
                    check=False,
                )
            except subprocess.TimeoutExpired as error:
                return UICapabilityResult(
                    success=False,
                    error=f"xcodebuild test timed out after {error.timeout}s",
                    metadata={"timeout": error.timeout, "command": " ".join(command)},
                )
            except OSError as error:
                return UICapabilityResult(
                    success=False,
                    error=f"Failed to execute xcodebuild: {error}",
                    metadata={"command": " ".join(command)},
                )
            stream = (result.stdout or "") + (result.stderr or "")
            if TIMEOUT_MARKER not in stream:
                break
            # Else loop and retry — flaky UI query timeout.

        if result is None:  # pragma: no cover - unreachable, satisfies pyright
            return UICapabilityResult(success=False, error="no result")

        # Check for license error in output
        combined_output = result.stdout + result.stderr
        combined_lower = combined_output.lower()
        if "license" in combined_lower and "not been accepted" in combined_lower:
            return UICapabilityResult(
                success=False,
                error=_LICENSE_ERROR,
                metadata={"command": " ".join(command)},
            )

        if not xcresult_path.exists():
            return UICapabilityResult(
                success=False,
                error="No .xcresult bundle produced by xcodebuild test",
                metadata={
                    "command": " ".join(command),
                    "exit_code": result.returncode,
                    "stdout_snippet": _truncate_stdout(result.stdout),
                },
            )

        destination_id = destination.replace("=", "_").replace(",", "_").replace(" ", "_")
        output_dir = self.project_dir / ".specs" / "design" / "screens"
        exported_paths = self._parse_xcresult(xcresult_path, output_dir, destination_id)

        first_path = exported_paths[0] if exported_paths else None
        has_error = not exported_paths and result.returncode != 0

        # Persist the Swift hash next to the bundle so the next call can skip
        # xcodebuild when the source is unchanged (optimisation #1).
        if swift_hash is not None and (result.returncode == 0 or bool(exported_paths)):
            import contextlib

            with contextlib.suppress(OSError):
                hash_path.write_text(swift_hash, encoding="utf-8")

        return UICapabilityResult(
            success=result.returncode == 0 or bool(exported_paths),
            output_path=first_path,
            error=result.stderr or None if has_error else None,
            metadata={
                "command": " ".join(command),
                "exit_code": result.returncode,
                "exported_paths": [str(p) for p in exported_paths],
                "stdout_snippet": _truncate_stdout(result.stdout),
                "xcresult_path": str(xcresult_path),
            },
        )

    def _compute_swift_hash(self, only_testing: str | None) -> str | None:
        """Return a SHA-256 hex digest of all .swift files in the test target dir.

        Used as the cache key for skipping xcodebuild when the test target's
        source hasn't changed since the last bundle. Returns None when the
        target directory can't be located (e.g. only_testing is None for a
        backward-compat single-bundle project).

        Args:
            only_testing: Test target name (e.g. "STRAPTUITests").

        Returns:
            64-char hex SHA-256, or None if hashing is not applicable.
        """
        if not only_testing:
            return None
        target_dir = self.project_dir / only_testing
        if not target_dir.is_dir():
            return None
        import hashlib

        h = hashlib.sha256()
        # Sort for determinism. Hash the relative path + content of each .swift
        # so renames invalidate the cache too.
        for swift in sorted(target_dir.rglob("*.swift")):
            try:
                h.update(str(swift.relative_to(target_dir)).encode("utf-8"))
                h.update(b"\0")
                h.update(swift.read_bytes())
                h.update(b"\0")
            except OSError:
                return None
        return h.hexdigest()

    # @spec FR-005: launch_arguments injection — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-005  # noqa: E501
    def run_flow(
        self,
        destination: str | None = None,
        test_scheme: str | None = None,
        launch_arguments: list[str] | None = None,
        platform: str | None = None,
    ) -> UICapabilityResult:
        """Run the full XCUITest suite and report pass/fail.

        Args:
            destination: Xcode destination string.
            test_scheme: Xcode scheme name (auto-detected if None).
            launch_arguments: Arguments passed via XCUI_LAUNCH_ARGS env var.

        Returns:
            Result indicating pass/fail with failed test names if any.
        """
        if not self._check_macos():
            return UICapabilityResult(
                success=False,
                error=_MACOS_SKIP_ERROR,
                metadata={"skipped": True},
            )

        if self._get_toolchain_path() is None:
            return UICapabilityResult(
                success=False,
                error=_XCODE_MISSING_ERROR,
            )

        if not self._check_xcode_license():
            return UICapabilityResult(
                success=False,
                error=_LICENSE_ERROR,
            )

        # Auto-detect destination when surfaces.yaml didn't supply one (same logic
        # as capture_screenshot — see comment there).
        if destination is None:
            detected = self._autodetect_destination(platform=platform or "ios")
            if detected is not None:
                destination = detected
            else:
                destination = (
                    "platform=watchOS Simulator,name=Apple Watch"
                    if (platform or "").lower() == "watchos"
                    else "platform=iOS Simulator,name=iPhone 16"
                )

        # Same id→name normalization as capture_screenshot.
        destination = self._normalize_destination_by_id(destination)

        with tempfile.TemporaryDirectory() as tmp_dir:
            xcresult_path = Path(tmp_dir) / "flow_result.xcresult"
            command = self._build_xcodebuild_command(
                destination=destination,
                test_scheme=test_scheme,
                xcresult_path=xcresult_path,
            )
            env = self._build_env(launch_arguments)

            try:
                result = subprocess.run(
                    command,
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    timeout=FLOW_TIMEOUT_SECONDS,
                    env=env,
                    check=False,
                )
            except subprocess.TimeoutExpired as error:
                return UICapabilityResult(
                    success=False,
                    error=f"XCUITest flow timed out after {error.timeout}s",
                    metadata={"timeout": error.timeout, "command": " ".join(command)},
                )
            except OSError as error:
                return UICapabilityResult(
                    success=False,
                    error=f"Failed to execute xcodebuild: {error}",
                    metadata={"command": " ".join(command)},
                )

            combined_output = result.stdout + result.stderr
            combined_lower = combined_output.lower()
            if "license" in combined_lower and "not been accepted" in combined_lower:
                return UICapabilityResult(
                    success=False,
                    error=_LICENSE_ERROR,
                    metadata={"command": " ".join(command)},
                )

            success = result.returncode == 0
            # Parse failed test names from xcodebuild output
            failed_tests = self._extract_failed_tests(combined_output)

            return UICapabilityResult(
                success=success,
                error=(
                    f"Tests failed: {', '.join(failed_tests)}"
                    if failed_tests
                    else (result.stderr or None if not success else None)
                ),
                metadata={
                    "command": " ".join(command),
                    "exit_code": result.returncode,
                    "failed_tests": failed_tests,
                    "stdout_snippet": _truncate_stdout(result.stdout),
                },
            )

    def compare_baseline(
        self,
        baseline: str,
        screenshot: str,
        threshold: float = DEFAULT_COMPARE_THRESHOLD,
    ) -> UICapabilityResult:
        """Compare a screenshot against a baseline image using pixelmatch.

        Delegates to the Feature 010 pixelmatch-cli.js script, reusing the
        same comparison engine as the web runner.

        Args:
            baseline: Baseline PNG path, absolute or project-relative.
            screenshot: Screenshot PNG path, absolute or project-relative.
            threshold: Pixel diff tolerance (Feature 010 default: 0.05).

        Returns:
            Result containing the diff path when the script creates one.
        """
        # @spec FR-006: compare_baseline reuses pixelmatch — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-001  # noqa: E501
        script_path = self.project_dir / "scripts" / "pixelmatch-cli.js"
        if not script_path.exists():
            return UICapabilityResult(
                success=False,
                error=f"Feature 010 pixelmatch script not found: {script_path}",
                metadata={"script_path": str(script_path)},
            )

        baseline_path = _resolve_project_path(self.project_dir, baseline)
        screenshot_path = _resolve_project_path(self.project_dir, screenshot)

        if not baseline_path.exists():
            return UICapabilityResult(
                success=False,
                error=f"Baseline PNG not found: {baseline_path}",
                metadata={"baseline_path": str(baseline_path)},
            )

        if not screenshot_path.exists():
            return UICapabilityResult(
                success=False,
                error=f"Screenshot PNG not found: {screenshot_path}",
                metadata={"screenshot_path": str(screenshot_path)},
            )

        command = [
            "node",
            str(script_path),
            str(baseline_path),
            str(screenshot_path),
            str(threshold),
        ]
        try:
            result = subprocess.run(
                command,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=COMPARE_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            return UICapabilityResult(
                success=False,
                error=f"Pixelmatch comparison timed out after {error.timeout}s",
                metadata={"timeout": error.timeout, "command": " ".join(command)},
            )
        except OSError as error:
            return UICapabilityResult(
                success=False,
                error=f"Failed to execute pixelmatch comparison: {error}",
                metadata={"command": " ".join(command)},
            )

        diff_path = self.project_dir / f"{baseline_path.stem}.diff.png"
        return UICapabilityResult(
            success=result.returncode == 0,
            output_path=diff_path if diff_path.exists() else None,
            error=result.stderr or None if result.returncode > 1 else None,
            metadata={
                "command": " ".join(command),
                "exit_code": result.returncode,
                "threshold": threshold,
                "baseline": str(baseline_path),
                "screenshot": str(screenshot_path),
                "diff_produced": diff_path.exists(),
                "stdout_snippet": _truncate_stdout(result.stdout),
            },
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_xcodeproj(self) -> Path | None:
        """Return the first .xcodeproj or .xcworkspace under project_dir, or None."""
        if not self.project_dir.exists():
            return None
        # .xcworkspace wins over .xcodeproj when both are present (workspace is
        # what xcodebuild expects in CocoaPods/SPM-mixed projects).
        workspaces = sorted(self.project_dir.glob("*.xcworkspace"))
        if workspaces:
            return workspaces[0]
        projects = sorted(self.project_dir.glob("*.xcodeproj"))
        return projects[0] if projects else None

    def _list_shared_schemes(self, xcodeproj: Path) -> list[str]:
        """Read scheme names from `<xcodeproj>/xcshareddata/xcschemes/*.xcscheme`."""
        schemes_dir = xcodeproj / "xcshareddata" / "xcschemes"
        if not schemes_dir.is_dir():
            return []
        return sorted(p.stem for p in schemes_dir.glob("*.xcscheme"))

    def _autodetect_scheme(
        self, xcodeproj: Path, platform: str | None = None
    ) -> str | None:
        """Pick the most likely scheme for the given platform from shared schemes.

        Args:
            xcodeproj: Path to .xcodeproj or .xcworkspace.
            platform: 'ios' or 'watchos' to filter; None returns the first scheme.

        Returns:
            Scheme name, or None when no suitable scheme is found.
        """
        schemes = self._list_shared_schemes(xcodeproj)
        if not schemes:
            return None
        if platform == "watchos":
            for scheme in schemes:
                lower = scheme.lower()
                if "watch" in lower:
                    return scheme
            return None
        if platform == "ios":
            # Prefer non-watch schemes for iOS; fallback to first available.
            for scheme in schemes:
                if "watch" not in scheme.lower():
                    return scheme
        return schemes[0]

    def _build_xcodebuild_command(
        self,
        destination: str,
        test_scheme: str | None,
        xcresult_path: Path,
        project: str | None = None,
        workspace: str | None = None,
        only_testing: str | None = None,
    ) -> list[str]:
        """Assemble the xcodebuild test command.

        Args:
            destination: Xcode destination string.
            test_scheme: Scheme to test (uses -scheme flag if provided).
            xcresult_path: Path for the output .xcresult bundle.
            project: Optional .xcodeproj path (relative or absolute).
            workspace: Optional .xcworkspace path (takes precedence over project).
            only_testing: Restrict the run to a specific test bundle/method via
                xcodebuild's `-only-testing:` flag. Required when a scheme has
                multiple targets across platforms (e.g. iOS UITests + watchOS
                UITests in the same scheme): otherwise xcodebuild tries to run
                the wrong-platform bundles and the whole invocation fails.

        Returns:
            Command list suitable for subprocess.run.
        """
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

    # @spec FR-005: launch_arguments injection — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-005  # noqa: E501
    def _build_env(self, launch_arguments: list[str] | None) -> dict[str, str] | None:
        """Build the environment dict for xcodebuild, injecting XCUI_LAUNCH_ARGS.

        Args:
            launch_arguments: Optional list of strings to encode as JSON in
                XCUI_LAUNCH_ARGS so the XCUITest harness can read them.

        Returns:
            Environment dict with XCUI_LAUNCH_ARGS set, or None if no args.
        """
        if not launch_arguments:
            return None
        import os

        env = os.environ.copy()
        env["XCUI_LAUNCH_ARGS"] = json.dumps(launch_arguments)
        return env

    def _extract_failed_tests(self, output: str) -> list[str]:
        """Parse xcodebuild output to find failing test names.

        Args:
            output: Combined stdout + stderr from xcodebuild.

        Returns:
            List of failing test identifiers (e.g. "MyTests/testFoo").
        """
        failed: list[str] = []
        for line in output.splitlines():
            # xcodebuild prints "Test Case '-[ClassName testName]' failed"
            if "failed (" in line.lower() and "test case" in line.lower():
                # Extract test name between brackets
                start = line.find("[")
                end = line.find("]")
                if start != -1 and end != -1:
                    test_id = line[start + 1 : end].replace(" ", "/")
                    failed.append(test_id)
        return failed


def load_xcuitest_runner_manifest() -> dict[str, Any]:
    """Load the built-in iOS/watchOS runner manifest from disk.

    Returns:
        Parsed YAML content for `livespec/ui-runners/ios.yaml`.

    Raises:
        FileNotFoundError: If the built-in manifest cannot be found.
        yaml.YAMLError: If the manifest contents are not valid YAML.
    """
    manifest_path = xcuitest_runner_manifest_path()
    if not manifest_path.exists():
        raise FileNotFoundError(f"iOS runner manifest not found: {manifest_path}")

    with manifest_path.open() as manifest_file:
        manifest = yaml.safe_load(manifest_file)
    return cast(dict[str, Any], manifest)


def detect_xcuitest_runner(project_dir: Path | str) -> bool:
    """Detect whether a project should use the built-in iOS/watchOS runner.

    Args:
        project_dir: Project root to inspect.

    Returns:
        `True` when the iOS runner should match the project, otherwise `False`.
    """
    return XCUITestRunnerHandler(project_dir).detect()
