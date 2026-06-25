# LiveSpec traceability anchors
# @spec(AC-007)
# @spec(AC-013)
# @spec(FR-001)
# @spec(FR-002)
# @spec(FR-003)
# @spec(FR-004)
# @spec(FR-005)
# @spec(FR-006)
# @spec(FR-008)

"""iOS/watchOS UI runner support for XCUITest-based projects."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]  # PyYAML is a runtime dependency without stubs.

DEFAULT_COMPARE_THRESHOLD = 0.05
SCREENSHOT_TIMEOUT_SECONDS = 1200
FLOW_TIMEOUT_SECONDS = 1800
SIMULATOR_BOOT_TIMEOUT_SECONDS = 120
XCRESULTTOOL_TIMEOUT_SECONDS = 60

_MACOS_SKIP_ERROR = "iOS UI runner requires macOS — skipped on non-macOS hosts"
_XCODE_MISSING_ERROR = (
    "Xcode not installed. Install from App Store or https://developer.apple.com/xcode/"
)
_LICENSE_ERROR = "Xcode license not accepted. Run: sudo xcodebuild -license accept"


@dataclass
class UICapabilityResult:
    """Describe the outcome of one UI runner capability invocation."""

    success: bool
    output_path: Path | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=lambda: cast(dict[str, Any], {}))


def xcuitest_runner_manifest_path() -> Path:
    """Return the filesystem path to the built-in iOS/watchOS runner manifest."""
    return Path(__file__).resolve().parent.parent / "livespec" / "ui-runners" / "ios.yaml"


class XCUITestRunnerHandler:
    """Handle UI runner capabilities for XCUITest iOS/watchOS projects."""

    def __init__(self, project_dir: Path | str) -> None:
        """Initialize the handler with a project root."""
        self.project_dir = Path(project_dir).resolve()

    def _check_macos(self) -> bool:
        """Return True when running on macOS."""
        from validator.ios_simulator_core import check_macos

        return check_macos()

    def _get_toolchain_path(self) -> str | None:
        """Return path to xcodebuild, or None if not found."""
        from validator.ios_simulator_core import get_toolchain_path

        return get_toolchain_path()

    def _check_xcode_license(self) -> bool:
        """Return True if the Xcode license has been accepted."""
        from validator.ios_simulator_core import check_xcode_license

        return check_xcode_license()

    def preflight_message(self) -> str:
        """Return an actionable diagnostic for the dispatcher BLOCKED line."""
        import platform

        if not self._check_macos():
            return f"XCUITest runner requires macOS host (current: {platform.system().lower()})"
        if self._get_toolchain_path() is None:
            return "xcrun simctl not found — install Xcode CLI tools"
        if not self._check_xcode_license():
            return _LICENSE_ERROR
        return ""

    def detect(self) -> bool:
        """Check whether the project is an Xcode/Swift project."""
        if (self.project_dir / "Package.swift").exists():
            return True
        if not self.project_dir.exists():
            return False
        return any(
            entry.suffix in {".xcodeproj", ".xcworkspace"} for entry in self.project_dir.iterdir()
        )

    def _list_simulators(self) -> dict[str, Any]:
        """Return parsed output of `xcrun simctl list devices --json`."""
        from validator.ios_simulator_core import list_simulators

        return list_simulators()

    def _find_simulator_udid(
        self, destination_name: str, platform_filter: str = "iOS"
    ) -> str | None:
        """Find the UDID for a named simulator matching the given platform."""
        from validator.ios_simulator_core import find_simulator_udid

        return find_simulator_udid(destination_name, platform_filter)

    def _boot_simulator(self, udid: str, timeout: int = SIMULATOR_BOOT_TIMEOUT_SECONDS) -> bool:
        """Boot a simulator if it is not already booted."""
        from validator.ios_simulator_core import boot_simulator

        return boot_simulator(udid, timeout)

    def _wait_simulator_ready(
        self, udid: str, timeout: int = SIMULATOR_BOOT_TIMEOUT_SECONDS
    ) -> bool:
        """Wait for a simulator to reach ready state."""
        from validator.ios_simulator_core import wait_simulator_ready

        return wait_simulator_ready(udid, timeout)

    def _filter_destinations_by_platform(
        self, destinations: list[dict[str, Any]], platform: str = "ios"
    ) -> list[dict[str, Any]]:
        """Filter a destinations list to those matching the given platform."""
        from validator.ios_simulator_core import filter_destinations_by_platform

        return filter_destinations_by_platform(destinations, platform)

    def _autodetect_destination(self, platform: str = "ios") -> str | None:
        """Pick the first available simulator destination for the given platform."""
        from validator.ios_simulator_core import autodetect_destination

        return autodetect_destination(platform, self._list_simulators())

    def _friendly_destination_id(self, destination: str) -> str:
        """Derive a stable, human-readable screenshot folder name."""
        from validator.ios_simulator_core import friendly_destination_id

        return friendly_destination_id(destination)

    def _convert_heic_to_png(self, heic_path: Path, png_path: Path) -> bool:
        """Convert a HEIC image to PNG using the macOS `sips` utility."""
        from validator.ios_xcresult_core import convert_heic_to_png

        return convert_heic_to_png(heic_path, png_path)

    def _extract_attachments_from_xcresult_json(
        self, data: Any, attachments: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """Recursively extract ActionTestAttachment nodes from xcresulttool JSON."""
        from validator.ios_xcresult_core import extract_attachments_from_xcresult_json

        return extract_attachments_from_xcresult_json(data, attachments)

    def _parse_xcresult(
        self, bundle_path: Path, output_dir: Path, destination_id: str
    ) -> list[Path]:
        """Extract screenshots from an .xcresult bundle."""
        from validator.ios_xcresult_core import parse_xcresult

        return parse_xcresult(bundle_path, output_dir, destination_id)

    def _iter_manifest_attachments(self, manifest: object) -> list[dict[str, str]]:
        """Flatten `xcresulttool export attachments` manifest into one list."""
        from validator.ios_xcresult_core import iter_manifest_attachments

        return iter_manifest_attachments(manifest)

    @staticmethod
    def _strip_attachment_suffix(suggested_name: str) -> str:
        """Recover the user-set attachment name from Xcode's filename."""
        from validator.ios_xcresult_core import strip_attachment_suffix

        return strip_attachment_suffix(suggested_name)

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
        output_path: Path | None = None,
        feature_slug: str | None = None,
        run_id: str | None = None,
    ) -> UICapabilityResult:
        """Run xcodebuild test and extract screenshots from .xcresult bundle."""
        from validator.ios_runner_core import capture_screenshot

        args = (self, screen, destination, test_scheme, launch_arguments, project, workspace)
        return capture_screenshot(*args, platform, only_testing, output_path, feature_slug, run_id)

    def _compute_swift_hash(self, only_testing: str | None) -> str | None:
        """Return a SHA-256 hex digest of all .swift files in the test target dir."""
        from validator.ios_hash_core import compute_swift_hash

        return compute_swift_hash(self.project_dir, only_testing)

    def run_flow(
        self,
        destination: str | None = None,
        test_scheme: str | None = None,
        launch_arguments: list[str] | None = None,
        platform: str | None = None,
    ) -> UICapabilityResult:
        """Run the full XCUITest suite and report pass/fail."""
        from validator.ios_runner_core import run_flow

        return run_flow(self, destination, test_scheme, launch_arguments, platform)

    def compare_baseline(
        self,
        baseline: str,
        screenshot: str,
        threshold: float = DEFAULT_COMPARE_THRESHOLD,
    ) -> UICapabilityResult:
        """Compare a screenshot against a baseline image using pixelmatch."""
        from validator.ios_hash_core import compare_baseline

        return compare_baseline(self.project_dir, baseline, screenshot, threshold)

    def _find_xcodeproj(self) -> Path | None:
        """Return the first .xcodeproj or .xcworkspace under project_dir."""
        from validator.ios_simulator_core import find_xcodeproj

        return find_xcodeproj(self.project_dir)

    def _list_shared_schemes(self, xcodeproj: Path) -> list[str]:
        """Read scheme names from `<xcodeproj>/xcshareddata/xcschemes/*.xcscheme`."""
        from validator.ios_simulator_core import list_shared_schemes

        return list_shared_schemes(xcodeproj)

    def _autodetect_scheme(self, xcodeproj: Path, platform: str | None = None) -> str | None:
        """Pick the most likely scheme for the given platform from shared schemes."""
        from validator.ios_simulator_core import autodetect_scheme

        return autodetect_scheme(xcodeproj, platform)

    def _build_xcodebuild_command(
        self,
        destination: str,
        test_scheme: str | None,
        xcresult_path: Path,
        project: str | None = None,
        workspace: str | None = None,
        only_testing: str | None = None,
    ) -> list[str]:
        """Assemble the xcodebuild test command."""
        from validator.ios_simulator_core import build_xcodebuild_command

        return build_xcodebuild_command(
            destination, test_scheme, xcresult_path, project, workspace, only_testing
        )

    def _build_env(self, launch_arguments: list[str] | None) -> dict[str, str] | None:
        """Build the environment dict for xcodebuild, injecting XCUI_LAUNCH_ARGS."""
        from validator.ios_simulator_core import build_env

        return build_env(launch_arguments)

    def _extract_failed_tests(self, output: str) -> list[str]:
        """Parse xcodebuild output to find failing test names."""
        from validator.ios_simulator_core import extract_failed_tests

        return extract_failed_tests(output)


def load_xcuitest_runner_manifest() -> dict[str, Any]:
    """Load the built-in iOS/watchOS runner manifest from disk."""
    manifest_path = xcuitest_runner_manifest_path()
    if not manifest_path.exists():
        raise FileNotFoundError(f"iOS runner manifest not found: {manifest_path}")
    with manifest_path.open() as manifest_file:
        manifest = yaml.safe_load(manifest_file)
    return cast(dict[str, Any], manifest)


def detect_xcuitest_runner(project_dir: Path | str) -> bool:
    """Detect whether a project should use the built-in iOS/watchOS runner."""
    return XCUITestRunnerHandler(project_dir).detect()
