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
SCREENSHOT_TIMEOUT_SECONDS = 300
FLOW_TIMEOUT_SECONDS = 600
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
        for entry in self.project_dir.iterdir() if self.project_dir.exists() else []:
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
            if data.get("_type", {}).get("_name") == "ActionTestAttachment":
                attachments.append(data)
            for value in data.values():
                self._extract_attachments_from_xcresult_json(value, attachments)
        elif isinstance(data, list):
            for item in data:
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

        # Step 1: get JSON manifest
        try:
            result = subprocess.run(
                [
                    "xcrun",
                    "xcresulttool",
                    "get",
                    "--path",
                    str(bundle_path),
                    "--format",
                    "json",
                ],
                capture_output=True,
                text=True,
                timeout=XCRESULTTOOL_TIMEOUT_SECONDS,
                check=False,
            )
            data = json.loads(result.stdout or "{}")
        except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError):
            # EC-002: corrupted bundle — return empty partial result without crash
            return exported

        # Step 2: find all attachments
        attachments = self._extract_attachments_from_xcresult_json(data)

        # Step 3: export each attachment
        for i, att in enumerate(attachments):
            name = att.get("name", {}).get("_value", f"screenshot_{i}")
            payload_ref = att.get("payloadRef", {}).get("id", {}).get("_value")
            if not payload_ref:
                continue

            try:
                with tempfile.TemporaryDirectory() as tmp_dir:
                    subprocess.run(
                        [
                            "xcrun",
                            "xcresulttool",
                            "export",
                            "--path",
                            str(bundle_path),
                            "--id",
                            payload_ref,
                            "--output-path",
                            tmp_dir,
                            "--type",
                            "file",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=False,
                    )
                    # Find exported file
                    for exported_file in Path(tmp_dir).iterdir():
                        suffix = exported_file.suffix.lower()
                        if suffix not in {".heic", ".png", ".jpg", ".jpeg"}:
                            continue
                        png_name = f"{name}.png"
                        png_path = dest_dir / png_name
                        if suffix == ".heic":
                            if self._convert_heic_to_png(exported_file, png_path):
                                exported.append(png_path)
                        else:
                            import shutil

                            shutil.copy2(exported_file, png_path)
                            exported.append(png_path)
            except (OSError, subprocess.TimeoutExpired):
                # EC-002: skip one bad attachment, continue with rest
                continue

        return exported

    # ------------------------------------------------------------------
    # Public capabilities
    # ------------------------------------------------------------------

    # @spec FR-005: launch_arguments injection — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-005  # noqa: E501
    def capture_screenshot(
        self,
        screen: str = "main",
        destination: str = "platform=iOS Simulator,name=iPhone 16",
        test_scheme: str | None = None,
        launch_arguments: list[str] | None = None,
    ) -> UICapabilityResult:
        """Run xcodebuild test, extract screenshots from .xcresult bundle.

        Args:
            screen: Screen identifier used for output naming.
            destination: Xcode destination string.
            test_scheme: Xcode scheme name (auto-detected if None).
            launch_arguments: Arguments passed as XCUI_LAUNCH_ARGS env var.

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

        with tempfile.TemporaryDirectory() as tmp_dir:
            xcresult_path = Path(tmp_dir) / "result.xcresult"
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
            return UICapabilityResult(
                success=result.returncode == 0 or bool(exported_paths),
                output_path=first_path,
                error=result.stderr or None if has_error else None,
                metadata={
                    "command": " ".join(command),
                    "exit_code": result.returncode,
                    "exported_paths": [str(p) for p in exported_paths],
                    "stdout_snippet": _truncate_stdout(result.stdout),
                },
            )

    # @spec FR-005: launch_arguments injection — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-005  # noqa: E501
    def run_flow(
        self,
        destination: str = "platform=iOS Simulator,name=iPhone 16",
        test_scheme: str | None = None,
        launch_arguments: list[str] | None = None,
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

    def _build_xcodebuild_command(
        self,
        destination: str,
        test_scheme: str | None,
        xcresult_path: Path,
    ) -> list[str]:
        """Assemble the xcodebuild test command.

        Args:
            destination: Xcode destination string.
            test_scheme: Scheme to test (uses -scheme flag if provided).
            xcresult_path: Path for the output .xcresult bundle.

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
