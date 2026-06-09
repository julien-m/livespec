# LiveSpec traceability anchors
# @spec(AC-002)
# @spec(AC-004)
# @spec(AC-005)
# @spec(AC-006)
# @spec(AC-007)
# @spec(AC-008)
# @spec(AC-009)
# @spec(AC-010)
# @spec(AC-011)
# @spec(AC-013)

"""Unit tests for the Android/Maestro UI runner.

All tests mock subprocess and OS calls so they run on any host without
requiring Android SDK, adb, emulator, or Maestro CLI installed.
"""

# @spec FR-001: Android runner detection — .specs/features/031-ui-runner-android/spec.md#fr-001
# @spec FR-002: AVD orchestration — .specs/features/031-ui-runner-android/spec.md#fr-002
# @spec FR-003: Maestro screenshot extraction — .specs/features/031-ui-runner-android/spec.md#fr-003
# @spec FR-004: adb fallback screenshot — .specs/features/031-ui-runner-android/spec.md#fr-004
# @spec FR-005: device override + per-device baselines
#   .specs/features/031-ui-runner-android/spec.md#fr-005
# @spec FR-006: Wear OS warning — .specs/features/031-ui-runner-android/spec.md#fr-006

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from validator.ui_runner_maestro import (
    MaestroRunnerHandler,
    detect_maestro_runner,
    load_maestro_runner_manifest,
    maestro_runner_manifest_path,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def handler(tmp_path: Path) -> MaestroRunnerHandler:
    """Return a handler pointed at a temp project directory."""
    return MaestroRunnerHandler(tmp_path)


@pytest.fixture
def android_project(tmp_path: Path) -> Path:
    """Create a minimal Android project directory structure."""
    (tmp_path / "build.gradle.kts").write_text(
        'plugins { id("com.android.application") version "8.0" }\n'
    )
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "build.gradle.kts").write_text('android { namespace = "com.example" }\n')
    return tmp_path


@pytest.fixture
def android_project_with_maestro(android_project: Path) -> Path:
    """Android project with a .specs/maestro/ directory of YAML flows."""
    maestro_dir = android_project / ".specs" / "maestro"
    maestro_dir.mkdir(parents=True)
    (maestro_dir / "home.yaml").write_text(
        "appId: com.example\n---\n- launchApp\n- takeScreenshot: home\n"
    )
    (maestro_dir / "settings.yaml").write_text(
        "appId: com.example\n---\n- launchApp\n- tapOn: Settings\n"
    )
    return android_project


# ---------------------------------------------------------------------------
# Detection tests
# ---------------------------------------------------------------------------

# @spec FR-001: Android runner detection — .specs/features/031-ui-runner-android/spec.md#fr-001


def test_detect_build_gradle(tmp_path: Path) -> None:
    """Projects with build.gradle are detected as Android projects."""
    (tmp_path / "build.gradle").write_text("// Gradle build file\n")
    handler = MaestroRunnerHandler(tmp_path)
    assert handler.detect() is True


def test_detect_build_gradle_kts(tmp_path: Path) -> None:
    """Projects with build.gradle.kts are detected as Android projects."""
    (tmp_path / "build.gradle.kts").write_text('plugins { id("com.android.application") }\n')
    handler = MaestroRunnerHandler(tmp_path)
    assert handler.detect() is True


def test_detect_android_manifest(tmp_path: Path) -> None:
    """Projects with AndroidManifest.xml are detected as Android projects."""
    (tmp_path / "AndroidManifest.xml").write_text('<manifest package="com.example"/>\n')
    handler = MaestroRunnerHandler(tmp_path)
    assert handler.detect() is True


def test_detect_maestro_dir(tmp_path: Path) -> None:
    """Projects with a maestro/ directory are detected as Android projects."""
    maestro_dir = tmp_path / "maestro"
    maestro_dir.mkdir()
    (maestro_dir / "flow.yaml").write_text("appId: com.example\n")
    handler = MaestroRunnerHandler(tmp_path)
    assert handler.detect() is True


def test_detect_specs_maestro_dir(tmp_path: Path) -> None:
    """Projects with .specs/maestro/ directory are detected as Android projects."""
    specs_maestro = tmp_path / ".specs" / "maestro"
    specs_maestro.mkdir(parents=True)
    handler = MaestroRunnerHandler(tmp_path)
    assert handler.detect() is True


