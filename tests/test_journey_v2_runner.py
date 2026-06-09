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
    """FR-024: XCUITest journeys invoke xcodebuild for the generated class."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    source = _write_v2_journey(specs)
    source.write_text(
        source.read_text(encoding="utf-8").replace("runner: playwright", "runner: xcuitest"),
        encoding="utf-8",
    )
    compile_result = compile_journeys(tmp_path, journey="onboarding-first-project")
    assert compile_result.error_count == 0
    (tmp_path / "App.xcodeproj").mkdir()
    (tmp_path / "App.xcodeproj" / "project.pbxproj").write_text("", encoding="utf-8")
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
    command = calls[0]
    assert command[0] == "xcodebuild"
    assert "-only-testing:STRAPTUITests/OnboardingFirstProjectJourney" in command


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
