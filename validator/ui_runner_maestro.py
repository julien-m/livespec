"""Android UI runner support for Maestro YAML flow-based projects.

This module provides an orchestrator around adb/emulator/maestro so the
validator can detect an Android Gradle project and invoke screenshot
capture, flow execution, and baseline comparison for Android emulators.
"""

# @spec FR-001: Android/Maestro runner manifest — .specs/features/031-ui-runner-android/spec.md#fr-001  # noqa: E501
# @spec FR-002: AVD orchestration — .specs/features/031-ui-runner-android/spec.md#fr-002
# @spec FR-003: Maestro screenshot extraction — .specs/features/031-ui-runner-android/spec.md#fr-003  # noqa: E501
# @spec FR-004: adb fallback screenshot — .specs/features/031-ui-runner-android/spec.md#fr-004
# @spec FR-005: device override + per-device baselines — .specs/features/031-ui-runner-android/spec.md#fr-005  # noqa: E501
# @spec FR-006: Wear OS experimental warning — .specs/features/031-ui-runner-android/spec.md#fr-006

from __future__ import annotations

import os
import subprocess
import time
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]

DEFAULT_COMPARE_THRESHOLD = 0.05
FLOW_TIMEOUT_SECONDS = 300
COMPARE_TIMEOUT_SECONDS = 60
AVD_BOOT_TIMEOUT_SECONDS = 90
AVD_BOOT_POLL_INTERVAL = 5
SCREENCAP_REMOTE_PATH = "/sdcard/livespec_screen.png"
STDOUT_SNIPPET_LIMIT = 200

_ANDROID_SDK_SKIP_ERROR = (
    "Android UI runner requires Android SDK — skipped on this host. "
    "Install: https://developer.android.com/studio or set ANDROID_HOME."
)
_MAESTRO_MISSING_ERROR = (
    "Maestro CLI not installed. "
    "Install: curl -Ls https://get.maestro.mobile.dev | bash"
)
_WEAROS_EXPERIMENTAL_WARNING = (
    "Wear OS support is experimental in Maestro — proceed with caution"
)
_NO_FLOWS_ERROR = (
    "No Maestro flows found. "
    "Create YAML flows in .specs/maestro/ or maestro/ directory."
)
_ADB_NO_DEVICES_ERROR = (
    "ADB sees no devices — emulator may not be running. "
    "Check ANDROID_HOME and emulator path, or run avdmanager to list available AVDs."
)
_AVD_BOOT_TIMEOUT_ERROR = "Emulator failed to reach adb-ready state within {timeout}s."


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


# @spec FR-001: Android/Maestro manifest path helper — .specs/features/031-ui-runner-android/spec.md#fr-001  # noqa: E501
def maestro_runner_manifest_path() -> Path:
    """Return the filesystem path to the built-in Android runner manifest.

    Returns:
        Absolute path to `livespec/ui-runners/android.yaml`.
    """
    return (
        Path(__file__).resolve().parent.parent / "livespec" / "ui-runners" / "android.yaml"
    )