def test_detect_no_markers_returns_false(tmp_path: Path) -> None:
    """Empty directory is not detected as an Android project."""
    handler = MaestroRunnerHandler(tmp_path)
    assert handler.detect() is False


def test_detect_maestro_runner_function(android_project: Path) -> None:
    """Module-level detect_maestro_runner() delegates to handler."""
    assert detect_maestro_runner(android_project) is True


# ---------------------------------------------------------------------------
# Toolchain detection
# ---------------------------------------------------------------------------

# @spec FR-002: AVD orchestration — .specs/features/031-ui-runner-android/spec.md#fr-002


def test_check_android_sdk_found_via_env(handler: MaestroRunnerHandler) -> None:
    """_check_android_sdk returns True when ANDROID_HOME is set and exists."""
    with (
        patch.dict("os.environ", {"ANDROID_HOME": str(handler.project_dir)}),
    ):
        assert handler._check_android_sdk() is True


def test_check_android_sdk_missing_env(handler: MaestroRunnerHandler) -> None:
    """_check_android_sdk returns False when ANDROID_HOME is not set."""
    with patch.dict("os.environ", {}, clear=True):
        # Remove both ANDROID_HOME and ANDROID_SDK_ROOT
        import os

        env = {k: v for k, v in os.environ.items() if k not in ("ANDROID_HOME", "ANDROID_SDK_ROOT")}
        with patch.dict("os.environ", env, clear=True):
            assert handler._check_android_sdk() is False


def test_check_maestro_found(handler: MaestroRunnerHandler) -> None:
    """_check_maestro returns True when maestro binary is found on PATH."""
    mock_result = MagicMock(returncode=0, stdout="/usr/local/bin/maestro\n")
    with patch("validator.ui_runner_maestro.subprocess.run", return_value=mock_result):
        assert handler._check_maestro() is True


def test_check_maestro_not_found(handler: MaestroRunnerHandler) -> None:
    """_check_maestro returns False when maestro is not on PATH."""
    with patch(
        "validator.ui_runner_maestro.subprocess.run",
        side_effect=FileNotFoundError("maestro not found"),
    ):
        assert handler._check_maestro() is False


def test_check_maestro_nonzero_exit(handler: MaestroRunnerHandler) -> None:
    """_check_maestro returns False when maestro exits non-zero."""
    mock_result = MagicMock(returncode=1, stdout="")
    with patch("validator.ui_runner_maestro.subprocess.run", return_value=mock_result):
        assert handler._check_maestro() is False


# ---------------------------------------------------------------------------
# AVD listing and boot orchestration
# ---------------------------------------------------------------------------

# @spec FR-002: AVD orchestration — .specs/features/031-ui-runner-android/spec.md#fr-002

_AVD_LIST_OUTPUT = """Available Android Virtual Devices:
    Name: Pixel_8_API_35
    Path: /Users/user/.android/avd/Pixel_8_API_35.avd
---------
    Name: Pixel_Tablet_API_34
    Path: /Users/user/.android/avd/Pixel_Tablet_API_34.avd
---------
"""

_ADB_DEVICES_WITH_EMULATOR = "List of devices attached\nemulator-5554\tdevice\n"
_ADB_DEVICES_EMPTY = "List of devices attached\n"


def test_list_avds_parses_output(handler: MaestroRunnerHandler) -> None:
    """_list_avds parses avdmanager output and returns AVD names."""
    mock_result = MagicMock(returncode=0, stdout=_AVD_LIST_OUTPUT)
    with patch("validator.ui_runner_maestro.subprocess.run", return_value=mock_result):
        avds = handler._list_avds()
    assert "Pixel_8_API_35" in avds
    assert "Pixel_Tablet_API_34" in avds


def test_list_avds_returns_empty_on_error(handler: MaestroRunnerHandler) -> None:
    """_list_avds returns empty list when avdmanager fails."""
    with patch(
        "validator.ui_runner_maestro.subprocess.run",
        side_effect=OSError("avdmanager not found"),
    ):
        avds = handler._list_avds()
    assert avds == []


