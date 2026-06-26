# @spec(AC-015)

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
from typing import NotRequired, TypeAlias, TypedDict, Unpack
from unittest.mock import Mock

import pytest

from tests.test_journey_v2_validation import _write_feature, _write_v2_journey
from validator.journeys.compiler import compile_journeys
from validator.journeys.runner import run_journeys

_JsonValue: TypeAlias = (
    None | bool | int | float | str | list["_JsonValue"] | dict[str, "_JsonValue"]
)


class _RunKwargs(TypedDict, total=False):
    cwd: NotRequired[str]
    capture_output: NotRequired[bool]
    text: NotRequired[bool]
    timeout: NotRequired[int]
    check: NotRequired[bool]


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


def _setup_watch_xcuitest_compiled_project(tmp_path: Path) -> None:
    """Create a watchOS fixture by moving the compiled artifact and manifest path."""
    _setup_xcuitest_compiled_project(tmp_path)
    specs = tmp_path / ".specs"
    compiled = tmp_path / "STRAPTUITests" / "Journeys" / "OnboardingFirstProjectJourney.swift"
    watch_dir = tmp_path / "STRAPTWATCHUITests" / "Journeys"
    watch_dir.mkdir(parents=True)
    watch_artifact = watch_dir / "OnboardingFirstProjectWatchJourney.swift"
    compiled.rename(watch_artifact)
    manifest_path = specs / "journeys" / "onboarding-first-project" / "compiled" / "manifest.json"
    manifest_data: _JsonValue = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest_data, dict):
        raise AssertionError("compiled manifest JSON must be an object")
    native_output_paths: list[_JsonValue] = [
        "STRAPTWATCHUITests/Journeys/OnboardingFirstProjectWatchJourney.swift"
    ]
    manifest_data["native_output_paths"] = native_output_paths
    manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")


def _install_simctl_fake(
    monkeypatch: pytest.MonkeyPatch,
    devices: _JsonValue,
) -> list[list[str]]:
    """Monkeypatch runner subprocess calls and return captured argv calls."""
    calls: list[list[str]] = []

    def fake_run(
        argv: list[str],
        **_kwargs: Unpack[_RunKwargs],
    ) -> subprocess.CompletedProcess[str]:
        # Match subprocess.run keyword arguments; this fake only inspects argv.
        calls.append(list(argv))
        if argv[:5] == ["xcrun", "simctl", "list", "devices", "available"]:
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(devices), stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    monkeypatch.setattr("validator.journeys.runner.subprocess.run", fake_run)
    return calls


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
    monkeypatch: pytest.MonkeyPatch,
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
    monkeypatch: pytest.MonkeyPatch,
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


def test_run_journeys_preserves_native_runner_stdout_and_stderr_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-031: native runner failures keep both process streams for diagnosis."""
    _setup_compiled(tmp_path)

    def fake_run(
        argv: list[str],
        **_kwargs: Unpack[_RunKwargs],
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            argv,
            1,
            stdout="assertion detail from stdout",
            stderr="xcodebuild summary from stderr",
        )

    monkeypatch.setattr("validator.journeys.runner.subprocess.run", fake_run)

    result = run_journeys(tmp_path, journey="onboarding-first-project")

    assert result.error_count == 1
    assert "xcodebuild summary from stderr" in result.issues[0].message
    assert "assertion detail from stdout" in result.issues[0].message


def test_run_journeys_reports_timeout_with_captured_native_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-031: timeouts include captured native output when subprocess exposes it."""
    _setup_compiled(tmp_path)

    def fake_run(
        argv: list[str],
        **_kwargs: Unpack[_RunKwargs],
    ) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(
            argv,
            600,
            output="partial stdout before timeout",
            stderr="partial stderr before timeout",
        )

    monkeypatch.setattr("validator.journeys.runner.subprocess.run", fake_run)

    result = run_journeys(tmp_path, journey="onboarding-first-project")

    assert result.error_count == 1
    assert result.issues[0].code == "journey_native_run_timeout"
    assert "timed out after 600s" in result.issues[0].message
    assert "partial stderr before timeout" in result.issues[0].message
    assert "partial stdout before timeout" in result.issues[0].message