# @spec FR-001: Android runner class — .specs/features/031-ui-runner-android/spec.md#fr-001
class MaestroRunnerHandler:
    """Handle UI runner capabilities for Android Maestro YAML flow projects."""

    def __init__(self, project_dir: Path | str) -> None:
        """Initialize the handler.

        Args:
            project_dir: Project root containing Android project assets.
        """
        self.project_dir = Path(project_dir).resolve()

    # ------------------------------------------------------------------
    # Platform / toolchain guards
    # ------------------------------------------------------------------

    # @spec FR-002: Android SDK detection — .specs/features/031-ui-runner-android/spec.md#fr-002
    def _check_android_sdk(self) -> bool:
        """Return True when Android SDK is available on this host.

        Checks ANDROID_HOME or ANDROID_SDK_ROOT environment variable and
        verifies the directory exists.
        """
        for var in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
            sdk_path = os.environ.get(var)
            if sdk_path and Path(sdk_path).exists():
                return True
        return False

    # @spec FR-002: Maestro CLI detection — .specs/features/031-ui-runner-android/spec.md#fr-002
    def _check_maestro(self) -> bool:
        """Return True when the Maestro CLI binary is available on PATH."""
        try:
            result = subprocess.run(
                ["which", "maestro"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            return result.returncode == 0 and bool(result.stdout.strip())
        except (OSError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    # @spec FR-013: Maestro preflight diagnostics — .specs/features/037-test-multi-runner-integration/spec.md#fr-013  # noqa: E501
    def preflight_message(self) -> str:
        """Return an actionable diagnostic for the dispatcher BLOCKED line.

        Returns:
            Empty string when the toolchain is ready; otherwise a hint
            covering the missing piece (CLI, SDK, emulator).
        """
        if not self._check_maestro():
            return (
                "maestro CLI not on PATH — install: "
                "curl -Ls 'https://get.maestro.mobile.dev' | bash"
            )
        if not self._check_android_sdk():
            return (
                "Android SDK not found — set ANDROID_HOME or install Android Studio"
            )
        if self._get_running_emulator() is None:
            return (
                "no Android emulator available — start one with "
                "'emulator -avd <name>'"
            )
        return ""

    # ------------------------------------------------------------------
    # Project detection
    # ------------------------------------------------------------------

    # @spec FR-001: Android project detection — .specs/features/031-ui-runner-android/spec.md#fr-001
    def detect(self) -> bool:
        """Check whether the project is an Android Gradle / Maestro project.

        Returns:
            `True` when the project contains `build.gradle`, `build.gradle.kts`,
            `AndroidManifest.xml`, or a `maestro/` / `.specs/maestro/` directory.
        """
        if not self.project_dir.exists():
            return False

        # Gradle build files
        for marker in ("build.gradle", "build.gradle.kts", "AndroidManifest.xml"):
            if (self.project_dir / marker).exists():
                return True

        # Maestro flow directories
        return (
            (self.project_dir / "maestro").exists()
            or (self.project_dir / ".specs" / "maestro").exists()
        )

    # ------------------------------------------------------------------
    # AVD management
    # ------------------------------------------------------------------

    # @spec FR-002: AVD listing — .specs/features/031-ui-runner-android/spec.md#fr-002
    def _list_avds(self) -> list[str]:
        """Return a list of available AVD names from avdmanager.

        Returns:
            List of AVD name strings; empty list on error.
        """
        try:
            result = subprocess.run(
                ["avdmanager", "list", "avd"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if result.returncode != 0:
                return []
            avds: list[str] = []
            for line in result.stdout.splitlines():
                stripped = line.strip()
                if stripped.startswith("Name:"):
                    avds.append(stripped[len("Name:"):].strip())
            return avds
        except (OSError, FileNotFoundError, subprocess.TimeoutExpired):
            return []

    # @spec FR-002: running emulator detection — .specs/features/031-ui-runner-android/spec.md#fr-002  # noqa: E501
    def _get_running_emulator(self) -> str | None:
        """Return the adb serial of a running emulator, or None if none found.

        Returns:
            Serial string like 'emulator-5554', or None.
        """
        try:
            result = subprocess.run(
                ["adb", "devices"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            if result.returncode != 0:
                return None
            for line in result.stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2 and parts[0].startswith("emulator-") and parts[1] == "device":
                    return parts[0]
        except (OSError, FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return None

    # @spec FR-002: AVD boot — .specs/features/031-ui-runner-android/spec.md#fr-002
    def _boot_avd(self, avd_name: str) -> None:
        """Start the named AVD in headless (no-window) mode.

        Args:
            avd_name: Name of the Android Virtual Device to boot.
        """
        subprocess.Popen(
            ["emulator", "-avd", avd_name, "-no-window"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    # @spec FR-002: AVD boot readiness polling — .specs/features/031-ui-runner-android/spec.md#fr-002  # noqa: E501
    def _wait_for_boot(
        self,
        serial: str,
        timeout: int = AVD_BOOT_TIMEOUT_SECONDS,
        poll_interval: float = AVD_BOOT_POLL_INTERVAL,
    ) -> bool:
        """Wait for the AVD identified by `serial` to reach boot_completed state.

        Polls `adb -s <serial> shell getprop sys.boot_completed` every
        `poll_interval` seconds until the value is '1' or `timeout` expires.

        Args:
            serial: ADB device serial (e.g. 'emulator-5554').
            timeout: Maximum seconds to wait.
            poll_interval: Seconds between polls.

        Returns:
            True when boot_completed=1, False on timeout.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                result = subprocess.run(
                    ["adb", "-s", serial, "shell", "getprop", "sys.boot_completed"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                if result.returncode == 0 and result.stdout.strip() == "1":
                    return True
            except (OSError, subprocess.TimeoutExpired):
                pass
            time.sleep(poll_interval)
        return False

    # @spec FR-002: combined boot + wait — .specs/features/031-ui-runner-android/spec.md#fr-002
    def _boot_avd_and_wait(
        self,
        avd_name: str,
        timeout: int = AVD_BOOT_TIMEOUT_SECONDS,
    ) -> bool:
        """Boot the named AVD and wait until it is adb-ready.

        Args:
            avd_name: AVD name to launch.
            timeout: Max seconds to wait for readiness.

        Returns:
            True if the emulator became ready; False on timeout or error.
        """
        self._boot_avd(avd_name)
        # Brief pause to allow emulator process to start
        time.sleep(2)
        # Wait for an emulator serial to appear
        deadline = time.monotonic() + timeout
        serial: str | None = None
        while time.monotonic() < deadline:
            serial = self._get_running_emulator()
            if serial:
                break
            time.sleep(2)

        if serial is None:
            return False

        remaining = int(deadline - time.monotonic())
        return self._wait_for_boot(serial, timeout=max(remaining, 10))

    # ------------------------------------------------------------------
    # AVD selection
    # ------------------------------------------------------------------

    # @spec FR-005: AVD selection with alphabetical tie-breaking — .specs/features/031-ui-runner-android/spec.md#fr-005  # noqa: E501
    def _select_avd(self, avds: list[str], preferred: str) -> str | None:
        """Select an AVD from a list based on a preferred name or prefix.

        Exact match wins; if no exact match, return the first (alphabetically
        sorted) AVD whose name contains `preferred` (EC-001 tie-breaking).

        Args:
            avds: List of available AVD names.
            preferred: Exact name or prefix/substring to match.

        Returns:
            Matched AVD name string, or None if nothing matches.
        """
        if preferred in avds:
            return preferred
        # Substring/prefix match — sort for deterministic EC-001 behaviour
        matches = sorted(avd for avd in avds if preferred in avd)
        return matches[0] if matches else None

    # ------------------------------------------------------------------
    # Flow discovery
    # ------------------------------------------------------------------

    # @spec FR-003: Maestro flow discovery — .specs/features/031-ui-runner-android/spec.md#fr-003
    def _find_flows(self) -> list[Path]:
        """Return sorted list of YAML flow files under .specs/maestro/ or maestro/.

        Returns:
            Sorted list of YAML file Paths; empty list if no flows found.
        """
        for candidate in (
            self.project_dir / ".specs" / "maestro",
            self.project_dir / "maestro",
        ):
            if candidate.is_dir():
                flows = sorted(candidate.glob("*.yaml"))
                if flows:
                    return flows
        return []

    # ------------------------------------------------------------------
    # Screenshot extraction
    # ------------------------------------------------------------------

    # @spec FR-003: Maestro screenshot extraction — .specs/features/031-ui-runner-android/spec.md#fr-003  # noqa: E501
    def _find_maestro_screenshots(self, maestro_output_dir: Path) -> list[Path]:
        """Find PNG screenshots emitted by Maestro in the given output directory.

        Args:
            maestro_output_dir: Directory where Maestro writes screenshot PNGs.

        Returns:
            Sorted list of PNG paths; empty list if directory absent or empty.
        """
        if not maestro_output_dir.exists():
            return []
        return sorted(maestro_output_dir.glob("*.png"))

    # @spec FR-004: adb fallback screenshot — .specs/features/031-ui-runner-android/spec.md#fr-004
    def _capture_adb_screenshot(self, serial: str, output_path: Path) -> bool:
        """Capture a screenshot via adb shell screencap and pull to output_path.

        Args:
            serial: ADB device serial (e.g. 'emulator-5554').
            output_path: Local destination path for the PNG file.

        Returns:
            True on success, False on failure.
        """
        try:
            # Step 1: screencap on device
            screencap_result = subprocess.run(
                [
                    "adb", "-s", serial,
                    "shell", "screencap", "-p", SCREENCAP_REMOTE_PATH,
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if screencap_result.returncode != 0:
                return False

            # Step 2: pull from device
            output_path.parent.mkdir(parents=True, exist_ok=True)
            pull_result = subprocess.run(
                ["adb", "-s", serial, "pull", SCREENCAP_REMOTE_PATH, str(output_path)],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            # Step 3: clean up remote file (best-effort)
            subprocess.run(
                ["adb", "-s", serial, "shell", "rm", SCREENCAP_REMOTE_PATH],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            return pull_result.returncode == 0 and output_path.exists()
        except (OSError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    # ------------------------------------------------------------------
    # Baseline path resolution
    # ------------------------------------------------------------------

    # @spec FR-005: per-device baseline path resolution — .specs/features/031-ui-runner-android/spec.md#fr-005  # noqa: E501
    def _resolve_baseline_path(
        self, screen: str, avd_name: str | None = None
    ) -> Path:
        """Resolve the path where a baseline PNG should be stored.

        With device override, path includes the AVD name as a subdirectory.
        Without override, PNGs go directly into .specs/design/screens/.

        Args:
            screen: Screen identifier (stem of the PNG file).
            avd_name: AVD name for per-device path, or None for flat path.

        Returns:
            Absolute path for the PNG file.
        """
        base = self.project_dir / ".specs" / "design" / "screens"
        if avd_name:
            return base / avd_name / f"{screen}.png"
        return base / f"{screen}.png"

    # ------------------------------------------------------------------
    # Output parsing
    # ------------------------------------------------------------------

    # @spec FR-003: Maestro output parsing — .specs/features/031-ui-runner-android/spec.md#fr-003
    def _parse_maestro_result(self, output: str, returncode: int) -> bool:
        """Determine whether a Maestro flow run succeeded.

        Args:
            output: Combined stdout + stderr from `maestro test`.
            returncode: Process exit code.

        Returns:
            True if the flow completed successfully, False otherwise.
        """
        if returncode != 0:
            return False
        output_lower = output.lower()
        return "flow failed" not in output_lower

    # ------------------------------------------------------------------
    # Public capabilities
    # ------------------------------------------------------------------

    # @spec FR-004: run_flow capability — .specs/features/031-ui-runner-android/spec.md#fr-004
    def run_flow(
        self,
        avd_name: str | None = None,
        platform: str = "android",
        fail_fast: bool = False,
        timeout: int = FLOW_TIMEOUT_SECONDS,
    ) -> UICapabilityResult:
        """Run all Maestro flows in .specs/maestro/ and report results.

        Args:
            avd_name: AVD name override (default from manifest if None).
            platform: Platform filter — 'android' (default) or 'wearos'.
            fail_fast: If True, stop on first failed flow.
            timeout: Timeout in seconds for each flow invocation.

        Returns:
            UICapabilityResult indicating pass/fail with per-flow details.
        """
        # EC-006: Missing Android SDK — exit 0 (skipped)
        if not self._check_android_sdk():
            return UICapabilityResult(
                success=False,
                error=_ANDROID_SDK_SKIP_ERROR,
                metadata={"skipped": True},
            )

        # AC-009: Missing Maestro CLI — exit 1 with install hint
        if not self._check_maestro():
            return UICapabilityResult(
                success=False,
                error=_MAESTRO_MISSING_ERROR,
                metadata={"skipped": False},
            )

        # FR-006: Wear OS experimental warning
        if platform.lower() == "wearos":
            warnings.warn(_WEAROS_EXPERIMENTAL_WARNING, UserWarning, stacklevel=2)

        # Discover flows
        flows = self._find_flows()
        if not flows:
            return UICapabilityResult(
                success=False,
                error=_NO_FLOWS_ERROR,
                metadata={"flows_dir": str(self.project_dir / ".specs" / "maestro")},
            )

        # Ensure an emulator is running
        serial = self._get_running_emulator()
        if serial is None:
            effective_avd = avd_name or "Pixel_8_API_35"
            # Validate AVD exists when overriding (FR-005 / AC-008)
            if avd_name:
                available = self._list_avds()
                matched = self._select_avd(available, preferred=avd_name)
                if matched is None:
                    return UICapabilityResult(
                        success=False,
                        error=(
                            f"AVD '{avd_name}' not found. "
                            f"Available AVDs: {', '.join(available) or '(none)'}. "
                            "Create with: avdmanager create avd -n <name> -k <system-image>"
                        ),
                        metadata={"available_avds": available},
                    )
                effective_avd = matched
            booted = self._boot_avd_and_wait(effective_avd)
            if not booted:
                return UICapabilityResult(
                    success=False,
                    error=_AVD_BOOT_TIMEOUT_ERROR.format(timeout=AVD_BOOT_TIMEOUT_SECONDS),
                    metadata={"avd": effective_avd},
                )
            serial = self._get_running_emulator()
            if serial is None:
                return UICapabilityResult(
                    success=False,
                    error=_ADB_NO_DEVICES_ERROR,
                    metadata={"avd": effective_avd},
                )

        # Run flows
        per_flow_results: list[dict[str, Any]] = []
        all_passed = True

        for flow_path in flows:
            flow_name = flow_path.stem
            try:
                result = subprocess.run(
                    ["maestro", "test", str(flow_path)],
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
                combined_output = result.stdout + result.stderr
                passed = self._parse_maestro_result(combined_output, result.returncode)
                per_flow_results.append({
                    "flow": flow_name,
                    "passed": passed,
                    "exit_code": result.returncode,
                    "stdout_snippet": _truncate_stdout(combined_output),
                })
                if not passed:
                    all_passed = False
                    if fail_fast:
                        return UICapabilityResult(
                            success=False,
                            error=f"Flow '{flow_name}' failed (fail_fast=True)",
                            metadata={
                                "flow_results": per_flow_results,
                                "exit_code": result.returncode,
                                "stdout_snippet": _truncate_stdout(combined_output),
                            },
                        )
            except subprocess.TimeoutExpired as exc:
                per_flow_results.append({
                    "flow": flow_name,
                    "passed": False,
                    "error": f"timed out after {exc.timeout}s",
                })
                all_passed = False
                return UICapabilityResult(
                    success=False,
                    error=f"Flow '{flow_name}' timed out after {exc.timeout}s",
                    metadata={"flow_results": per_flow_results, "timeout": exc.timeout},
                )
            except OSError as exc:
                per_flow_results.append({
                    "flow": flow_name,
                    "passed": False,
                    "error": str(exc),
                })
                all_passed = False
                if fail_fast:
                    return UICapabilityResult(
                        success=False,
                        error=f"Failed to execute maestro for flow '{flow_name}': {exc}",
                        metadata={"flow_results": per_flow_results},
                    )

        failed_flows = [r["flow"] for r in per_flow_results if not r.get("passed")]
        return UICapabilityResult(
            success=all_passed,
            error=(
                f"Flows failed: {', '.join(failed_flows)}" if failed_flows else None
            ),
            metadata={
                "flow_results": per_flow_results,
                "serial": serial,
                "total_flows": len(flows),
                "passed_flows": len(flows) - len(failed_flows),
            },
        )

    # @spec FR-003: capture_screenshot capability — .specs/features/031-ui-runner-android/spec.md#fr-003  # noqa: E501
    # @spec FR-002: uniform capture_screenshot(screen) signature — .specs/features/037-test-multi-runner-integration/spec.md#fr-002  # noqa: E501
    def capture_screenshot(
        self,
        screen: str = "main",
        *,
        avd_name: str | None = None,
        platform: str = "android",
        fail_fast: bool = False,
        timeout: int = FLOW_TIMEOUT_SECONDS,
        output_path: Path | None = None,
        feature_slug: str | None = None,
        run_id: str | None = None,
    ) -> UICapabilityResult:
        """Run flows, extract tagged screenshots, fall back to adb screencap.

        ``output_path`` is honoured as the destination directory (when a dir
        is supplied) or as the destination PNG for the first capture (when a
        file path is supplied). Combined with ``feature_slug`` + ``run_id``
        the runner derives the canonical
        ``.specs/features/<slug>/run/<run_id>/android/`` layout, mirroring
        the web runner. When the caller supplies an ``output_path`` under
        ``.specs/design/screens/`` the capture is refused (BLOCKED guard).

        Args:
            screen: Screen identifier (matched against `takeScreenshot:` names).
            avd_name: AVD name override.
            platform: Platform filter.
            fail_fast: Stop on first failed flow.
            timeout: Per-flow timeout in seconds.
            output_path: Optional explicit destination — directory or PNG file.
            feature_slug: Used to derive the canonical run layout when
                ``output_path`` is omitted.
            run_id: Timestamp folder name under ``run/`` for the canonical
                layout.

        Returns:
            UICapabilityResult with output_path pointing to first captured PNG.
        """
        from validator.ui_runner_protocol import (
            RuntimeOutputMisplacedError,
            assert_output_not_in_design_screens,
        )

        if output_path is not None:
            try:
                assert_output_not_in_design_screens(output_path)
            except RuntimeOutputMisplacedError as exc:
                return UICapabilityResult(
                    success=False,
                    error=str(exc),
                    metadata={"guard": "runtime_under_design_screens"},
                )
        elif feature_slug and run_id:
            output_path = (
                self.project_dir
                / ".specs"
                / "features"
                / feature_slug
                / "run"
                / run_id
                / "android"
            )
        # Note: the `missing_output_context` BLOCKED return is deferred
        # until AFTER the SDK / Maestro / emulator capability checks below
        # so operators see capability-missing diagnostics first.
        if not self._check_android_sdk():
            return UICapabilityResult(
                success=False,
                error=_ANDROID_SDK_SKIP_ERROR,
                metadata={"skipped": True},
            )

        if not self._check_maestro():
            return UICapabilityResult(
                success=False,
                error=_MAESTRO_MISSING_ERROR,
                metadata={"skipped": False},
            )

        if platform.lower() == "wearos":
            warnings.warn(_WEAROS_EXPERIMENTAL_WARNING, UserWarning, stacklevel=2)

        flows = self._find_flows()
        if not flows:
            return UICapabilityResult(
                success=False,
                error=_NO_FLOWS_ERROR,
            )

        serial = self._get_running_emulator()
        if serial is None:
            effective_avd = avd_name or "Pixel_8_API_35"
            booted = self._boot_avd_and_wait(effective_avd)
            if not booted:
                return UICapabilityResult(
                    success=False,
                    error=_AVD_BOOT_TIMEOUT_ERROR.format(timeout=AVD_BOOT_TIMEOUT_SECONDS),
                )
            serial = self._get_running_emulator()
            if serial is None:
                return UICapabilityResult(
                    success=False,
                    error=_ADB_NO_DEVICES_ERROR,
                )

        # C6 strict: enforce the canonical run-path context now that the
        # capability checks above have all passed. Without this the runner
        # would silently default to `.specs/design/screens/`.
        if output_path is None:
            return UICapabilityResult(
                success=False,
                error=(
                    "Maestro runner refuses to write into .specs/design/screens/ "
                    "by default (C6 strict). Provide output_path or "
                    "feature_slug+run_id to derive "
                    ".specs/features/<slug>/run/<run_id>/android/."
                ),
                metadata={
                    "guard": "missing_output_context",
                    "target": "android",
                },
            )
        # Single-file destination: use parent dir, preserve filename for the primary screen.
        output_dir = output_path.parent if output_path.suffix.lower() == ".png" else output_path
        output_dir.mkdir(parents=True, exist_ok=True)

        all_screenshots: list[Path] = []

        for flow_path in flows:
            flow_name = flow_path.stem
            try:
                subprocess.run(
                    ["maestro", "test", str(flow_path)],
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
                # Try to find screenshots from Maestro output (~/.maestro/tests/)
                maestro_home = Path.home() / ".maestro" / "tests"
                maestro_screenshots = self._find_maestro_screenshots(maestro_home)
                if maestro_screenshots:
                    for src in maestro_screenshots:
                        dest = output_dir / f"{flow_name}_{src.name}"
                        try:
                            import shutil
                            shutil.copy2(src, dest)
                            all_screenshots.append(dest)
                        except OSError:
                            pass
                else:
                    # Fallback: adb screencap
                    fallback_path = output_dir / f"{flow_name}.png"
                    if self._capture_adb_screenshot(serial, fallback_path):
                        all_screenshots.append(fallback_path)

            except subprocess.TimeoutExpired as exc:
                return UICapabilityResult(
                    success=False,
                    error=f"Flow '{flow_name}' timed out after {exc.timeout}s",
                    metadata={"timeout": exc.timeout},
                )
            except OSError as exc:
                if fail_fast:
                    return UICapabilityResult(
                        success=False,
                        error=f"Failed to execute maestro: {exc}",
                    )

        first_path = all_screenshots[0] if all_screenshots else None
        return UICapabilityResult(
            success=True,
            output_path=first_path,
            metadata={
                "screenshots": [str(p) for p in all_screenshots],
                "serial": serial,
                "total_flows": len(flows),
            },
        )

    # @spec FR-006: compare_baseline uses pixelmatch — .specs/features/031-ui-runner-android/spec.md#fr-006  # noqa: E501
    def compare_baseline(
        self,
        baseline: str,
        screenshot: str,
        threshold: float = DEFAULT_COMPARE_THRESHOLD,
    ) -> UICapabilityResult:
        """Compare a screenshot against a baseline image using pixelmatch.

        Delegates to the Feature 010 pixelmatch-cli.js script, reusing the
        same comparison engine as the web and iOS runners.

        Args:
            baseline: Baseline PNG path, absolute or project-relative.
            screenshot: Screenshot PNG path, absolute or project-relative.
            threshold: Pixel diff tolerance (Feature 010 default: 0.05).

        Returns:
            Result containing the diff path when the script creates one.
        """
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
        except subprocess.TimeoutExpired as exc:
            return UICapabilityResult(
                success=False,
                error=f"Pixelmatch comparison timed out after {exc.timeout}s",
                metadata={"timeout": exc.timeout, "command": " ".join(command)},
            )
        except OSError as exc:
            return UICapabilityResult(
                success=False,
                error=f"Failed to execute pixelmatch comparison: {exc}",
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


# @spec FR-001: manifest loader — .specs/features/031-ui-runner-android/spec.md#fr-001
def load_maestro_runner_manifest() -> dict[str, Any]:
    """Load the built-in Android runner manifest from disk.

    Returns:
        Parsed YAML content for `livespec/ui-runners/android.yaml`.

    Raises:
        FileNotFoundError: If the built-in manifest cannot be found.
        yaml.YAMLError: If the manifest contents are not valid YAML.
    """
    manifest_path = maestro_runner_manifest_path()
    if not manifest_path.exists():
        raise FileNotFoundError(f"Android runner manifest not found: {manifest_path}")

    with manifest_path.open() as manifest_file:
        manifest = yaml.safe_load(manifest_file)
    return cast(dict[str, Any], manifest)


# @spec FR-001: module-level detection helper — .specs/features/031-ui-runner-android/spec.md#fr-001
def detect_maestro_runner(project_dir: Path | str) -> bool:
    """Detect whether a project should use the built-in Android/Maestro runner.

    Args:
        project_dir: Project root to inspect.

    Returns:
        `True` when the Android runner should match the project, otherwise `False`.
    """
    return MaestroRunnerHandler(project_dir).detect()
