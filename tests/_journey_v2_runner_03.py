"""Preserved test cases and fixtures for test_journey_v2_runner.py."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Unpack
from unittest.mock import Mock

import pytest

from tests._journey_v2_runner_01 import (
    _install_simctl_fake,
    _JsonValue,
    _RunKwargs,
    _setup_compiled,
    _setup_watch_xcuitest_compiled_project,
    _setup_xcuitest_compiled_project,
)
from validator.journeys.runner import run_journeys


@pytest.mark.parametrize(
    ("failure", "expected_code", "expected_message"),
    [
        (
            "missing",
            "journey_simulator_discovery_missing",
            "xcrun simctl not found",
        ),
        (
            "timeout",
            "journey_simulator_discovery_timeout",
            "timed out",
        ),
        (
            "nonzero",
            "journey_simulator_discovery_failed",
            "simctl unavailable",
        ),
        (
            "invalid_json",
            "journey_simulator_discovery_invalid_json",
            "invalid JSON",
        ),
        (
            "invalid_json_root_shape",
            "journey_simulator_discovery_invalid_json",
            "JSON missing object field: devices",
        ),
        (
            "invalid_json_devices_shape",
            "journey_simulator_discovery_invalid_json",
            "JSON missing object field: devices",
        ),
        (
            "invalid_is_available_shape",
            "journey_simulator_discovery_invalid_json",
            "isAvailable must be a boolean",
        ),
        (
            "invalid_runtime_devices_shape",
            "journey_simulator_discovery_invalid_json",
            "runtime device entry must be a list",
        ),
        (
            "invalid_device_entry_shape",
            "journey_simulator_discovery_invalid_json",
            "simctl device entry must be an object",
        ),
        (
            "invalid_device_identity_shape",
            "journey_simulator_discovery_invalid_json",
            "device fields name and udid must be strings",
        ),
        (
            "invalid_state_shape",
            "journey_simulator_discovery_invalid_json",
            "simctl device field state must be a string when present",
        ),
    ],
)
def test_run_journeys_reports_simulator_discovery_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    expected_code: str,
    expected_message: str,
) -> None:
    """FR-024: simulator discovery failures become blocking journey issues."""
    _setup_xcuitest_compiled_project(tmp_path)
    monkeypatch.delenv("LIVESPEC_XCODE_DESTINATION", raising=False)

    def fake_run(
        argv: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        if argv[:5] != ["xcrun", "simctl", "list", "devices", "available"]:
            return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")
        return _simctl_failure_result(argv, failure)

    monkeypatch.setattr("validator.journeys.runner.subprocess.run", fake_run)

    result = run_journeys(tmp_path, journey="onboarding-first-project")

    assert result.executed == []
    assert result.error_count == 1
    assert result.issues[0].code == expected_code
    assert expected_message in result.issues[0].message


def test_run_journeys_reports_no_available_simulator_for_matching_platform(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-024: XCUITest discovery fails clearly when no matching simulator is usable."""
    _setup_xcuitest_compiled_project(tmp_path)
    monkeypatch.delenv("LIVESPEC_XCODE_DESTINATION", raising=False)
    devices: _JsonValue = {
        "devices": {
            "com.apple.CoreSimulator.SimRuntime.iOS-26-4": [
                {"name": "iPhone 17", "udid": "IPHONE-17", "isAvailable": False},
            ],
            "com.apple.CoreSimulator.SimRuntime.watchOS-26-4": [
                {"name": "Apple Watch Series 11", "udid": "WATCH-11", "isAvailable": True},
            ],
        },
    }

    def fake_run(
        argv: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        if argv[:5] == ["xcrun", "simctl", "list", "devices", "available"]:
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(devices), stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    monkeypatch.setattr("validator.journeys.runner.subprocess.run", fake_run)

    result = run_journeys(tmp_path, journey="onboarding-first-project")

    assert result.executed == []
    assert result.error_count == 1
    assert result.issues[0].code == "journey_simulator_unavailable"
    assert "No available iOS simulator" in result.issues[0].message


def test_run_journeys_executes_watch_xcuitest_on_available_watch_simulator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-024: watchOS XCUITest journeys resolve and boot a watch simulator."""
    _setup_watch_xcuitest_compiled_project(tmp_path)
    devices: _JsonValue = {
        "devices": {
            "com.apple.CoreSimulator.SimRuntime.iOS-26-4": [
                {"name": "iPhone 17", "udid": "IPHONE-17", "isAvailable": True},
            ],
            "com.apple.CoreSimulator.SimRuntime.watchOS-26-4": [
                {"name": "Apple Watch Series 11", "udid": "WATCH-11", "isAvailable": True},
            ],
        },
    }
    monkeypatch.delenv("LIVESPEC_XCODE_DESTINATION", raising=False)
    calls = _install_simctl_fake(monkeypatch, devices)

    result = run_journeys(tmp_path, journey="onboarding-first-project")

    assert result.error_count == 0, [issue.code for issue in result.issues]
    assert calls[1] == ["xcrun", "simctl", "boot", "WATCH-11"]
    assert calls[2] == ["xcrun", "simctl", "bootstatus", "WATCH-11", "-b"]
    command = calls[3]
    destination = command[command.index("-destination") + 1]
    assert destination == "platform=watchOS Simulator,id=WATCH-11"
    assert "-only-testing:STRAPTWATCHUITests/OnboardingFirstProjectWatchJourney" in command


# @spec FR-024: XCUITest simulator destination ranking and boot orchestration.
def test_run_journeys_prefers_shutdown_watch_over_newer_booted_watch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-024: shutdown Apple Watch devices beat booted watches across runtimes."""
    _setup_watch_xcuitest_compiled_project(tmp_path)
    devices: _JsonValue = {
        "devices": {
            "com.apple.CoreSimulator.SimRuntime.watchOS-26-5": [
                {
                    "name": "Apple Watch Series 11",
                    "udid": "NEWER-WATCH-BOOTED",
                    "state": "Booted",
                    "isAvailable": True,
                },
            ],
            "com.apple.CoreSimulator.SimRuntime.watchOS-26-4": [
                {
                    "name": "Apple Watch Series 10",
                    "udid": "OLDER-WATCH-SHUTDOWN",
                    "state": "Shutdown",
                    "isAvailable": True,
                },
            ],
        },
    }
    monkeypatch.delenv("LIVESPEC_XCODE_DESTINATION", raising=False)
    calls = _install_simctl_fake(monkeypatch, devices)

    result = run_journeys(tmp_path, journey="onboarding-first-project")

    assert result.error_count == 0, [issue.code for issue in result.issues]
    assert calls[1] == ["xcrun", "simctl", "boot", "OLDER-WATCH-SHUTDOWN"]
    destination = calls[3][calls[3].index("-destination") + 1]
    assert destination == "platform=watchOS Simulator,id=OLDER-WATCH-SHUTDOWN"


def test_run_journeys_supports_injected_executor(tmp_path: Path) -> None:
    """FR-024: callers can test runner dispatch without monkeypatching subprocess globally."""
    _setup_compiled(tmp_path)
    executor = Mock(return_value=subprocess.CompletedProcess(["npx"], 0, "", ""))

    result = run_journeys(tmp_path, journey="onboarding-first-project", executor=executor)

    assert result.error_count == 0
    executor.assert_called_once()


def test_run_journeys_rejects_missing_compiled_artifact(tmp_path: Path) -> None:
    """FR-024: manifests cannot pass when their native artifact vanished."""
    _setup_compiled(tmp_path)
    artifact = tmp_path / "tests" / "e2e" / "journeys" / "onboarding_first_project.spec.ts"
    artifact.unlink()

    result = run_journeys(tmp_path, journey="onboarding-first-project")

    assert result.executed == []
    assert result.error_count == 1
    assert result.issues[0].code == "journey_compiled_missing"


def test_run_journeys_rejects_unsupported_manifest_runner(tmp_path: Path) -> None:
    """FR-024: manifest runner values cannot select arbitrary executables."""
    specs = _setup_compiled(tmp_path)
    manifest_path = specs / "journeys" / "onboarding-first-project" / "compiled" / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["runner"] = "open"
    manifest_path.write_text(json.dumps(data), encoding="utf-8")

    result = run_journeys(tmp_path, journey="onboarding-first-project")

    assert result.executed == []
    assert result.error_count == 1
    assert result.issues[0].code == "journey_native_runner_unsupported"


def test_run_journeys_reclassifies_bootstrap_failure_prefix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-010: the bootstrap prefix on non-zero exit reclassifies the issue."""
    _setup_compiled(tmp_path)
    calls: list[list[str]] = []
    bootstrap_line = "JOURNEY_BOOTSTRAP_FAILURE: marker 'session-list' not found within 15s"

    def fake_run(
        argv: list[str],
        **_kwargs: Unpack[_RunKwargs],
    ) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        return subprocess.CompletedProcess(
            argv,
            65,
            stdout=f"Test Suite started\n{bootstrap_line}\nTest Suite failed",
            stderr="xcodebuild summary",
        )

    monkeypatch.setattr("validator.journeys.runner.subprocess.run", fake_run)

    result = run_journeys(tmp_path, journey="onboarding-first-project")

    assert result.error_count == 1
    issue = result.issues[0]
    assert issue.code == "journey_bootstrap_marker_missing"
    # The matched line leads the message; the full output is appended after.
    assert issue.message.splitlines()[0] == bootstrap_line
    assert "Test Suite failed" in issue.message
    assert "xcodebuild summary" in issue.message
    # No xcresult parsing: only the native runner command itself was executed.
    assert len(calls) == 1
    assert all("xcresult" not in part for call in calls for part in call)


def test_run_journeys_keeps_native_run_failed_without_prefix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-010: non-zero exits without the prefix keep journey_native_run_failed."""
    _setup_compiled(tmp_path)

    def fake_run(
        argv: list[str],
        **_kwargs: Unpack[_RunKwargs],
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 1, stdout="business assertion failed", stderr="")

    monkeypatch.setattr("validator.journeys.runner.subprocess.run", fake_run)

    result = run_journeys(tmp_path, journey="onboarding-first-project")

    assert result.error_count == 1
    assert result.issues[0].code == "journey_native_run_failed"


def _simctl_failure_result(argv: list[str], failure: str) -> subprocess.CompletedProcess[str]:
    if failure == "missing":
        raise FileNotFoundError("xcrun")
    if failure == "timeout":
        raise subprocess.TimeoutExpired(argv, timeout=30)
    if failure == "nonzero":
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="simctl unavailable")
    return subprocess.CompletedProcess(argv, 0, stdout=_invalid_simctl_output(failure), stderr="")


