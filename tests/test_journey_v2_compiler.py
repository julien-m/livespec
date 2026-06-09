# LiveSpec traceability anchors
# @spec(AC-002)
# @spec(AC-016)
# @spec(AC-018)
# @spec(AC-024)
# @spec(AC-027)
# @spec(AC-032)
# @spec(AC-033)
# @spec(AC-034)
# @spec(AC-037)
# @spec(AC-038)
# @spec(AC-040)

"""Tests for User Journeys v2 compiler registry and manifest semantics."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from pytest import MonkeyPatch

from tests.test_journey_v2_validation import _write_feature, _write_v2_journey
from validator.journeys import compiler as compiler_module
from validator.journeys.capabilities import validate_runner_capability
from validator.journeys.compiler import compile_journeys
from validator.journeys.manifest import read_compiled_manifest
from validator.journeys.models import ValidationResult


def test_compile_v2_writes_manifest_and_playwright_artifact(tmp_path: Path) -> None:
    """FR-028: Playwright compile writes native artifact plus manifest metadata."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    source = _write_v2_journey(specs)

    result = compile_journeys(tmp_path, journey="onboarding-first-project")

    manifest = read_compiled_manifest(tmp_path, "onboarding-first-project")
    assert result.error_count == 0, [issue.code for issue in result.issues]
    assert manifest is not None
    assert manifest.journey_id == "onboarding-first-project"
    assert manifest.source_path == ".specs/journeys/onboarding-first-project/journey.yaml"
    assert manifest.source_hash
    assert manifest.native_output_paths == ["tests/e2e/journeys/onboarding_first_project.spec.ts"]
    artifact = tmp_path / manifest.native_output_paths[0]
    text = artifact.read_text(encoding="utf-8")
    assert "livespec-journey-id: onboarding-first-project" in text
    assert f"livespec-journey-source-hash: {manifest.source_hash}" in text
    assert json.loads((source.parent / "compiled" / "manifest.json").read_text())


