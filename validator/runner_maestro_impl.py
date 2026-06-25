# LiveSpec traceability anchors
# @spec(AC-002)
# @spec(FR-001)
# @spec(FR-002)
# @spec(FR-003)
# @spec(FR-004)
# @spec(FR-005)
# @spec(FR-006)

"""Android UI runner support for Maestro YAML flow-based projects."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]  # PyYAML is a runtime dependency without stubs.

DEFAULT_COMPARE_THRESHOLD = 0.05
FLOW_TIMEOUT_SECONDS = 300
AVD_BOOT_TIMEOUT_SECONDS = 90
AVD_BOOT_POLL_INTERVAL = 5
SCREENCAP_REMOTE_PATH = "/sdcard/livespec_screen.png"

_ANDROID_SDK_SKIP_ERROR = (
    "Android UI runner requires Android SDK — skipped on this host. "
    "Install: https://developer.android.com/studio or set ANDROID_HOME."
)
_MAESTRO_MISSING_ERROR = (
    "Maestro CLI not installed. Install: curl -Ls https://get.maestro.mobile.dev | bash"
)
_WEAROS_EXPERIMENTAL_WARNING = "Wear OS support is experimental in Maestro — proceed with caution"
_NO_FLOWS_ERROR = (
    "No Maestro flows found. Create YAML flows in .specs/maestro/ or maestro/ directory."
)
_ADB_NO_DEVICES_ERROR = (
    "ADB sees no devices — emulator may not be running. "
    "Check ANDROID_HOME and emulator path, or run avdmanager to list available AVDs."
)
_AVD_BOOT_TIMEOUT_ERROR = "Emulator failed to reach adb-ready state within {timeout}s."


@dataclass
class UICapabilityResult:
    """Describe the outcome of one UI runner capability invocation."""

    success: bool
    output_path: Path | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=lambda: cast(dict[str, Any], {}))


def maestro_runner_manifest_path() -> Path:
    """Return the filesystem path to the built-in Android runner manifest."""
    return Path(__file__).resolve().parent.parent / "livespec" / "ui-runners" / "android.yaml"


class MaestroRunnerHandler:
    """Handle UI runner capabilities for Android Maestro YAML flow projects."""

    def __init__(self, project_dir: Path | str) -> None:
        """Initialize the handler with a project root."""
        self.project_dir = Path(project_dir).resolve()

    def _check_android_sdk(self) -> bool:
        """Return True when Android SDK is available on this host."""
        from validator.android_runner_core import check_android_sdk

        return check_android_sdk()

    def _check_maestro(self) -> bool:
        """Return True when the Maestro CLI binary is available on PATH."""
        from validator.android_runner_core import check_maestro

        return check_maestro()

    def preflight_message(self) -> str:
        """Return an actionable diagnostic for the dispatcher BLOCKED line."""
        if not self._check_maestro():
            return (
                "maestro CLI not on PATH — install: "
                "curl -Ls 'https://get.maestro.mobile.dev' | bash"
            )
        if not self._check_android_sdk():
            return "Android SDK not found — set ANDROID_HOME or install Android Studio"
        if self._get_running_emulator() is None:
            return "no Android emulator available — start one with 'emulator -avd <name>'"
        return ""

    def detect(self) -> bool:
        """Check whether the project is an Android Gradle / Maestro project."""
        if not self.project_dir.exists():
            return False
        for marker in ("build.gradle", "build.gradle.kts", "AndroidManifest.xml"):
            if (self.project_dir / marker).exists():
                return True
        return (self.project_dir / "maestro").exists() or (
            self.project_dir / ".specs" / "maestro"
        ).exists()

    def _list_avds(self) -> list[str]:
        """Return available AVD names from avdmanager."""
        from validator.android_runner_core import list_avds

        return list_avds()

    def _get_running_emulator(self) -> str | None:
        """Return the adb serial of a running emulator, or None if none exists."""
        from validator.android_runner_core import get_running_emulator

        return get_running_emulator()

    def _boot_avd(self, avd_name: str) -> None:
        """Start the named AVD in headless mode."""
        from validator.android_runner_core import boot_avd

        boot_avd(avd_name)

    def _wait_for_boot(
        self,
        serial: str,
        timeout: int = AVD_BOOT_TIMEOUT_SECONDS,
        poll_interval: float = AVD_BOOT_POLL_INTERVAL,
    ) -> bool:
        """Wait for the AVD identified by `serial` to reach boot_completed state."""
        from validator.android_runner_core import wait_for_boot

        return wait_for_boot(serial, timeout, poll_interval)

    def _boot_avd_and_wait(self, avd_name: str, timeout: int = AVD_BOOT_TIMEOUT_SECONDS) -> bool:
        """Boot the named AVD and wait until it is adb-ready."""
        from validator.android_runner_core import boot_avd_and_wait

        return boot_avd_and_wait(avd_name, timeout)

    def _select_avd(self, avds: list[str], preferred: str) -> str | None:
        """Select an AVD by exact name or deterministic substring match."""
        from validator.android_runner_core import select_avd

        return select_avd(avds, preferred)

    def _find_flows(self) -> list[Path]:
        """Return sorted YAML flow files under .specs/maestro/ or maestro/."""
        from validator.android_runner_core import find_flows

        return find_flows(self.project_dir)

    def _find_maestro_screenshots(self, maestro_output_dir: Path) -> list[Path]:
        """Find PNG screenshots emitted by Maestro in the given directory."""
        from validator.android_runner_core import find_maestro_screenshots

        return find_maestro_screenshots(maestro_output_dir)

    def _capture_adb_screenshot(self, serial: str, output_path: Path) -> bool:
        """Capture a screenshot via adb shell screencap and pull."""
        from validator.android_runner_core import capture_adb_screenshot

        return capture_adb_screenshot(serial, output_path)

    def _resolve_baseline_path(self, screen: str, avd_name: str | None = None) -> Path:
        """Resolve the path where a baseline PNG should be stored."""
        from validator.android_runner_core import resolve_baseline_path

        return resolve_baseline_path(self.project_dir, screen, avd_name)

    def _parse_maestro_result(self, output: str, returncode: int) -> bool:
        """Determine whether a Maestro flow run succeeded."""
        from validator.android_runner_core import parse_maestro_result

        return parse_maestro_result(output, returncode)

    def run_flow(
        self,
        avd_name: str | None = None,
        platform: str = "android",
        fail_fast: bool = False,
        timeout: int = FLOW_TIMEOUT_SECONDS,
    ) -> UICapabilityResult:
        """Run all Maestro flows in .specs/maestro/ and report results."""
        from validator.android_runner_core import run_flow

        return run_flow(self, avd_name, platform, fail_fast, timeout)

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
        """Run flows, extract tagged screenshots, and fall back to adb screencap."""
        from validator.android_runner_core import capture_screenshot

        return capture_screenshot(
            self, screen, avd_name, platform, fail_fast, timeout, output_path, feature_slug, run_id
        )

    def compare_baseline(
        self,
        baseline: str,
        screenshot: str,
        threshold: float = DEFAULT_COMPARE_THRESHOLD,
    ) -> UICapabilityResult:
        """Compare a screenshot against a baseline image using pixelmatch."""
        from validator.android_capture_core import compare_baseline

        return compare_baseline(self.project_dir, baseline, screenshot, threshold)


def load_maestro_runner_manifest() -> dict[str, Any]:
    """Load the built-in Android runner manifest from disk."""
    manifest_path = maestro_runner_manifest_path()
    if not manifest_path.exists():
        raise FileNotFoundError(f"Android runner manifest not found: {manifest_path}")
    with manifest_path.open() as manifest_file:
        manifest = yaml.safe_load(manifest_file)
    return cast(dict[str, Any], manifest)


def detect_maestro_runner(project_dir: Path | str) -> bool:
    """Detect whether a project should use the built-in Android/Maestro runner."""
    return MaestroRunnerHandler(project_dir).detect()