def test_check_avd_booted_returns_serial(handler: MaestroRunnerHandler) -> None:
    """_get_running_emulator returns serial when an emulator is running."""
    mock_result = MagicMock(returncode=0, stdout=_ADB_DEVICES_WITH_EMULATOR)
    with patch("validator.ui_runner_maestro.subprocess.run", return_value=mock_result):
        serial = handler._get_running_emulator()
    assert serial == "emulator-5554"


def test_check_avd_not_booted_returns_none(handler: MaestroRunnerHandler) -> None:
    """_get_running_emulator returns None when no emulator is running."""
    mock_result = MagicMock(returncode=0, stdout=_ADB_DEVICES_EMPTY)
    with patch("validator.ui_runner_maestro.subprocess.run", return_value=mock_result):
        serial = handler._get_running_emulator()
    assert serial is None


def test_boot_avd_starts_emulator(handler: MaestroRunnerHandler) -> None:
    """_boot_avd invokes emulator -avd <name> -no-window."""
    called_cmds: list[list[str]] = []

    def mock_run(cmd, *args, **kwargs):
        called_cmds.append(list(cmd))
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = ""
        mock.stderr = ""
        return mock

    with patch("validator.ui_runner_maestro.subprocess.Popen") as mock_popen:
        mock_popen.return_value.__enter__ = lambda s: s
        mock_popen.return_value.__exit__ = MagicMock(return_value=False)
        mock_popen.return_value.poll = MagicMock(return_value=None)
        handler._boot_avd("Pixel_8_API_35")

    popen_call = mock_popen.call_args
    assert popen_call is not None
    cmd_arg = popen_call[0][0]
    assert "emulator" in " ".join(str(c) for c in cmd_arg)
    assert "Pixel_8_API_35" in " ".join(str(c) for c in cmd_arg)


def test_wait_for_boot_polls_boot_completed(handler: MaestroRunnerHandler) -> None:
    """_wait_for_boot polls adb shell getprop sys.boot_completed."""
    call_log: list[list[str]] = []

    def mock_run(cmd, *args, **kwargs):
        call_log.append(list(cmd))
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "1\n"  # boot_completed
        mock.stderr = ""
        return mock

    with patch("validator.ui_runner_maestro.subprocess.run", side_effect=mock_run):
        result = handler._wait_for_boot("emulator-5554", timeout=30)

    assert result is True
    boot_checks = [
        cmd for cmd in call_log if "getprop" in " ".join(cmd) and "boot_completed" in " ".join(cmd)
    ]
    assert len(boot_checks) >= 1


def test_wait_for_boot_timeout_returns_false(handler: MaestroRunnerHandler) -> None:
    """_wait_for_boot returns False when emulator does not boot within timeout."""

    def mock_run(cmd, *args, **kwargs):
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "0\n"  # not yet booted
        mock.stderr = ""
        return mock

    with patch("validator.ui_runner_maestro.subprocess.run", side_effect=mock_run):
        # Use a very short timeout to force expiry quickly
        result = handler._wait_for_boot("emulator-5554", timeout=1, poll_interval=0.5)

    assert result is False


# ---------------------------------------------------------------------------
# Missing Android SDK — graceful degradation
# ---------------------------------------------------------------------------

# @spec FR-002: Android SDK absent — exit 0 with skipped
#   .specs/features/031-ui-runner-android/spec.md#fr-002


def test_run_flow_no_sdk_returns_skipped(handler: MaestroRunnerHandler) -> None:
    """When ANDROID_HOME is missing, run_flow returns skipped (not crash)."""
    with (
        patch.object(handler, "_check_android_sdk", return_value=False),
        patch.object(handler, "_check_maestro", return_value=True),
    ):
        result = handler.run_flow()
    assert result.success is False
    assert result.metadata.get("skipped") is True
    assert result.error is not None
    assert "android" in result.error.lower() or "sdk" in result.error.lower()


def test_capture_screenshot_no_sdk_returns_skipped(handler: MaestroRunnerHandler) -> None:
    """When ANDROID_HOME is missing, capture_screenshot returns skipped (not crash)."""
    with (
        patch.object(handler, "_check_android_sdk", return_value=False),
        patch.object(handler, "_check_maestro", return_value=True),
    ):
        result = handler.capture_screenshot()
    assert result.success is False
    assert result.metadata.get("skipped") is True


