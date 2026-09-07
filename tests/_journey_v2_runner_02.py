"""Preserved test cases and fixtures for test_journey_v2_runner.py."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Unpack

import pytest

from tests._journey_v2_runner_01 import (
    _install_simctl_fake,
    _JsonValue,
    _RunKwargs,
    _setup_xcuitest_compiled_project,
)
from tests.test_journey_v2_validation import _write_feature, _write_v2_journey
from validator.journeys.compiler import compile_journeys
from validator.journeys.runner import run_journeys


def test_run_journeys_executes_xcuitest_with_only_testing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-024: XCUITest journeys boot an available simulator and run one generated class."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    source = _write_v2_journey(specs)
    source.write_text(
        source.read_text(encoding="utf-8")
        .replace("runner: playwright", "runner: xcuitest")
        .replace("route: /signup", "route: strapt://signup"),
        encoding="utf-8",
    )
    compile_result = compile_journeys(tmp_path, journey="onboarding-first-project")
    assert compile_result.error_count == 0
    (tmp_path / "App.xcodeproj").mkdir()
    (tmp_path / "App.xcodeproj" / "project.pbxproj").write_text("", encoding="utf-8")
    calls: list[list[str]] = []
    devices: _JsonValue = {
        "devices": {
            "com.apple.CoreSimulator.SimRuntime.iOS-9-3": [
                {"name": "iPhone 6", "udid": "IPHONE-OLD", "isAvailable": True},
            ],
            "com.apple.CoreSimulator.SimRuntime.iOS-26-4": [
                {"name": "iPhone 16", "udid": "IPHONE-16", "isAvailable": False},
                {"name": "iPhone 17", "udid": "IPHONE-17", "isAvailable": True},
            ],
        },
    }
    monkeypatch.delenv("LIVESPEC_XCODE_DESTINATION", raising=False)

    def fake_run(
        argv: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        if argv[:5] == ["xcrun", "simctl", "list", "devices", "available"]:
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(devices), stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    monkeypatch.setattr("validator.journeys.runner.subprocess.run", fake_run)

    result = run_journeys(tmp_path, journey="onboarding-first-project")

    assert result.error_count == 0, [issue.code for issue in result.issues]
    assert calls[1] == ["xcrun", "simctl", "boot", "IPHONE-17"]
    assert calls[2] == ["xcrun", "simctl", "bootstatus", "IPHONE-17", "-b"]
    command = calls[3]
    assert command[:2] == ["xcodebuild", "test"]
    destination = command[command.index("-destination") + 1]
    assert destination == "platform=iOS Simulator,id=IPHONE-17"
    assert "iPhone 16" not in destination
    assert "-only-testing:STRAPTUITests/OnboardingFirstProjectJourney" in command


def test_run_journeys_records_xcuitest_destination_and_udid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-001: XCUITest records expose the selected Xcode destination and UDID."""
    _setup_xcuitest_compiled_project(tmp_path)
    monkeypatch.setenv("LIVESPEC_XCODE_DESTINATION", "platform=iOS Simulator,id=IPHONE-17")

    def fake_run(
        argv: list[str],
        **_kwargs: Unpack[_RunKwargs],
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    monkeypatch.setattr("validator.journeys.runner.subprocess.run", fake_run)

    result = run_journeys(tmp_path, journey="onboarding-first-project")

    assert result.error_count == 0, [issue.code for issue in result.issues]
    assert result.runs[0].runner == "xcuitest"
    assert result.runs[0].udid == "IPHONE-17"
    assert result.runs[0].destination == "platform=iOS Simulator,id=IPHONE-17"
    assert result.runs[0].platform == "ios"
    assert "id=IPHONE-17" in result.runs[0].command


def test_run_journeys_writes_last_run_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-003: each attempted journey writes the latest run receipt."""
    _setup_xcuitest_compiled_project(tmp_path)
    monkeypatch.setenv("LIVESPEC_XCODE_DESTINATION", "platform=iOS Simulator,id=IPHONE-17")

    def fake_run(
        argv: list[str],
        **_kwargs: Unpack[_RunKwargs],
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    monkeypatch.setattr("validator.journeys.runner.subprocess.run", fake_run)

    result = run_journeys(tmp_path, journey="onboarding-first-project")

    assert result.error_count == 0
    receipt_path = (
        tmp_path / ".specs" / "journeys" / "onboarding-first-project" / "runs" / "last-run.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["udid"] == "IPHONE-17"
    assert receipt["destination"] == "platform=iOS Simulator,id=IPHONE-17"


def test_run_journeys_uses_bounded_xcuitest_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """FR-024: hung XCUITest runs fail faster than the generic native timeout."""
    _setup_xcuitest_compiled_project(tmp_path)
    devices: _JsonValue = {
        "devices": {
            "com.apple.CoreSimulator.SimRuntime.iOS-26-5": [
                {
                    "name": "iPhone 17 Pro",
                    "udid": "FRESH-SHUTDOWN",
                    "state": "Shutdown",
                    "isAvailable": True,
                },
            ],
        },
    }
    calls: list[tuple[list[str], int]] = []

    def fake_run(
        argv: list[str],
        **kwargs: Unpack[_RunKwargs],
    ) -> subprocess.CompletedProcess[str]:
        timeout = kwargs.get("timeout")
        if not isinstance(timeout, int):
            raise AssertionError("runner timeout must be an int")
        calls.append((list(argv), timeout))
        if argv[:5] == ["xcrun", "simctl", "list", "devices", "available"]:
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(devices), stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    monkeypatch.delenv("LIVESPEC_XCODE_DESTINATION", raising=False)
    monkeypatch.setattr("validator.journeys.runner.subprocess.run", fake_run)

    result = run_journeys(tmp_path, journey="onboarding-first-project")

    assert result.error_count == 0, [issue.code for issue in result.issues]
    xcodebuild_calls = [
        (argv, timeout) for argv, timeout in calls if argv[:2] == ["xcodebuild", "test"]
    ]
    assert len(xcodebuild_calls) == 1
    assert xcodebuild_calls[0][1] == 120
    assert "timeout=120s" in capsys.readouterr().err


def test_run_journeys_uses_surfaces_yaml_for_shared_watch_xcuitest_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-024: shared Swift journey files still run against the declared watch surface."""
    _setup_shared_watch_xcuitest_project(tmp_path)
    calls: list[list[str]] = []

    def fake_run(
        argv: list[str],
        **_kwargs: Unpack[_RunKwargs],
    ) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    monkeypatch.delenv("LIVESPEC_XCODE_DESTINATION", raising=False)
    monkeypatch.delenv("LIVESPEC_XCODE_SCHEME", raising=False)
    monkeypatch.setattr("validator.journeys.runner.subprocess.run", fake_run)

    result = run_journeys(tmp_path, journey="onboarding-first-project")

    assert result.error_count == 0, [issue.code for issue in result.issues]
    command = next(argv for argv in calls if argv[:2] == ["xcodebuild", "test"])
    assert command[command.index("-scheme") + 1] == "STRAPT Watch App"
    assert command[command.index("-destination") + 1] == (
        "platform=watchOS Simulator,id=WATCH-CONFIG"
    )
    assert "-only-testing:STRAPTWATCHUITests/OnboardingFirstProjectJourney" in command
    assert ["xcrun", "simctl", "boot", "WATCH-CONFIG"] in calls
    assert all("IPHONE-CONFIG" not in " ".join(argv) for argv in calls)


# @spec FR-024: XCUITest simulator destination ranking and boot orchestration.
def test_run_journeys_prefers_shutdown_simulator_over_booted_stale_device(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-024: avoid reusing booted CoreSimulator devices that can wedge XCTest startup."""
    _setup_xcuitest_compiled_project(tmp_path)
    devices: _JsonValue = {
        "devices": {
            "com.apple.CoreSimulator.SimRuntime.iOS-26-5": [
                {
                    "name": "iPhone 17 Pro",
                    "udid": "BOOTED-STUCK",
                    "state": "Booted",
                    "isAvailable": True,
                },
                {
                    "name": "iPhone 17 Pro Max",
                    "udid": "FRESH-SHUTDOWN",
                    "state": "Shutdown",
                    "isAvailable": True,
                },
                {
                    "name": "iPad Air 11-inch",
                    "udid": "IPAD-SHUTDOWN",
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
    assert calls[1] == ["xcrun", "simctl", "boot", "FRESH-SHUTDOWN"]
    assert calls[2] == ["xcrun", "simctl", "bootstatus", "FRESH-SHUTDOWN", "-b"]
    command = calls[3]
    destination = command[command.index("-destination") + 1]
    assert destination == "platform=iOS Simulator,id=FRESH-SHUTDOWN"


# @spec FR-024: XCUITest simulator destination ranking and boot orchestration.
def test_run_journeys_prefers_iphone_family_before_shutdown_ipad(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-024: iOS journeys stay on iPhone even when an iPad is shutdown."""
    _setup_xcuitest_compiled_project(tmp_path)
    devices: _JsonValue = {
        "devices": {
            "com.apple.CoreSimulator.SimRuntime.iOS-26-5": [
                {
                    "name": "iPad Air 11-inch",
                    "udid": "IPAD-SHUTDOWN",
                    "state": "Shutdown",
                    "isAvailable": True,
                },
                {
                    "name": "iPhone 17 Pro",
                    "udid": "IPHONE-BOOTED",
                    "state": "Booted",
                    "isAvailable": True,
                },
            ],
        },
    }
    monkeypatch.delenv("LIVESPEC_XCODE_DESTINATION", raising=False)
    calls = _install_simctl_fake(monkeypatch, devices)

    result = run_journeys(tmp_path, journey="onboarding-first-project")

    assert result.error_count == 0, [issue.code for issue in result.issues]
    assert calls[1] == ["xcrun", "simctl", "bootstatus", "IPHONE-BOOTED", "-b"]
    destination = calls[2][calls[2].index("-destination") + 1]
    assert destination == "platform=iOS Simulator,id=IPHONE-BOOTED"


# @spec FR-024: XCUITest simulator destination ranking and boot orchestration.
def test_run_journeys_prefers_shutdown_iphone_over_newer_booted_iphone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-024: shutdown iPhones beat booted iPhones across runtime versions."""
    _setup_xcuitest_compiled_project(tmp_path)
    devices: _JsonValue = {
        "devices": {
            "com.apple.CoreSimulator.SimRuntime.iOS-26-5": [
                {
                    "name": "iPhone 17 Pro",
                    "udid": "NEWER-BOOTED",
                    "state": "Booted",
                    "isAvailable": True,
                },
            ],
            "com.apple.CoreSimulator.SimRuntime.iOS-26-4": [
                {
                    "name": "iPhone 16 Pro",
                    "udid": "OLDER-SHUTDOWN",
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
    assert calls[1] == ["xcrun", "simctl", "boot", "OLDER-SHUTDOWN"]
    destination = calls[3][calls[3].index("-destination") + 1]
    assert destination == "platform=iOS Simulator,id=OLDER-SHUTDOWN"


def _setup_shared_watch_xcuitest_project(tmp_path: Path) -> None:
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    source = _write_v2_journey(specs)
    source.write_text(
        source.read_text(encoding="utf-8")
        .replace("surface: web", "surface: watchos")
        .replace("runner: playwright", "runner: xcuitest")
        .replace("route: /signup", "route: strapt://signup"),
        encoding="utf-8",
    )
    (specs / "surfaces.yaml").write_text(
        """
surfaces:
  - id: straptuitests
    name: STRAPTUITests
    runner: xcuitest
    platform: ios
    runnerConfig:
      scheme: STRAPT
      onlyTesting: STRAPTUITests
      destination: platform=iOS Simulator,id=IPHONE-CONFIG
  - id: straptwatchuitests
    name: STRAPTWATCHUITests
    runner: xcuitest
    platform: watchos
    runnerConfig:
      scheme: STRAPT Watch App
      onlyTesting: STRAPTWATCHUITests
      destination: platform=watchOS Simulator,id=WATCH-CONFIG
""".lstrip(),
        encoding="utf-8",
    )
    compile_result = compile_journeys(tmp_path, journey="onboarding-first-project")
    assert compile_result.error_count == 0
    (tmp_path / "App.xcodeproj").mkdir()
    (tmp_path / "App.xcodeproj" / "project.pbxproj").write_text("", encoding="utf-8")
