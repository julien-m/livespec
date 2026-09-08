"""Preserved test cases and fixtures for test_journey_v2_runner.py."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import NotRequired, TypeAlias, TypedDict, Unpack

import pytest

from tests.test_journey_v2_validation import _write_feature, _write_v2_journey
from validator.journeys.compiler import compile_journeys
from validator.journeys.runner import run_journeys

_JsonValue: TypeAlias = (
    bool | int | float | str | list["_JsonValue"] | dict[str, "_JsonValue"] | None
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


def test_run_journeys_records_playwright_run_without_udid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-001: non-Xcode journey runs still expose replay metadata."""
    _setup_compiled(tmp_path)

    def fake_run(
        argv: list[str],
        **_kwargs: Unpack[_RunKwargs],
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    monkeypatch.setattr("validator.journeys.runner.subprocess.run", fake_run)

    result = run_journeys(tmp_path, journey="onboarding-first-project")

    assert result.error_count == 0
    assert len(result.runs) == 1
    record = result.runs[0]
    assert record.runner == "playwright"
    assert record.udid is None
    assert record.destination is None
    assert record.command == (
        "npx playwright test tests/e2e/journeys/onboarding_first_project.spec.ts"
    )


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


def test_run_journeys_records_run_even_when_native_run_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-001: attempted destination metadata survives native runner failure."""
    _setup_xcuitest_compiled_project(tmp_path)
    monkeypatch.setenv("LIVESPEC_XCODE_DESTINATION", "platform=iOS Simulator,id=IPHONE-17")

    def fake_run(
        argv: list[str],
        **_kwargs: Unpack[_RunKwargs],
    ) -> subprocess.CompletedProcess[str]:
        if argv[:2] == ["xcodebuild", "test"]:
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="failed")
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    monkeypatch.setattr("validator.journeys.runner.subprocess.run", fake_run)

    result = run_journeys(tmp_path, journey="onboarding-first-project")

    assert result.executed == []
    assert result.error_count == 1
    assert len(result.runs) == 1
    assert result.runs[0].udid == "IPHONE-17"
    assert result.runs[0].destination == "platform=iOS Simulator,id=IPHONE-17"


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