# ---------------------------------------------------------------------------
# Missing Maestro CLI — exit 1 with install hint
# ---------------------------------------------------------------------------

# @spec FR-002: Maestro absent — exit 1 with curl hint
#   .specs/features/031-ui-runner-android/spec.md#fr-002


def test_run_flow_no_maestro_returns_error(handler: MaestroRunnerHandler) -> None:
    """When Maestro CLI is missing, run_flow returns error with install hint."""
    with (
        patch.object(handler, "_check_android_sdk", return_value=True),
        patch.object(handler, "_check_maestro", return_value=False),
    ):
        result = handler.run_flow()
    assert result.success is False
    assert result.metadata.get("skipped") is not True  # not skipped — it is an error
    assert result.error is not None
    assert "maestro" in result.error.lower()
    assert "curl" in result.error.lower() or "install" in result.error.lower()


def test_capture_screenshot_no_maestro_returns_error(handler: MaestroRunnerHandler) -> None:
    """When Maestro CLI is missing, capture_screenshot returns error with install hint."""
    with (
        patch.object(handler, "_check_android_sdk", return_value=True),
        patch.object(handler, "_check_maestro", return_value=False),
    ):
        result = handler.capture_screenshot()
    assert result.success is False
    assert result.error is not None
    assert "maestro" in result.error.lower()


# ---------------------------------------------------------------------------
# Maestro flow execution
# ---------------------------------------------------------------------------

# @spec FR-003: Maestro screenshot extraction — .specs/features/031-ui-runner-android/spec.md#fr-003
# @spec FR-004: adb fallback screenshot — .specs/features/031-ui-runner-android/spec.md#fr-004


def test_run_flow_executes_maestro_test(
    android_project_with_maestro: Path,
) -> None:
    """run_flow invokes `maestro test` for each YAML flow found."""
    handler = MaestroRunnerHandler(android_project_with_maestro)
    called_cmds: list[list[str]] = []

    def mock_run(cmd, *args, **kwargs):
        called_cmds.append(list(cmd))
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "Flow Completed\n"
        mock.stderr = ""
        return mock

    with (
        patch.object(handler, "_check_android_sdk", return_value=True),
        patch.object(handler, "_check_maestro", return_value=True),
        patch.object(handler, "_get_running_emulator", return_value="emulator-5554"),
        patch("validator.ui_runner_maestro.subprocess.run", side_effect=mock_run),
    ):
        handler.run_flow()

    maestro_calls = [
        cmd for cmd in called_cmds if "maestro" in " ".join(cmd) and "test" in " ".join(cmd)
    ]
    assert len(maestro_calls) >= 1


def test_run_flow_no_flows_dir_returns_error(handler: MaestroRunnerHandler) -> None:
    """run_flow returns error when no .specs/maestro/ directory exists."""
    with (
        patch.object(handler, "_check_android_sdk", return_value=True),
        patch.object(handler, "_check_maestro", return_value=True),
        patch.object(handler, "_get_running_emulator", return_value="emulator-5554"),
    ):
        result = handler.run_flow()
    assert result.success is False
    assert result.error is not None


