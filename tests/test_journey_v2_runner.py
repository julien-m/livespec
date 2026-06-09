# LiveSpec traceability anchors
# @spec(AC-016)
# @spec(AC-025)
# @spec(AC-027)
# @spec(AC-028)
# @spec(AC-031)

"""Tests for compiled-only User Journeys v2 run semantics."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from pytest import MonkeyPatch

from tests.test_journey_v2_validation import _write_feature, _write_v2_journey
from validator.journeys.compiler import compile_journeys
from validator.journeys.runner import run_journeys


def _setup_compiled(tmp_path: Path) -> Path:
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    _write_v2_journey(specs)
    result = compile_journeys(tmp_path, journey="onboarding-first-project")
    assert result.error_count == 0
    return specs


def _setup_xcuitest_compiled_project(tmp_path: Path) -> None:
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


def test_run_journeys_executes_manifest_artifacts_without_compiling(tmp_path: Path) -> None:
    """FR-023: run uses compiled artifacts and does not rewrite them."""
    _setup_compiled(tmp_path)
    artifact = tmp_path / "tests" / "e2e" / "journeys" / "onboarding_first_project.spec.ts"
    before = artifact.stat().st_mtime_ns

    result = run_journeys(tmp_path, journey="onboarding-first-project", execute=False)

    assert result.error_count == 0, [issue.code for issue in result.issues]
    assert result.executed == ["onboarding-first-project"]
    assert artifact.stat().st_mtime_ns == before


def test_run_journeys_fails_stale_manifest_without_recompiling(tmp_path: Path) -> None:
    """AC-028: stale compiled manifests fail before native runner execution."""
    specs = _setup_compiled(tmp_path)
    source = specs / "journeys" / "onboarding-first-project" / "journey.yaml"
    source.write_text(source.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
    artifact = tmp_path / "tests" / "e2e" / "journeys" / "onboarding_first_project.spec.ts"
    before = artifact.stat().st_mtime_ns

    result = run_journeys(tmp_path, journey="onboarding-first-project", execute=False)

    assert result.error_count == 1
    assert result.issues[0].code == "journey_compiled_stale"
    assert artifact.stat().st_mtime_ns == before


def test_run_journeys_fails_old_compiler_manifest_without_recompiling(tmp_path: Path) -> None:
    """FR-029: old compiler manifests force explicit regeneration after migrations."""
    specs = _setup_compiled(tmp_path)
    manifest_path = specs / "journeys" / "onboarding-first-project" / "compiled" / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["compiler_version"] = "journeys-v2-1"
    manifest_path.write_text(json.dumps(data), encoding="utf-8")

    result = run_journeys(tmp_path, journey="onboarding-first-project", execute=False)

    assert result.error_count == 1
    assert result.issues[0].code == "journey_compiler_stale"
    assert "compiler version" in result.issues[0].message


def test_run_journeys_reports_manual_and_disabled_without_execution(tmp_path: Path) -> None:
    """FR-027: manual and disabled policies are reported and never executed."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    source = _write_v2_journey(specs)
    source.write_text(
        source.read_text(encoding="utf-8").replace("local: impacted", "local: manual"),
        encoding="utf-8",
    )

    result = run_journeys(tmp_path, journey="onboarding-first-project", execute=False)

    assert result.executed == []
    assert result.manual == ["onboarding-first-project"]