def _invalid_simctl_output(failure: str) -> str:
    if failure == "invalid_json_root_shape":
        return "{}"
    if failure == "invalid_json_devices_shape":
        return '{"devices": []}'
    if failure == "invalid_is_available_shape":
        invalid_availability_payload: _JsonValue = {
            "devices": {
                "com.apple.CoreSimulator.SimRuntime.iOS-26-4": [
                    {"name": "iPhone 17", "udid": "IPHONE-17", "isAvailable": "false"}
                ]
            }
        }
        return json.dumps(invalid_availability_payload)
    if failure == "invalid_runtime_devices_shape":
        invalid_runtime_payload: _JsonValue = {
            "devices": {"com.apple.CoreSimulator.SimRuntime.iOS-26-4": {}}
        }
        return json.dumps(invalid_runtime_payload)
    if failure == "invalid_device_entry_shape":
        invalid_entry_payload: _JsonValue = {
            "devices": {"com.apple.CoreSimulator.SimRuntime.iOS-26-4": ["iPhone 17"]}
        }
        return json.dumps(invalid_entry_payload)
    if failure == "invalid_device_identity_shape":
        invalid_identity_payload: _JsonValue = {
            "devices": {
                "com.apple.CoreSimulator.SimRuntime.iOS-26-4": [
                    {"name": "iPhone 17", "udid": None, "isAvailable": True}
                ]
            }
        }
        return json.dumps(invalid_identity_payload)
    if failure == "invalid_state_shape":
        invalid_state_payload: _JsonValue = {
            "devices": {
                "com.apple.CoreSimulator.SimRuntime.iOS-26-4": [
                    {"name": "iPhone 17", "udid": "IPHONE-17", "state": None, "isAvailable": True}
                ]
            }
        }
        return json.dumps(invalid_state_payload)
    return "{not json"