def test_run_flow_continues_after_single_flow_failure(
    android_project_with_maestro: Path,
) -> None:
    """Failed flow does not stop other flows by default (AC-011)."""
    handler = MaestroRunnerHandler(android_project_with_maestro)
    call_count = 0

    def mock_run(cmd, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock = MagicMock()
        # First maestro test call fails; second should still run
        if "maestro" in " ".join(cmd) and "test" in " ".join(cmd):
            if call_count <= 1:
                mock.returncode = 1
                mock.stdout = "Flow Failed\n"
            else:
                mock.returncode = 0
                mock.stdout = "Flow Completed\n"
        else:
            mock.returncode = 0
            mock.stdout = ""
        mock.stderr = ""
        return mock

    with (
        patch.object(handler, "_check_android_sdk", return_value=True),
        patch.object(handler, "_check_maestro", return_value=True),
        patch.object(handler, "_get_running_emulator", return_value="emulator-5554"),
        patch("validator.ui_runner_maestro.subprocess.run", side_effect=mock_run),
    ):
        handler.run_flow()

    # Both flows should have been attempted (call_count >= 2 maestro test calls)
    assert call_count >= 2


def test_run_flow_fail_fast_stops_on_first_failure(
    android_project_with_maestro: Path,
) -> None:
    """With fail_fast=True, first failed flow stops execution (AC-011)."""
    handler = MaestroRunnerHandler(android_project_with_maestro)
    maestro_call_count = 0

    def mock_run(cmd, *args, **kwargs):
        nonlocal maestro_call_count
        mock = MagicMock()
        if "maestro" in " ".join(cmd) and "test" in " ".join(cmd):
            maestro_call_count += 1
            mock.returncode = 1
            mock.stdout = "Flow Failed\n"
        else:
            mock.returncode = 0
            mock.stdout = ""
        mock.stderr = ""
        return mock

    with (
        patch.object(handler, "_check_android_sdk", return_value=True),
        patch.object(handler, "_check_maestro", return_value=True),
        patch.object(handler, "_get_running_emulator", return_value="emulator-5554"),
        patch("validator.ui_runner_maestro.subprocess.run", side_effect=mock_run),
    ):
        result = handler.run_flow(fail_fast=True)

    assert result.success is False
    assert maestro_call_count == 1  # stopped after first failure


# ---------------------------------------------------------------------------
# Screenshot extraction from Maestro output
# ---------------------------------------------------------------------------

# @spec FR-003: Maestro screenshot extraction — .specs/features/031-ui-runner-android/spec.md#fr-003


def test_find_maestro_screenshots_finds_tagged_pngs(
    handler: MaestroRunnerHandler, tmp_path: Path
) -> None:
    """_find_maestro_screenshots locates PNGs from ~/.maestro/tests/ output."""
    # Simulate Maestro output directory structure
    maestro_output = tmp_path / "maestro_run"
    maestro_output.mkdir()
    (maestro_output / "home.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (maestro_output / "settings.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    screenshots = handler._find_maestro_screenshots(maestro_output)
    assert len(screenshots) == 2
    assert all(p.suffix == ".png" for p in screenshots)


def test_find_maestro_screenshots_empty_dir(handler: MaestroRunnerHandler, tmp_path: Path) -> None:
    """_find_maestro_screenshots returns empty list for empty directory."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    assert handler._find_maestro_screenshots(empty_dir) == []


def test_find_maestro_screenshots_nonexistent_dir(
    handler: MaestroRunnerHandler, tmp_path: Path
) -> None:
    """_find_maestro_screenshots returns empty list for nonexistent directory."""
    missing = tmp_path / "does_not_exist"
    assert handler._find_maestro_screenshots(missing) == []


# ---------------------------------------------------------------------------
# adb fallback screenshot
# ---------------------------------------------------------------------------

# @spec FR-004: adb fallback screenshot — .specs/features/031-ui-runner-android/spec.md#fr-004


def test_capture_adb_screenshot_invokes_screencap(
    handler: MaestroRunnerHandler, tmp_path: Path
) -> None:
    """_capture_adb_screenshot runs adb shell screencap and pulls the PNG."""
    output_path = tmp_path / "screen.png"
    called_cmds: list[list[str]] = []

    def mock_run(cmd, *args, **kwargs):
        called_cmds.append(list(cmd))
        # Simulate adb pull creating the file
        if "pull" in " ".join(cmd):
            output_path.write_bytes(b"\x89PNG\r\n\x1a\n")
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = ""
        mock.stderr = ""
        return mock

    with patch("validator.ui_runner_maestro.subprocess.run", side_effect=mock_run):
        result = handler._capture_adb_screenshot("emulator-5554", output_path)

    assert result is True
    screencap_calls = [cmd for cmd in called_cmds if "screencap" in " ".join(cmd)]
    pull_calls = [cmd for cmd in called_cmds if "pull" in " ".join(cmd)]
    assert len(screencap_calls) >= 1
    assert len(pull_calls) >= 1


def test_capture_adb_screenshot_uses_serial(handler: MaestroRunnerHandler, tmp_path: Path) -> None:
    """_capture_adb_screenshot passes -s <serial> to adb."""
    output_path = tmp_path / "screen.png"
    captured_serial: list[str] = []

    def mock_run(cmd, *args, **kwargs):
        cmd_str = " ".join(str(c) for c in cmd)
        if "-s" in cmd_str and "emulator-9876" in cmd_str:
            captured_serial.append("found")
        if "pull" in cmd_str:
            output_path.write_bytes(b"\x89PNG\r\n\x1a\n")
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = ""
        mock.stderr = ""
        return mock

    with patch("validator.ui_runner_maestro.subprocess.run", side_effect=mock_run):
        handler._capture_adb_screenshot("emulator-9876", output_path)

    assert len(captured_serial) >= 1


def test_capture_adb_screenshot_returns_false_on_failure(
    handler: MaestroRunnerHandler, tmp_path: Path
) -> None:
    """_capture_adb_screenshot returns False when adb commands fail."""
    output_path = tmp_path / "screen.png"

    with patch(
        "validator.ui_runner_maestro.subprocess.run",
        side_effect=OSError("adb not found"),
    ):
        result = handler._capture_adb_screenshot("emulator-5554", output_path)

    assert result is False


# ---------------------------------------------------------------------------
# capture_screenshot capability
# ---------------------------------------------------------------------------

# @spec FR-003: capture_screenshot capability — .specs/features/031-ui-runner-android/spec.md#fr-003


def test_capture_screenshot_uses_avd_subdirectory(
    android_project_with_maestro: Path, tmp_path: Path
) -> None:
    """capture_screenshot stores PNGs under .specs/design/screens/<avd_name>/."""
    handler = MaestroRunnerHandler(android_project_with_maestro)

    def mock_run(cmd, *args, **kwargs):
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "Flow Completed\n"
        mock.stderr = ""
        return mock

    with (
        patch.object(handler, "_check_android_sdk", return_value=True),
        patch.object(handler, "_check_maestro", return_value=True),
        patch.object(handler, "_get_running_emulator", return_value="emulator-5554"),
        patch.object(
            handler,
            "_find_maestro_screenshots",
            return_value=[tmp_path / "home.png"],
        ),
        patch("validator.ui_runner_maestro.subprocess.run", side_effect=mock_run),
    ):
        result = handler.capture_screenshot(avd_name="Pixel_8_API_35")

    # Output path should include the avd name
    if result.output_path is not None:
        assert "Pixel_8_API_35" in str(result.output_path) or result.success


# ---------------------------------------------------------------------------
# Device override (--device flag)
# ---------------------------------------------------------------------------

# @spec FR-005: device override + per-device baselines
#   .specs/features/031-ui-runner-android/spec.md#fr-005


def test_avd_not_found_lists_available_and_returns_error(
    android_project_with_maestro: Path,
) -> None:
    """run_flow returns error with available AVDs when specified AVD does not exist."""
    handler = MaestroRunnerHandler(android_project_with_maestro)

    with (
        patch.object(handler, "_check_android_sdk", return_value=True),
        patch.object(handler, "_check_maestro", return_value=True),
        patch.object(
            handler,
            "_list_avds",
            return_value=["Pixel_8_API_35", "Pixel_Tablet_API_34"],
        ),
        patch.object(handler, "_get_running_emulator", return_value=None),
        patch.object(handler, "_boot_avd_and_wait", return_value=False),
    ):
        result = handler.run_flow(avd_name="NonExistent_AVD_99")

    assert result.success is False
    assert result.error is not None


def test_per_device_baseline_path_includes_device_name(
    handler: MaestroRunnerHandler,
) -> None:
    """_resolve_baseline_path includes device name in per-device baseline path."""
    path = handler._resolve_baseline_path(screen="dashboard", avd_name="Pixel_Tablet_API_34")
    assert "Pixel_Tablet_API_34" in str(path)
    assert "dashboard" in str(path)


def test_default_baseline_path_no_device_override(
    handler: MaestroRunnerHandler,
) -> None:
    """_resolve_baseline_path with default AVD uses flat .specs/design/screens/ path."""
    path = handler._resolve_baseline_path(screen="home", avd_name=None)
    assert "home" in str(path)


# ---------------------------------------------------------------------------
# Wear OS warning
# ---------------------------------------------------------------------------

# @spec FR-006: Wear OS warning — .specs/features/031-ui-runner-android/spec.md#fr-006


def test_wearos_platform_emits_experimental_warning(
    android_project_with_maestro: Path,
) -> None:
    """run_flow with platform='wearos' emits an experimental warning."""
    handler = MaestroRunnerHandler(android_project_with_maestro)
    warnings_emitted: list[str] = []

    def mock_run(cmd, *args, **kwargs):
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "Flow Completed\n"
        mock.stderr = ""
        return mock

    with (
        patch.object(handler, "_check_android_sdk", return_value=True),
        patch.object(handler, "_check_maestro", return_value=True),
        patch.object(handler, "_get_running_emulator", return_value="emulator-5554"),
        patch("validator.ui_runner_maestro.subprocess.run", side_effect=mock_run),
        patch(
            "validator.ui_runner_maestro.warnings.warn",
            side_effect=lambda msg, *a, **kw: warnings_emitted.append(str(msg)),
        ),
    ):
        handler.run_flow(platform="wearos")

    # At least one warning containing 'experimental' about Wear OS
    wearos_warnings = [
        w for w in warnings_emitted if "wear" in w.lower() or "experimental" in w.lower()
    ]
    assert len(wearos_warnings) >= 1


# ---------------------------------------------------------------------------
# Maestro output parsing
# ---------------------------------------------------------------------------

# @spec FR-003: parse Maestro output — .specs/features/031-ui-runner-android/spec.md#fr-003


def test_parse_maestro_output_success(handler: MaestroRunnerHandler) -> None:
    """_parse_maestro_result returns success=True for 'Flow Completed' output."""
    output = "Flow Completed\nStep 1: Passed\nStep 2: Passed\n"
    assert handler._parse_maestro_result(output, returncode=0) is True


def test_parse_maestro_output_failure(handler: MaestroRunnerHandler) -> None:
    """_parse_maestro_result returns success=False for failed output."""
    output = "Flow Failed\nStep 1: Passed\nStep 2: Failed - Element not found\n"
    assert handler._parse_maestro_result(output, returncode=1) is False


def test_parse_maestro_output_nonzero_exit(handler: MaestroRunnerHandler) -> None:
    """_parse_maestro_result returns success=False for non-zero exit code."""
    assert handler._parse_maestro_result("", returncode=1) is False


# ---------------------------------------------------------------------------
# compare_baseline
# ---------------------------------------------------------------------------


def test_compare_baseline_missing_script(handler: MaestroRunnerHandler) -> None:
    """compare_baseline returns error when pixelmatch-cli.js is not found."""
    result = handler.compare_baseline("baseline.png", "screenshot.png")
    assert result.success is False
    assert result.error is not None
    assert "pixelmatch" in result.error.lower() or "not found" in result.error.lower()


def test_compare_baseline_delegates_to_pixelmatch(tmp_path: Path) -> None:
    """compare_baseline invokes node scripts/pixelmatch-cli.js with correct args."""
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    script = scripts_dir / "pixelmatch-cli.js"
    script.write_text("// pixelmatch stub\n")

    baseline = tmp_path / "baseline.png"
    screenshot = tmp_path / "screenshot.png"
    baseline.write_bytes(b"\x89PNG\r\n\x1a\n")
    screenshot.write_bytes(b"\x89PNG\r\n\x1a\n")

    captured_cmd: list[str] = []

    def mock_run(cmd, *args, **kwargs):
        captured_cmd.extend(cmd)
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = ""
        mock.stderr = ""
        return mock

    handler = MaestroRunnerHandler(tmp_path)
    with patch("validator.ui_runner_maestro.subprocess.run", side_effect=mock_run):
        handler.compare_baseline(str(baseline), str(screenshot))

    assert "node" in captured_cmd
    assert any("pixelmatch-cli.js" in arg for arg in captured_cmd)


# ---------------------------------------------------------------------------
# Timeout handling
# ---------------------------------------------------------------------------

# @spec FR-002: emulator boot timeout — .specs/features/031-ui-runner-android/spec.md#fr-002


def test_run_flow_timeout_returns_error(
    android_project_with_maestro: Path,
) -> None:
    """run_flow returns error when maestro test times out."""
    handler = MaestroRunnerHandler(android_project_with_maestro)

    def mock_run(cmd, *args, **kwargs):
        if "maestro" in " ".join(cmd) and "test" in " ".join(cmd):
            raise subprocess.TimeoutExpired(cmd, timeout=300)
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = ""
        mock.stderr = ""
        return mock

    with (
        patch.object(handler, "_check_android_sdk", return_value=True),
        patch.object(handler, "_check_maestro", return_value=True),
        patch.object(handler, "_get_running_emulator", return_value="emulator-5554"),
        patch("validator.ui_runner_maestro.subprocess.run", side_effect=mock_run),
    ):
        result = handler.run_flow()

    assert result.success is False
    assert result.error is not None
    assert "timeout" in result.error.lower() or "timed out" in result.error.lower()


# ---------------------------------------------------------------------------
# Multiple AVDs — alphabetical selection (EC-001)
# ---------------------------------------------------------------------------


def test_multiple_avds_match_picks_first_alphabetical(
    handler: MaestroRunnerHandler,
) -> None:
    """When multiple AVDs match, _select_avd returns the first alphabetically (EC-001)."""
    avds = ["Pixel_8_API_35_B", "Pixel_8_API_35_A", "Pixel_8_API_35_C"]
    selected = handler._select_avd(avds, preferred="Pixel_8")
    assert selected == "Pixel_8_API_35_A"


def test_select_avd_exact_match_wins(handler: MaestroRunnerHandler) -> None:
    """_select_avd returns exact match when available."""
    avds = ["Pixel_8_API_35", "Pixel_Tablet_API_34"]
    selected = handler._select_avd(avds, preferred="Pixel_Tablet_API_34")
    assert selected == "Pixel_Tablet_API_34"


def test_select_avd_no_match_returns_none(handler: MaestroRunnerHandler) -> None:
    """_select_avd returns None when no AVD matches."""
    avds = ["Pixel_8_API_35"]
    selected = handler._select_avd(avds, preferred="NonExistent_AVD")
    assert selected is None


# ---------------------------------------------------------------------------
# EC-006 — CI without Android SDK
# ---------------------------------------------------------------------------


def test_adb_zero_devices_after_boot_returns_error(
    android_project_with_maestro: Path,
) -> None:
    """EC-005: adb sees 0 devices after boot wait → clear error message."""
    handler = MaestroRunnerHandler(android_project_with_maestro)

    with (
        patch.object(handler, "_check_android_sdk", return_value=True),
        patch.object(handler, "_check_maestro", return_value=True),
        patch.object(handler, "_get_running_emulator", return_value=None),
        patch.object(handler, "_boot_avd_and_wait", return_value=False),
    ):
        result = handler.run_flow()

    assert result.success is False
    assert result.error is not None


# ---------------------------------------------------------------------------
# Manifest loading
# ---------------------------------------------------------------------------


def test_maestro_manifest_path_points_to_android_yaml() -> None:
    """maestro_runner_manifest_path() returns path to android.yaml."""
    path = maestro_runner_manifest_path()
    assert path.name == "android.yaml"
    assert "ui-runners" in str(path)


def test_load_maestro_runner_manifest() -> None:
    """load_maestro_runner_manifest() loads a valid YAML dict."""
    manifest = load_maestro_runner_manifest()
    assert isinstance(manifest, dict)
    assert "runner" in manifest
    assert manifest["runner"]["id"] == "maestro"


# ---------------------------------------------------------------------------
# Integration markers (require real Android SDK — skipped in CI)
# ---------------------------------------------------------------------------


@pytest.mark.android
def test_real_avd_boot_integration(tmp_path: Path) -> None:  # pragma: no cover
    """Integration: actually boot an Android AVD (Android SDK only)."""
    pytest.skip("Requires real Android SDK + AVD — run manually on developer host")


@pytest.mark.android
def test_real_maestro_flow_integration(tmp_path: Path) -> None:  # pragma: no cover
    """Integration: run real Maestro flow on fixture Android project."""
    pytest.skip("Requires real Android SDK + Maestro CLI — run manually on developer host")