def test_run_journeys_executes_playwright_artifact(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """FR-024: selected Playwright journeys invoke their compiled native artifact."""
    _setup_compiled(tmp_path)
    calls: list[list[str]] = []

    def fake_run(
        argv: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    monkeypatch.setattr("validator.journeys.runner.subprocess.run", fake_run)

    result = run_journeys(tmp_path, journey="onboarding-first-project")

    assert result.error_count == 0, [issue.code for issue in result.issues]
    assert result.executed == ["onboarding-first-project"]
    assert calls == [
        [
            "npx",
            "playwright",
            "test",
            "tests/e2e/journeys/onboarding_first_project.spec.ts",
        ]
    ]


def test_run_journeys_reports_native_runner_failure(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """AC-031: native runner failures block the journey gate."""
    _setup_compiled(tmp_path)

    def fake_run(
        argv: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="failed")

    monkeypatch.setattr("validator.journeys.runner.subprocess.run", fake_run)

    result = run_journeys(tmp_path, journey="onboarding-first-project")

    assert result.executed == []
    assert result.error_count == 1
    assert result.issues[0].code == "journey_native_run_failed"
    assert "failed" in result.issues[0].message


def test_run_journeys_executes_xcuitest_with_only_testing(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
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
    devices = {
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
    ],
)
def test_run_journeys_reports_simulator_discovery_errors(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
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
        if failure == "missing":
            raise FileNotFoundError("xcrun")
        if failure == "timeout":
            raise subprocess.TimeoutExpired(argv, timeout=30)
        if failure == "nonzero":
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="simctl unavailable")
        if failure == "invalid_json_root_shape":
            return subprocess.CompletedProcess(argv, 0, stdout="{}", stderr="")
        if failure == "invalid_json_devices_shape":
            return subprocess.CompletedProcess(argv, 0, stdout='{"devices": []}', stderr="")
        if failure == "invalid_is_available_shape":
            devices = {
                "devices": {
                    "com.apple.CoreSimulator.SimRuntime.iOS-26-4": [
                        {"name": "iPhone 17", "udid": "IPHONE-17", "isAvailable": "false"},
                    ],
                },
            }
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(devices), stderr="")
        if failure == "invalid_runtime_devices_shape":
            devices = {"devices": {"com.apple.CoreSimulator.SimRuntime.iOS-26-4": {}}}
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(devices), stderr="")
        if failure == "invalid_device_entry_shape":
            devices = {"devices": {"com.apple.CoreSimulator.SimRuntime.iOS-26-4": ["iPhone 17"]}}
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(devices), stderr="")
        if failure == "invalid_device_identity_shape":
            devices = {
                "devices": {
                    "com.apple.CoreSimulator.SimRuntime.iOS-26-4": [
                        {"name": "iPhone 17", "udid": None, "isAvailable": True},
                    ],
                },
            }
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(devices), stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout="{not json", stderr="")

    monkeypatch.setattr("validator.journeys.runner.subprocess.run", fake_run)

    result = run_journeys(tmp_path, journey="onboarding-first-project")

    assert result.executed == []
    assert result.error_count == 1
    assert result.issues[0].code == expected_code
    assert expected_message in result.issues[0].message


def test_run_journeys_reports_no_available_simulator_for_matching_platform(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """FR-024: XCUITest discovery fails clearly when no matching simulator is usable."""
    _setup_xcuitest_compiled_project(tmp_path)
    monkeypatch.delenv("LIVESPEC_XCODE_DESTINATION", raising=False)
    devices = {
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
    monkeypatch: MonkeyPatch,
) -> None:
    """FR-024: watchOS XCUITest journeys resolve and boot a watch simulator."""
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
    compiled = tmp_path / "STRAPTUITests" / "Journeys" / "OnboardingFirstProjectJourney.swift"
    watch_dir = tmp_path / "STRAPTWATCHUITests" / "Journeys"
    watch_dir.mkdir(parents=True)
    watch_artifact = watch_dir / "OnboardingFirstProjectWatchJourney.swift"
    compiled.rename(watch_artifact)
    manifest_path = specs / "journeys" / "onboarding-first-project" / "compiled" / "manifest.json"
    manifest_data: object = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest_data, dict):
        raise AssertionError("compiled manifest JSON must be an object")
    manifest = manifest_data
    manifest["native_output_paths"] = [
        "STRAPTWATCHUITests/Journeys/OnboardingFirstProjectWatchJourney.swift"
    ]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / "App.xcodeproj").mkdir()
    (tmp_path / "App.xcodeproj" / "project.pbxproj").write_text("", encoding="utf-8")
    calls: list[list[str]] = []
    devices = {
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
    assert calls[1] == ["xcrun", "simctl", "boot", "WATCH-11"]
    assert calls[2] == ["xcrun", "simctl", "bootstatus", "WATCH-11", "-b"]
    command = calls[3]
    destination = command[command.index("-destination") + 1]
    assert destination == "platform=watchOS Simulator,id=WATCH-11"
    assert "-only-testing:STRAPTWATCHUITests/OnboardingFirstProjectWatchJourney" in command


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