def test_run_journeys_emits_native_runner_progress_to_stderr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """FR-024: JSON callers still get stderr progress while native runners execute."""
    _setup_compiled(tmp_path)

    def fake_run(
        argv: list[str],
        **_kwargs: Unpack[_RunKwargs],
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    monkeypatch.setattr("validator.journeys.runner.subprocess.run", fake_run)

    result = run_journeys(tmp_path, journey="onboarding-first-project")

    assert result.error_count == 0
    stderr = capsys.readouterr().err
    assert "livespec journey run: executing onboarding-first-project" in stderr
    assert "timeout=600s" in stderr
    assert "npx playwright test" in stderr


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
            invalid_availability_payload: _JsonValue = {
                "devices": {
                    "com.apple.CoreSimulator.SimRuntime.iOS-26-4": [
                        {"name": "iPhone 17", "udid": "IPHONE-17", "isAvailable": "false"},
                    ],
                },
            }
            return subprocess.CompletedProcess(
                argv, 0, stdout=json.dumps(invalid_availability_payload), stderr=""
            )
        if failure == "invalid_runtime_devices_shape":
            invalid_runtime_payload: _JsonValue = {
                "devices": {"com.apple.CoreSimulator.SimRuntime.iOS-26-4": {}}
            }
            return subprocess.CompletedProcess(
                argv, 0, stdout=json.dumps(invalid_runtime_payload), stderr=""
            )
        if failure == "invalid_device_entry_shape":
            invalid_entry_payload: _JsonValue = {
                "devices": {"com.apple.CoreSimulator.SimRuntime.iOS-26-4": ["iPhone 17"]}
            }
            return subprocess.CompletedProcess(
                argv, 0, stdout=json.dumps(invalid_entry_payload), stderr=""
            )
        if failure == "invalid_device_identity_shape":
            invalid_identity_payload: _JsonValue = {
                "devices": {
                    "com.apple.CoreSimulator.SimRuntime.iOS-26-4": [
                        {"name": "iPhone 17", "udid": None, "isAvailable": True},
                    ],
                },
            }
            return subprocess.CompletedProcess(
                argv, 0, stdout=json.dumps(invalid_identity_payload), stderr=""
            )
        if failure == "invalid_state_shape":
            invalid_state_payload: _JsonValue = {
                "devices": {
                    "com.apple.CoreSimulator.SimRuntime.iOS-26-4": [
                        {
                            "name": "iPhone 17",
                            "udid": "IPHONE-17",
                            "state": None,
                            "isAvailable": True,
                        },
                    ],
                },
            }
            return subprocess.CompletedProcess(
                argv, 0, stdout=json.dumps(invalid_state_payload), stderr=""
            )
        return subprocess.CompletedProcess(argv, 0, stdout="{not json", stderr="")

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


def test_run_journeys_ignores_prefix_on_passing_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Edge case: stray prefix text in a passing run changes nothing."""
    _setup_compiled(tmp_path)

    def fake_run(
        argv: list[str],
        **_kwargs: Unpack[_RunKwargs],
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout="log noise JOURNEY_BOOTSTRAP_FAILURE: not a real failure",
            stderr="",
        )

    monkeypatch.setattr("validator.journeys.runner.subprocess.run", fake_run)

    result = run_journeys(tmp_path, journey="onboarding-first-project")

    assert result.error_count == 0, [issue.code for issue in result.issues]
    assert result.executed == ["onboarding-first-project"]


def test_run_journeys_fails_stale_contract_hash_without_recompiling(tmp_path: Path) -> None:
    """AC-009: a fixtures.yaml change after compilation marks artifacts stale."""
    specs = _setup_compiled(tmp_path)
    contract_path = specs / "journeys" / "fixtures.yaml"
    contract_path.write_text("schema_version: 1\n", encoding="utf-8")

    result = run_journeys(tmp_path, journey="onboarding-first-project", execute=False)

    assert result.error_count == 1
    assert result.issues[0].code == "journey_compiled_stale"
    assert "fixtures contract" in result.issues[0].message


def test_run_journeys_fails_when_contract_deleted_after_compile(tmp_path: Path) -> None:
    """AC-009: deleting the contract after compile is a hash mismatch."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    _write_v2_journey(specs)
    contract_path = specs / "journeys" / "fixtures.yaml"
    contract_path.write_text("schema_version: 1\n", encoding="utf-8")
    compile_result = compile_journeys(tmp_path, journey="onboarding-first-project")
    assert compile_result.error_count == 0
    contract_path.unlink()

    result = run_journeys(tmp_path, journey="onboarding-first-project", execute=False)

    assert result.error_count == 1
    assert result.issues[0].code == "journey_compiled_stale"


def test_run_journeys_reports_compiler_stale_before_contract_hash(tmp_path: Path) -> None:
    """AC-008: pre-v2-3 manifests report journey_compiler_stale, never a hash mismatch."""
    specs = _setup_compiled(tmp_path)
    manifest_path = specs / "journeys" / "onboarding-first-project" / "compiled" / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["compiler_version"] = "journeys-v2-2"
    # Tolerant reader: pre-060 manifests have no fixtures_contract_hash field.
    data.pop("fixtures_contract_hash", None)
    manifest_path.write_text(json.dumps(data), encoding="utf-8")
    (specs / "journeys" / "fixtures.yaml").write_text("schema_version: 1\n", encoding="utf-8")

    result = run_journeys(tmp_path, journey="onboarding-first-project", execute=False)

    assert result.error_count == 1
    assert result.issues[0].code == "journey_compiler_stale"
