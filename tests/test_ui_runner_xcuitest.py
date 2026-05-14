"""Unit tests for the iOS/watchOS XCUITest UI runner.

All tests mock subprocess and platform calls so they run on any OS without
requiring Xcode, xcrun, or a real iOS simulator.
"""

# @spec FR-001: manifest + runner detection
# .specs/features/030-ui-runner-ios-watchos/spec.md#fr-001
# @spec FR-002: .xcresult parsing
# .specs/features/030-ui-runner-ios-watchos/spec.md#fr-002
# @spec FR-003: simulator boot orchestration
# .specs/features/030-ui-runner-ios-watchos/spec.md#fr-003
# @spec FR-004: watchOS destination filtering
# .specs/features/030-ui-runner-ios-watchos/spec.md#fr-004
# @spec FR-005: launch_arguments injection
# .specs/features/030-ui-runner-ios-watchos/spec.md#fr-005
# @spec FR-006: Xcode license detection
# .specs/features/030-ui-runner-ios-watchos/spec.md#fr-006

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from validator.ui_runner_xcuitest import (
    XCUITestRunnerHandler,
    detect_xcuitest_runner,
    load_xcuitest_runner_manifest,
    xcuitest_runner_manifest_path,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def handler(tmp_path: Path) -> XCUITestRunnerHandler:
    """Return a handler pointed at a temp project directory."""
    return XCUITestRunnerHandler(tmp_path)


@pytest.fixture
def xcodeproj_project(tmp_path: Path) -> Path:
    """Create a minimal Xcode project directory structure."""
    (tmp_path / "MyApp.xcodeproj").mkdir()
    (tmp_path / "MyApp.xcodeproj" / "project.pbxproj").write_text("")
    return tmp_path


@pytest.fixture
def package_swift_project(tmp_path: Path) -> Path:
    """Create a minimal Swift Package Manager project."""
    (tmp_path / "Package.swift").write_text(
        "// swift-tools-version: 5.9\n"
        "import PackageDescription\n"
        "let package = Package(name: \"MyLib\")\n"
    )
    return tmp_path


# ---------------------------------------------------------------------------
# Detection tests
# ---------------------------------------------------------------------------

# @spec FR-001: project detection — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-001

def test_detect_xcodeproj(xcodeproj_project: Path) -> None:
    """Projects with .xcodeproj directory are detected as iOS projects."""
    handler = XCUITestRunnerHandler(xcodeproj_project)
    assert handler.detect() is True


def test_detect_package_swift(package_swift_project: Path) -> None:
    """Projects with Package.swift are detected as iOS/Swift projects."""
    handler = XCUITestRunnerHandler(package_swift_project)
    assert handler.detect() is True


def test_detect_no_project(tmp_path: Path) -> None:
    """Empty directory is not detected as an iOS project."""
    handler = XCUITestRunnerHandler(tmp_path)
    assert handler.detect() is False


def test_detect_xcuitest_runner_function(xcodeproj_project: Path) -> None:
    """Module-level detect_xcuitest_runner() delegates to handler."""
    assert detect_xcuitest_runner(xcodeproj_project) is True


# ---------------------------------------------------------------------------
# Non-macOS graceful degradation
# ---------------------------------------------------------------------------

# @spec FR-006: non-macOS skipped — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-006

def test_non_macos_capture_screenshot_returns_skipped(
    handler: XCUITestRunnerHandler,
) -> None:
    """On non-macOS, capture_screenshot returns skipped error without crash."""
    with patch("validator.ui_runner_xcuitest.platform.system", return_value="Linux"):
        result = handler.capture_screenshot()
    assert result.success is False
    assert result.error is not None
    assert "macOS" in result.error
    assert result.metadata.get("skipped") is True


def test_non_macos_run_flow_returns_skipped(handler: XCUITestRunnerHandler) -> None:
    """On non-macOS, run_flow returns skipped error without crash."""
    with patch("validator.ui_runner_xcuitest.platform.system", return_value="Linux"):
        result = handler.run_flow()
    assert result.success is False
    assert result.error is not None
    assert "macOS" in result.error
    assert result.metadata.get("skipped") is True


# ---------------------------------------------------------------------------
# Missing toolchain
# ---------------------------------------------------------------------------

# @spec FR-006: Xcode license detection — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-006

def test_missing_xcrun_capture_returns_error(handler: XCUITestRunnerHandler) -> None:
    """When xcrun is not found, capture_screenshot returns Xcode install hint."""
    with (
        patch("validator.ui_runner_xcuitest.platform.system", return_value="Darwin"),
        patch(
            "validator.ui_runner_xcuitest.subprocess.run",
            side_effect=FileNotFoundError("xcrun not found"),
        ),
    ):
        result = handler.capture_screenshot()
    assert result.success is False
    assert result.error is not None
    assert "Xcode" in result.error


def test_missing_xcrun_uses_get_toolchain(handler: XCUITestRunnerHandler) -> None:
    """_get_toolchain_path returns None when xcrun is unavailable."""
    with patch(
        "validator.ui_runner_xcuitest.subprocess.run",
        side_effect=FileNotFoundError("xcrun not found"),
    ):
        assert handler._get_toolchain_path() is None


def test_get_toolchain_path_returns_path_on_success(handler: XCUITestRunnerHandler) -> None:
    """_get_toolchain_path returns the path string when xcrun succeeds."""
    mock_result = MagicMock(returncode=0, stdout="/usr/bin/xcodebuild\n")
    with patch("validator.ui_runner_xcuitest.subprocess.run", return_value=mock_result):
        path = handler._get_toolchain_path()
    assert path == "/usr/bin/xcodebuild"


# ---------------------------------------------------------------------------
# Xcode license detection
# ---------------------------------------------------------------------------

# @spec FR-006: license detection — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-006

def test_xcode_license_not_accepted_returns_error(handler: XCUITestRunnerHandler) -> None:
    """When xcodebuild reports license not accepted, capture_screenshot returns recovery hint."""

    def mock_run(cmd, *args, **kwargs):
        joined = " ".join(str(c) for c in cmd)
        mock = MagicMock()
        if "--find" in joined:
            mock.returncode = 0
            mock.stdout = "/usr/bin/xcodebuild\n"
        elif "-license" in joined and "check" in joined:
            mock.returncode = 1
            mock.stdout = "The license has not been accepted."
            mock.stderr = ""
        else:
            mock.returncode = 0
            mock.stdout = ""
            mock.stderr = ""
        return mock

    with (
        patch("validator.ui_runner_xcuitest.platform.system", return_value="Darwin"),
        patch("validator.ui_runner_xcuitest.subprocess.run", side_effect=mock_run),
    ):
        result = handler.capture_screenshot()

    assert result.success is False
    assert result.error is not None
    assert "license" in result.error.lower()
    assert "sudo xcodebuild -license accept" in result.error


def test_check_xcode_license_returns_false_on_not_accepted(
    handler: XCUITestRunnerHandler,
) -> None:
    """_check_xcode_license returns False when license output says not accepted."""
    mock_result = MagicMock(
        returncode=1,
        stdout="The license has not been accepted.",
        stderr="",
    )
    with patch("validator.ui_runner_xcuitest.subprocess.run", return_value=mock_result):
        assert handler._check_xcode_license() is False


def test_check_xcode_license_returns_true_when_accepted(
    handler: XCUITestRunnerHandler,
) -> None:
    """_check_xcode_license returns True when xcodebuild license check passes."""
    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("validator.ui_runner_xcuitest.subprocess.run", return_value=mock_result):
        assert handler._check_xcode_license() is True


# ---------------------------------------------------------------------------
# Simulator boot management
# ---------------------------------------------------------------------------

# @spec FR-003: simulator boot orchestration
# .specs/features/030-ui-runner-ios-watchos/spec.md#fr-003

_SIMCTL_JSON_BOOTED = json.dumps({
    "devices": {
        "com.apple.CoreSimulator.SimRuntime.iOS-18-0": [
            {"udid": "TEST-UDID-001", "name": "iPhone 16", "state": "Booted"},
        ]
    }
})

_SIMCTL_JSON_SHUTDOWN = json.dumps({
    "devices": {
        "com.apple.CoreSimulator.SimRuntime.iOS-18-0": [
            {"udid": "TEST-UDID-001", "name": "iPhone 16", "state": "Shutdown"},
        ]
    }
})

_SIMCTL_JSON_EMPTY = json.dumps({"devices": {}})


def test_simulator_boot_already_booted(handler: XCUITestRunnerHandler) -> None:
    """When simulator is already Booted, _boot_simulator returns True without booting."""
    call_log: list[list[str]] = []

    def mock_run(cmd, *args, **kwargs):
        call_log.append(list(cmd))
        joined = " ".join(str(c) for c in cmd)
        mock = MagicMock()
        if "list" in joined and "devices" in joined and "--json" in joined:
            mock.returncode = 0
            mock.stdout = _SIMCTL_JSON_BOOTED
        else:
            mock.returncode = 0
            mock.stdout = ""
            mock.stderr = ""
        return mock

    with patch("validator.ui_runner_xcuitest.subprocess.run", side_effect=mock_run):
        result = handler._boot_simulator("TEST-UDID-001")

    assert result is True
    # simctl boot should NOT be called since it was already Booted
    boot_calls = [
        cmd
        for cmd in call_log
        if "boot" in " ".join(cmd)
        and "status" not in " ".join(cmd)
        and "list" not in " ".join(cmd)
    ]
    assert len(boot_calls) == 0


def test_simulator_boot_from_shutdown(handler: XCUITestRunnerHandler) -> None:
    """When simulator is Shutdown, _boot_simulator boots it and waits."""
    call_log: list[list[str]] = []

    def mock_run(cmd, *args, **kwargs):
        call_log.append(list(cmd))
        joined = " ".join(str(c) for c in cmd)
        mock = MagicMock()
        if "list" in joined and "devices" in joined and "--json" in joined:
            mock.returncode = 0
            mock.stdout = _SIMCTL_JSON_SHUTDOWN
        elif "bootstatus" in joined:
            mock.returncode = 0
            mock.stdout = ""
        elif "boot" in joined:
            mock.returncode = 0
            mock.stdout = ""
            mock.stderr = ""
        else:
            mock.returncode = 0
            mock.stdout = ""
            mock.stderr = ""
        return mock

    with patch("validator.ui_runner_xcuitest.subprocess.run", side_effect=mock_run):
        result = handler._boot_simulator("TEST-UDID-001")

    assert result is True
    boot_calls = [
        cmd
        for cmd in call_log
        if "boot" in " ".join(cmd)
        and "list" not in " ".join(cmd)
        and "status" not in " ".join(cmd)
    ]
    assert len(boot_calls) >= 1


def test_simulator_boot_device_not_found_returns_false(
    handler: XCUITestRunnerHandler,
) -> None:
    """When simulator UDID is not in simctl output, _boot_simulator boots it (no early exit)."""
    # If UDID doesn't exist in the list JSON, we still attempt the boot command
    def mock_run(cmd, *args, **kwargs):
        joined = " ".join(str(c) for c in cmd)
        mock = MagicMock()
        if "list" in joined and "--json" in joined:
            mock.returncode = 0
            mock.stdout = _SIMCTL_JSON_EMPTY
        elif "boot" in joined and "status" not in joined:
            mock.returncode = 1
            mock.stderr = "No device matching the given identifier."
            mock.stdout = ""
        elif "bootstatus" in joined:
            mock.returncode = 1
            mock.stdout = ""
            mock.stderr = ""
        else:
            mock.returncode = 0
            mock.stdout = ""
            mock.stderr = ""
        return mock

    with patch("validator.ui_runner_xcuitest.subprocess.run", side_effect=mock_run):
        result = handler._boot_simulator("NONEXISTENT-UDID")

    # Should return False since boot failed
    assert result is False


def test_list_simulators_returns_dict(handler: XCUITestRunnerHandler) -> None:
    """_list_simulators parses xcrun simctl list --json output."""
    mock_result = MagicMock(returncode=0, stdout=_SIMCTL_JSON_BOOTED)
    with patch("validator.ui_runner_xcuitest.subprocess.run", return_value=mock_result):
        data = handler._list_simulators()
    assert "devices" in data


def test_list_simulators_returns_empty_on_error(handler: XCUITestRunnerHandler) -> None:
    """_list_simulators returns {} when xcrun fails."""
    with patch(
        "validator.ui_runner_xcuitest.subprocess.run",
        side_effect=OSError("xcrun not found"),
    ):
        data = handler._list_simulators()
    assert data == {}


def test_find_simulator_udid_found(handler: XCUITestRunnerHandler) -> None:
    """_find_simulator_udid finds matching device by name and platform."""
    mock_result = MagicMock(returncode=0, stdout=_SIMCTL_JSON_BOOTED)
    with patch("validator.ui_runner_xcuitest.subprocess.run", return_value=mock_result):
        udid = handler._find_simulator_udid("iPhone 16", "iOS")
    assert udid == "TEST-UDID-001"


def test_find_simulator_udid_not_found(handler: XCUITestRunnerHandler) -> None:
    """_find_simulator_udid returns None for unknown device."""
    mock_result = MagicMock(returncode=0, stdout=_SIMCTL_JSON_EMPTY)
    with patch("validator.ui_runner_xcuitest.subprocess.run", return_value=mock_result):
        udid = handler._find_simulator_udid("iPhone 99", "iOS")
    assert udid is None


# ---------------------------------------------------------------------------
# Destination normalization (id=UUID → name=...,OS=...)
# ---------------------------------------------------------------------------

_SIMCTL_JSON_WATCH = json.dumps({
    "devices": {
        "com.apple.CoreSimulator.SimRuntime.watchOS-26-4": [
            {
                "udid": "C566988B-648F-4B35-AE30-A369C841335E",
                "name": "Apple Watch Series 11 (46mm)",
                "state": "Shutdown",
                "isAvailable": True,
            },
        ],
        "com.apple.CoreSimulator.SimRuntime.watchOS-26-5": [
            {
                "udid": "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE",
                "name": "Apple Watch Series 11 (46mm)",
                "state": "Shutdown",
                "isAvailable": True,
            },
        ],
    }
})


def test_normalize_destination_by_id_rewrites_uuid_to_name_and_os(
    handler: XCUITestRunnerHandler,
) -> None:
    """id=UUID destinations are rewritten to name=...,OS=... using simctl data."""
    mock_result = MagicMock(returncode=0, stdout=_SIMCTL_JSON_WATCH)
    with patch("validator.ui_runner_xcuitest.subprocess.run", return_value=mock_result):
        out = handler._normalize_destination_by_id(
            "platform=watchOS Simulator,id=C566988B-648F-4B35-AE30-A369C841335E"
        )
    assert out == (
        "platform=watchOS Simulator,name=Apple Watch Series 11 (46mm),OS=26.4"
    )


def test_normalize_destination_by_id_passthrough_when_no_id(
    handler: XCUITestRunnerHandler,
) -> None:
    """Destinations without id=<UUID> are returned unchanged (no simctl call)."""
    with patch(
        "validator.ui_runner_xcuitest.subprocess.run",
        side_effect=AssertionError("simctl must not be invoked"),
    ):
        out = handler._normalize_destination_by_id(
            "platform=iOS Simulator,name=iPhone 16"
        )
    assert out == "platform=iOS Simulator,name=iPhone 16"


def test_normalize_destination_by_id_falls_back_when_udid_unknown(
    handler: XCUITestRunnerHandler,
) -> None:
    """Unknown UDIDs fall back to the original destination string."""
    mock_result = MagicMock(returncode=0, stdout=_SIMCTL_JSON_EMPTY)
    with patch("validator.ui_runner_xcuitest.subprocess.run", return_value=mock_result):
        out = handler._normalize_destination_by_id(
            "platform=watchOS Simulator,id=00000000-0000-0000-0000-000000000000"
        )
    assert out == (
        "platform=watchOS Simulator,id=00000000-0000-0000-0000-000000000000"
    )


def test_normalize_destination_by_id_preserves_non_id_qualifiers(
    handler: XCUITestRunnerHandler,
) -> None:
    """Normalization preserves destination qualifiers other than the resolved id."""
    mock_result = MagicMock(returncode=0, stdout=_SIMCTL_JSON_WATCH)
    with patch("validator.ui_runner_xcuitest.subprocess.run", return_value=mock_result):
        out = handler._normalize_destination_by_id(
            "platform=watchOS Simulator,id=C566988B-648F-4B35-AE30-A369C841335E,"
            "variant=paired"
        )
    assert out == (
        "platform=watchOS Simulator,name=Apple Watch Series 11 (46mm),"
        "variant=paired,OS=26.4"
    )


# ---------------------------------------------------------------------------
# .xcresult bundle parsing
# ---------------------------------------------------------------------------

# @spec FR-002: .xcresult parsing — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-002

_XCRESULT_JSON_PNG = {
    "_type": {"_name": "ActionsInvocationRecord"},
    "actions": {
        "_values": [{
            "actionResult": {
                "testsRef": {
                    "id": {"_value": "test-ref-1"}
                }
            },
            "testPlanRunSummaries": {
                "_values": [{
                    "testableSummaries": {
                        "_values": [{
                            "tests": {
                                "_values": [{
                                    "_type": {"_name": "ActionTestAttachment"},
                                    "name": {"_value": "main_screen"},
                                    "uniformTypeIdentifier": {"_value": "public.png"},
                                    "payloadRef": {"id": {"_value": "att-payload-001"}},
                                }]
                            }
                        }]
                    }
                }]
            }
        }]
    }
}


def test_xcresult_attachment_extraction(handler: XCUITestRunnerHandler) -> None:
    """_extract_attachments_from_xcresult_json finds ActionTestAttachment nodes."""
    attachments = handler._extract_attachments_from_xcresult_json(_XCRESULT_JSON_PNG)
    assert len(attachments) == 1
    assert attachments[0]["name"]["_value"] == "main_screen"


def test_xcresult_parsing_png(tmp_path: Path) -> None:
    """_parse_xcresult exports PNG attachments via `xcresulttool export attachments`."""
    bundle_path = tmp_path / "result.xcresult"
    bundle_path.mkdir()
    output_dir = tmp_path / "output"

    def mock_run(cmd, *args, **kwargs):
        joined = " ".join(str(c) for c in cmd)
        mock = MagicMock()
        if "xcresulttool" in joined and "export" in joined and "attachments" in joined:
            # New Xcode 26 API: writes attachments + manifest.json into output-path
            import os
            out_path = None
            for i, arg in enumerate(cmd):
                if arg == "--output-path" and i + 1 < len(cmd):
                    out_path = cmd[i + 1]
                    break
            if out_path:
                os.makedirs(out_path, exist_ok=True)
                (Path(out_path) / "abc-uuid.png").write_bytes(b"\x89PNG\r\n\x1a\n")
                manifest = [{
                    "testIdentifier": "Tests/test_main()",
                    "attachments": [{
                        "exportedFileName": "abc-uuid.png",
                        "suggestedHumanReadableName": (
                            "main_screen_0_"
                            "12345678-90AB-CDEF-1234-567890ABCDEF.png"
                        ),
                    }],
                }]
                (Path(out_path) / "manifest.json").write_text(
                    json.dumps(manifest)
                )
            mock.returncode = 0
            mock.stdout = ""
        else:
            mock.returncode = 0
            mock.stdout = ""
            mock.stderr = ""
        return mock

    handler = XCUITestRunnerHandler(tmp_path)
    with patch("validator.ui_runner_xcuitest.subprocess.run", side_effect=mock_run):
        paths = handler._parse_xcresult(bundle_path, output_dir, "iPhone_16")

    assert len(paths) >= 1
    assert all(p.suffix == ".png" for p in paths)
    # Screen name was recovered from suggestedHumanReadableName.
    assert paths[0].name == "main_screen.png"


def test_xcresult_corrupted_bundle_no_crash(tmp_path: Path) -> None:
    """_parse_xcresult returns empty list (not crash) on corrupted .xcresult."""
    bundle_path = tmp_path / "corrupt.xcresult"
    bundle_path.mkdir()
    output_dir = tmp_path / "output"

    def mock_run(cmd, *args, **kwargs):
        joined = " ".join(str(c) for c in cmd)
        mock = MagicMock()
        if "xcresulttool" in joined and "get" in joined:
            mock.returncode = 0
            mock.stdout = "{{this is not json}}"  # malformed
        else:
            mock.returncode = 0
            mock.stdout = ""
        return mock

    handler = XCUITestRunnerHandler(tmp_path)
    with patch("validator.ui_runner_xcuitest.subprocess.run", side_effect=mock_run):
        paths = handler._parse_xcresult(bundle_path, output_dir, "iPhone_16")

    # Must not raise; returns partial (empty) list
    assert paths == []


def test_xcresult_heic_conversion(tmp_path: Path) -> None:
    """_parse_xcresult calls HEIC→PNG conversion for HEIC attachments."""
    bundle_path = tmp_path / "heic_test.xcresult"
    bundle_path.mkdir()
    output_dir = tmp_path / "output"

    sips_called = []

    def mock_run(cmd, *args, **kwargs):
        joined = " ".join(str(c) for c in cmd)
        mock = MagicMock()
        if "xcresulttool" in joined and "export" in joined and "attachments" in joined:
            # New Xcode 26 API: writes a HEIC + manifest.json into output-path
            import os
            out_path = None
            for i, arg in enumerate(cmd):
                if arg == "--output-path" and i + 1 < len(cmd):
                    out_path = cmd[i + 1]
                    break
            if out_path:
                os.makedirs(out_path, exist_ok=True)
                (Path(out_path) / "heic-uuid.heic").write_bytes(b"ftyp")
                manifest = [{
                    "testIdentifier": "Tests/test_watch()",
                    "attachments": [{
                        "exportedFileName": "heic-uuid.heic",
                        "suggestedHumanReadableName": (
                            "watch_screen_0_"
                            "12345678-90AB-CDEF-1234-567890ABCDEF.heic"
                        ),
                    }],
                }]
                (Path(out_path) / "manifest.json").write_text(
                    json.dumps(manifest)
                )
            mock.returncode = 0
            mock.stdout = ""
        elif "sips" in joined:
            sips_called.append(cmd)
            for i, arg in enumerate(cmd):
                if arg == "--out" and i + 1 < len(cmd):
                    Path(cmd[i + 1]).write_bytes(b"\x89PNG\r\n\x1a\n")
                    break
            mock.returncode = 0
            mock.stdout = ""
        else:
            mock.returncode = 0
            mock.stdout = ""
            mock.stderr = ""
        return mock

    handler = XCUITestRunnerHandler(tmp_path)
    with patch("validator.ui_runner_xcuitest.subprocess.run", side_effect=mock_run):
        handler._parse_xcresult(bundle_path, output_dir, "Watch")

    assert len(sips_called) >= 1


# ---------------------------------------------------------------------------
# Launch arguments injection
# ---------------------------------------------------------------------------

# @spec FR-005: launch_arguments injection
# .specs/features/030-ui-runner-ios-watchos/spec.md#fr-005

def test_launch_arguments_propagated_to_env(handler: XCUITestRunnerHandler) -> None:
    """_build_env includes XCUI_LAUNCH_ARGS when launch_arguments are provided."""
    env = handler._build_env(["--ui-test-mode", "--mock-user=admin"])
    assert env is not None
    assert "XCUI_LAUNCH_ARGS" in env
    decoded = json.loads(env["XCUI_LAUNCH_ARGS"])
    assert decoded == ["--ui-test-mode", "--mock-user=admin"]


def test_launch_arguments_empty_returns_none(handler: XCUITestRunnerHandler) -> None:
    """_build_env returns None when no launch arguments are provided."""
    assert handler._build_env(None) is None
    assert handler._build_env([]) is None


def test_launch_arguments_in_capture_screenshot(tmp_path: Path) -> None:
    """capture_screenshot passes XCUI_LAUNCH_ARGS to xcodebuild subprocess."""
    (tmp_path / "Package.swift").write_text("// swift-tools-version: 5.9\n")
    handler = XCUITestRunnerHandler(tmp_path)

    captured_env: dict[str, str] | None = None

    def mock_run(cmd, *args, **kwargs):
        nonlocal captured_env
        joined = " ".join(str(c) for c in cmd)
        mock = MagicMock()
        if "--find" in joined:
            mock.returncode = 0
            mock.stdout = "/usr/bin/xcodebuild\n"
        elif "-license" in joined:
            mock.returncode = 0
            mock.stdout = ""
            mock.stderr = ""
        elif "xcodebuild" in joined and "test" in joined:
            captured_env = kwargs.get("env")
            mock.returncode = 0
            mock.stdout = ""
            mock.stderr = ""
        else:
            mock.returncode = 0
            mock.stdout = ""
            mock.stderr = ""
        return mock

    with (
        patch("validator.ui_runner_xcuitest.platform.system", return_value="Darwin"),
        patch("validator.ui_runner_xcuitest.subprocess.run", side_effect=mock_run),
    ):
        handler.capture_screenshot(launch_arguments=["--ui-test-mode"])

    if captured_env is not None:
        assert "XCUI_LAUNCH_ARGS" in captured_env
        args = json.loads(captured_env["XCUI_LAUNCH_ARGS"])
        assert "--ui-test-mode" in args


# ---------------------------------------------------------------------------
# watchOS destination filtering
# ---------------------------------------------------------------------------

# @spec FR-004: watchOS destination filtering
# .specs/features/030-ui-runner-ios-watchos/spec.md#fr-004

SAMPLE_DESTINATIONS = [
    {
        "platform": "iOS Simulator",
        "name": "iPhone 16",
        "udid": "auto-detect",
        "default": True,
    },
    {
        "platform": "watchOS Simulator",
        "name": "Apple Watch Series 10 - 46mm",
        "udid": "auto-detect",
        "default": False,
    },
]


@pytest.mark.parametrize(
    "platform, expected_count, expected_platform_str",
    [
        ("ios", 1, "iOS Simulator"),
        ("watchos", 1, "watchOS Simulator"),
    ],
)
def test_filter_destinations_by_platform(
    handler: XCUITestRunnerHandler,
    platform: str,
    expected_count: int,
    expected_platform_str: str,
) -> None:
    """_filter_destinations_by_platform returns only matching platform entries."""
    filtered = handler._filter_destinations_by_platform(SAMPLE_DESTINATIONS, platform)
    assert len(filtered) == expected_count
    for dest in filtered:
        assert expected_platform_str in dest["platform"]


def test_filter_destinations_empty_list(handler: XCUITestRunnerHandler) -> None:
    """_filter_destinations_by_platform handles empty input gracefully."""
    assert handler._filter_destinations_by_platform([], "ios") == []


# ---------------------------------------------------------------------------
# compare_baseline
# ---------------------------------------------------------------------------

def test_compare_baseline_missing_script(handler: XCUITestRunnerHandler) -> None:
    """compare_baseline returns error when pixelmatch-cli.js is not found."""
    result = handler.compare_baseline("baseline.png", "screenshot.png")
    assert result.success is False
    assert result.error is not None
    assert "pixelmatch" in result.error.lower() or "not found" in result.error.lower()


def test_compare_baseline_delegates_to_pixelmatch(tmp_path: Path) -> None:
    """compare_baseline invokes node scripts/pixelmatch-cli.js with correct args."""
    # Create required files
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

    handler = XCUITestRunnerHandler(tmp_path)
    with patch("validator.ui_runner_xcuitest.subprocess.run", side_effect=mock_run):
        handler.compare_baseline(str(baseline), str(screenshot))

    assert "node" in captured_cmd
    assert any("pixelmatch-cli.js" in arg for arg in captured_cmd)


# ---------------------------------------------------------------------------
# Manifest loading
# ---------------------------------------------------------------------------

def test_xcuitest_manifest_path_points_to_ios_yaml() -> None:
    """xcuitest_runner_manifest_path() returns path to ios.yaml."""
    path = xcuitest_runner_manifest_path()
    assert path.name == "ios.yaml"
    assert "ui-runners" in str(path)


def test_load_xcuitest_runner_manifest() -> None:
    """load_xcuitest_runner_manifest() loads a valid YAML dict."""
    manifest = load_xcuitest_runner_manifest()
    assert isinstance(manifest, dict)
    assert "runner" in manifest
    assert manifest["runner"]["id"] == "ios"


# ---------------------------------------------------------------------------
# Coordinated execution markers (pytest.mark.macos)
# These tests require a real macOS + Xcode environment and are skipped in CI.
# ---------------------------------------------------------------------------

@pytest.mark.macos
def test_real_simulator_boot_integration(tmp_path: Path) -> None:  # pragma: no cover
    """Integration: actually boot an iOS simulator (macOS only, skipped in CI)."""
    pytest.skip("Requires real Xcode + iOS Simulator — run manually on macOS")


@pytest.mark.macos
def test_real_xcresult_extraction_integration(tmp_path: Path) -> None:  # pragma: no cover
    """Integration: run real xcodebuild on fixture project (macOS only)."""
    pytest.skip("Requires real Xcode + iOS Simulator — run manually on macOS")