def test_compile_v2_generates_xcuitest_and_maestro_by_runner(tmp_path: Path) -> None:
    """FR-029: registry dispatches XCUITest and Maestro compilers."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    source = _write_v2_journey(specs)
    base = source.read_text(encoding="utf-8")
    source.write_text(
        base.replace("runner: playwright", "runner: xcuitest").replace(
            "route: /signup",
            'route: "myapp://signup"',
        ),
        encoding="utf-8",
    )
    ios_result = compile_journeys(tmp_path, journey="onboarding-first-project")
    shutil.rmtree(source.parent / "compiled")
    source.write_text(base.replace("runner: playwright", "runner: maestro"), encoding="utf-8")
    maestro_result = compile_journeys(tmp_path, journey="onboarding-first-project", force=True)

    assert ios_result.error_count == 0
    assert maestro_result.error_count == 0
    swift_artifact = tmp_path / "STRAPTUITests" / "Journeys" / "OnboardingFirstProjectJourney.swift"
    maestro_artifact = (
        tmp_path / ".specs" / "maestro" / "journeys" / "onboarding_first_project.yaml"
    )
    assert swift_artifact.exists()
    assert maestro_artifact.exists()
    swift_text = swift_artifact.read_text(encoding="utf-8")
    assert "func testOnboardingFirstProjectJourney() throws" in swift_text
    assert "testJourney()" not in swift_text


def test_compile_v2_runs_xcodegen_for_xcuitest_project_yml(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """FR-029: XcodeGen projects regenerate xcodeproj after Swift journey output."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    source = _write_v2_journey(specs)
    source.write_text(
        source.read_text(encoding="utf-8")
        .replace("runner: playwright", "runner: xcuitest")
        .replace("route: /signup", 'route: "myapp://signup"'),
        encoding="utf-8",
    )
    (tmp_path / "project.yml").write_text("name: App\n", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(
        argv: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout="generated", stderr="")

    monkeypatch.setattr("validator.journeys.compiler.shutil.which", lambda _: "/bin/xcodegen")
    monkeypatch.setattr("validator.journeys.compiler.subprocess.run", fake_run)

    result = compile_journeys(tmp_path, journey="onboarding-first-project")

    assert result.error_count == 0, [issue.message for issue in result.issues]
    assert calls == [["xcodegen", "generate"]]


def test_compile_v2_reports_xcodegen_failure_for_xcuitest_project_yml(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """FR-029: XcodeGen failures block stale Xcode project inclusion."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    source = _write_v2_journey(specs)
    source.write_text(
        source.read_text(encoding="utf-8")
        .replace("runner: playwright", "runner: xcuitest")
        .replace("route: /signup", 'route: "myapp://signup"'),
        encoding="utf-8",
    )
    (tmp_path / "project.yml").write_text("name: App\n", encoding="utf-8")

    def fake_run(
        argv: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="bad project")

    monkeypatch.setattr("validator.journeys.compiler.shutil.which", lambda _: "/bin/xcodegen")
    monkeypatch.setattr("validator.journeys.compiler.subprocess.run", fake_run)

    result = compile_journeys(tmp_path, journey="onboarding-first-project")

    assert result.error_count == 1
    assert result.issues[0].code == "journey_xcodegen_failed"
    assert read_compiled_manifest(tmp_path, "onboarding-first-project") is None


def test_compile_v2_rejects_ui_journey_for_pytest_and_cargo(tmp_path: Path) -> None:
    """AC-037: unsupported runners fail at capability validation."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    source = _write_v2_journey(specs)
    source.write_text(
        source.read_text(encoding="utf-8").replace("runner: playwright", "runner: cargo"),
        encoding="utf-8",
    )

    result = compile_journeys(tmp_path, journey="onboarding-first-project")

    assert result.error_count == 1
    assert result.issues[0].code == "journey_capability_unsupported"


def test_compile_v2_rejects_unsupported_xcuitest_steps_before_writing(
    tmp_path: Path,
) -> None:
    """AC-037: XCUITest compile rejects unsupported portable steps before output."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    source = _write_v2_journey(specs)
    source.write_text(
        source.read_text(encoding="utf-8")
        .replace("runner: playwright", "runner: xcuitest")
        .replace(
            "  - action: open\n    target:\n      route: /signup\n",
            "  - action: wait\n    seconds: 5\n",
        ),
        encoding="utf-8",
    )

    result = compile_journeys(tmp_path, journey="onboarding-first-project")

    swift_artifact = tmp_path / "STRAPTUITests" / "Journeys" / "OnboardingFirstProjectJourney.swift"
    assert result.error_count == 1
    assert result.issues[0].code == "journey_capability_unsupported"
    assert not swift_artifact.exists()


def test_compile_v2_rejects_xcuitest_open_without_url_before_writing(
    tmp_path: Path,
) -> None:
    """AC-037: XCUITest open requires a URL or deep link, not a relative route."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    source = _write_v2_journey(specs)
    source.write_text(
        source.read_text(encoding="utf-8").replace("runner: playwright", "runner: xcuitest"),
        encoding="utf-8",
    )

    result = compile_journeys(tmp_path, journey="onboarding-first-project")

    swift_artifact = tmp_path / "STRAPTUITests" / "Journeys" / "OnboardingFirstProjectJourney.swift"
    assert result.error_count == 1
    assert result.issues[0].code == "journey_capability_unsupported"
    assert "URL/deep link" in result.issues[0].message
    assert not swift_artifact.exists()


def test_compile_v2_rejects_malformed_step_payloads_before_writing() -> None:
    """AC-037: capability validation rejects malformed compiler step dictionaries."""
    issue = validate_runner_capability(
        "xcuitest",
        "broken-journey",
        [{"click": {}, "assert": {"test_id": "save"}}, {"fill": {"test_id": "name"}}],
    )

    assert issue is not None
    assert issue.code == "journey_capability_unsupported"
    assert "malformed step dictionary" in issue.message


def test_compile_v2_xcuitest_supports_negative_assertions_and_fill(
    tmp_path: Path,
) -> None:
    """AC-032: XCUITest compiler emits concrete code for supported actions."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    source = _write_v2_journey(specs)
    source.write_text(
        source.read_text(encoding="utf-8")
        .replace("runner: playwright", "runner: xcuitest")
        .replace(
            "  - action: open\n    target:\n      route: /signup\n",
            """
  - action: open
    target:
      route: "myapp://signup"
  - action: fill
    target:
      test_id: workout-name-field
    value: Morning Session
  - action: assert_not
    target:
      test_id: watch-short-workout-save-button
  - action: screenshot
""",
        ),
        encoding="utf-8",
    )

    result = compile_journeys(tmp_path, journey="onboarding-first-project")

    manifest = read_compiled_manifest(tmp_path, "onboarding-first-project")
    assert result.error_count == 0, [issue.message for issue in result.issues]
    assert manifest is not None
    text = (tmp_path / manifest.native_output_paths[0]).read_text(encoding="utf-8")
    assert "import Foundation" in text
    assert 'openJourneyURL("myapp://signup", in: app)' in text
    assert "app.open(url)" in text
    assert "Process()" not in text
    assert "launchEnvironment" not in text.split('openJourneyURL("myapp://signup", in: app)', 1)[1]
    assert (
        'app.descendants(matching: .any)["workout-name-field"].typeText("Morning Session")' in text
    )
    assert (
        'XCTAssertFalse(app.descendants(matching: .any)["watch-short-workout-save-button"].exists)'
        in text
    )
    assert "let attachment = XCTAttachment(screenshot: screenshot)" in text
    assert "attachment.lifetime = .keepAlways" in text


def test_compile_v2_xcuitest_injects_preconditions_before_launch(
    tmp_path: Path,
) -> None:
    """AC-032: XCUITest launch environment reflects declared journey preconditions."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    source = _write_v2_journey(specs)
    source.write_text(
        source.read_text(encoding="utf-8")
        .replace("runner: playwright", "runner: xcuitest")
        .replace("route: /signup", 'route: "myapp://signup"')
        .replace(
            "steps:\n",
            """
preconditions:
  auth: pro
  fixtures:
    - imported-workout
    - short-workout-boundaries
  mocks:
    - storekit-pro
  feature_flags:
    - paywall-v2
steps:
""".lstrip(),
        ),
        encoding="utf-8",
    )

    result = compile_journeys(tmp_path, journey="onboarding-first-project")

    manifest = read_compiled_manifest(tmp_path, "onboarding-first-project")
    assert result.error_count == 0, [issue.message for issue in result.issues]
    assert manifest is not None
    text = (tmp_path / manifest.native_output_paths[0]).read_text(encoding="utf-8")
    launch_index = text.index("        app.launch()")
    auth_index = text.index('app.launchEnvironment["UI_TEST_JOURNEY_AUTH"]')
    fixtures_index = text.index('app.launchEnvironment["UI_TEST_JOURNEY_FIXTURES"]')
    mocks_index = text.index('app.launchEnvironment["UI_TEST_JOURNEY_MOCKS"]')
    flags_index = text.index('app.launchEnvironment["UI_TEST_JOURNEY_FEATURE_FLAGS"]')
    open_index = text.index('openJourneyURL("myapp://signup", in: app)')
    assert auth_index < launch_index
    assert fixtures_index < launch_index
    assert mocks_index < launch_index
    assert flags_index < launch_index
    assert launch_index < open_index
    assert 'app.launchEnvironment["UI_TEST_JOURNEY_AUTH"] = "pro"' in text
    assert (
        'app.launchEnvironment["UI_TEST_JOURNEY_FIXTURES"] = '
        '"[\\"imported-workout\\",\\"short-workout-boundaries\\"]"' in text
    )
    assert 'app.launchEnvironment["UI_TEST_JOURNEY_MOCKS"] = "[\\"storekit-pro\\"]"' in text
    assert 'app.launchEnvironment["UI_TEST_JOURNEY_FEATURE_FLAGS"] = "[\\"paywall-v2\\"]"' in text
    assert "Process()" not in text


def test_compile_v2_fails_when_source_becomes_unreadable(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """FR-030: compiler fails explicitly when source cannot be reread after validation."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    source = _write_v2_journey(specs)
    real_validate = compiler_module.validate_journeys

    def validate_then_remove(project_root: Path, feature: str | None = None) -> ValidationResult:
        result = real_validate(project_root, feature)
        source.unlink()
        return result

    monkeypatch.setattr(compiler_module, "validate_journeys", validate_then_remove)

    result = compile_journeys(tmp_path, journey="onboarding-first-project")

    assert result.error_count == 1
    assert result.artifacts == []
    assert result.issues[0].code == "journey_source_unreadable"
    assert result.issues[0].path == source
    assert not (source.parent / "compiled" / "manifest.json").exists()


def test_compile_v2_manifest_ends_with_newline(tmp_path: Path) -> None:
    """FR-029: manifest writer preserves formatter-friendly JSON output."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    source = _write_v2_journey(specs)

    result = compile_journeys(tmp_path, journey="onboarding-first-project")

    assert result.error_count == 0, [issue.code for issue in result.issues]
    assert (source.parent / "compiled" / "manifest.json").read_bytes().endswith(b"\n")


def test_compile_v2_writes_llm_visual_contracts_into_manifest(tmp_path: Path) -> None:
    """AC-040: LLM visual checks compile to screenshot contracts referenced by manifest."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    source = _write_v2_journey(specs)
    source.write_text(
        source.read_text(encoding="utf-8").replace(
            "privacy:\n  llm_allowed: false\n  retention: none\n",
            """
visual_checks:
  - id: success-card-padding
    mode: llm
    assertion: min_margin
    target:
      semantic_id: success-card
    prompt: Verify that the card keeps visible padding and centered text.
    blocking: true
privacy:
  llm_allowed: true
  retention: local
  masking:
    - email
""".lstrip(),
        ),
        encoding="utf-8",
    )

    result = compile_journeys(tmp_path, journey="onboarding-first-project")

    manifest = read_compiled_manifest(tmp_path, "onboarding-first-project")
    assert result.error_count == 0, [issue.code for issue in result.issues]
    assert manifest is not None
    assert manifest.visual_contract_paths == [
        ".specs/journeys/onboarding-first-project/compiled/visual-contracts/"
        "success_card_padding.json"
    ]
    contract = json.loads((tmp_path / manifest.visual_contract_paths[0]).read_text())
    assert contract["mode"] == "llm"
    assert contract["privacy"]["masking"] == ["email"]
    assert contract["instructions"] == (
        "Verify that the card keeps visible padding and centered text."
    )


def test_compile_v2_writes_playwright_native_visual_assertions(tmp_path: Path) -> None:
    """AC-038: native visual checks compile to runner assertions when supported."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    source = _write_v2_journey(specs)
    source.write_text(
        source.read_text(encoding="utf-8").replace(
            "privacy:\n  llm_allowed: false\n  retention: none\n",
            """
visual_checks:
  - id: success-card-margin
    mode: native
    assertion: min_margin
    target:
      semantic_id: success-card
    min_px: 16
privacy:
  llm_allowed: false
  retention: none
""".lstrip(),
        ),
        encoding="utf-8",
    )

    result = compile_journeys(tmp_path, journey="onboarding-first-project")

    manifest = read_compiled_manifest(tmp_path, "onboarding-first-project")
    assert result.error_count == 0, [issue.code for issue in result.issues]
    assert manifest is not None
    artifact = tmp_path / manifest.native_output_paths[0]
    text = artifact.read_text(encoding="utf-8")
    assert "native visual check: success-card-margin" in text
    assert "boundingBox()" in text
    assert "toBeGreaterThanOrEqual(16)" in text
