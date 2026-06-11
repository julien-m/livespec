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

import hashlib
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
    negative_assertion = (
        "assertJourneyElementDoesNotExist(app.descendants(matching: .any)"
        '["watch-short-workout-save-button"], "watch-short-workout-save-button")'
    )
    immediate_negative_assertion = (
        'XCTAssertFalse(app.descendants(matching: .any)["watch-short-workout-save-button"].exists)'
    )
    assert negative_assertion in text
    assert "element.waitForExistence(timeout: timeout)" in text
    assert immediate_negative_assertion not in text
    assert "let attachment = XCTAttachment(screenshot: screenshot)" in text
    assert "attachment.lifetime = .keepAlways" in text


def test_compile_v2_xcuitest_waits_for_assertions(
    tmp_path: Path,
) -> None:
    """AC-032: XCUITest assertions wait for UI state instead of reading `.exists` directly."""
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
  - action: assert
    target:
      test_id: welcome
""",
        ),
        encoding="utf-8",
    )

    result = compile_journeys(tmp_path, journey="onboarding-first-project")

    manifest = read_compiled_manifest(tmp_path, "onboarding-first-project")
    assert result.error_count == 0, [issue.message for issue in result.issues]
    assert manifest is not None
    text = (tmp_path / manifest.native_output_paths[0]).read_text(encoding="utf-8")
    expected_assertion = (
        'assertJourneyElementExists(app.descendants(matching: .any)["welcome"], "welcome")'
    )
    assert expected_assertion in text
    assert "private func assertJourneyElementExists(" in text
    assert "XCTAssertTrue(app.descendants(matching: .any)" not in text
    assert "XCTAssertFalse(app.descendants(matching: .any)" not in text
    assert "element.waitForExistence(timeout: timeout)" in text
    assert "XCTAssertTrue(" in text


def test_compile_v2_xcuitest_injects_preconditions_before_launch(
    tmp_path: Path,
) -> None:
    """AC-032: XCUITest launch environment reflects declared journey preconditions."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    # Feature 060: fixture journeys now require a contract; seed-only entries
    # (no screens/markers, no bootstrap key) keep this codegen wait-free.
    (specs / "journeys" / "fixtures.yaml").parent.mkdir(parents=True, exist_ok=True)
    (specs / "journeys" / "fixtures.yaml").write_text(
        """
schema_version: 1
fixtures:
  imported-workout:
    surfaces: [web]
  short-workout-boundaries:
    surfaces: [web]
mocks:
  storekit-pro:
    surfaces: [web]
""".lstrip(),
        encoding="utf-8",
    )
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


FIXTURES_CONTRACT_YAML = """
schema_version: 1
bootstrap:
  ready_marker:
    ios: ui-test-bootstrap-ready
  timeout_seconds: 20
fixtures:
  imported-workout:
    surfaces: [ios]
    expected_screen:
      ios: iphone-session-page
    required_markers:
      ios: [zz-last-marker, session-exercise-list]
  short-workout-boundaries:
    surfaces: [ios]
    required_markers:
      ios: [boundary-marker, session-exercise-list]
mocks:
  storekit-pro:
    surfaces: [ios]
""".lstrip()


def _setup_xcuitest_fixture_project(tmp_path: Path, *, contract: str | None) -> Path:
    """Build an XCUITest journey declaring fixtures, with an optional contract."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    source = _write_v2_journey(specs)
    source.write_text(
        source.read_text(encoding="utf-8")
        .replace("runner: playwright", "runner: xcuitest")
        .replace("surface: web", "surface: ios")
        .replace("route: /signup", 'route: "myapp://signup"')
        .replace(
            "steps:\n",
            """
preconditions:
  fixtures:
    - imported-workout
    - short-workout-boundaries
  mocks:
    - storekit-pro
steps:
""".lstrip(),
        ),
        encoding="utf-8",
    )
    if contract is not None:
        contract_path = specs / "journeys" / "fixtures.yaml"
        contract_path.write_text(contract, encoding="utf-8")
    return source


def test_compile_v2_xcuitest_emits_bootstrap_waits_in_order(tmp_path: Path) -> None:
    """AC-005: waits follow app.launch() in ready -> screen -> sorted marker order."""
    _setup_xcuitest_fixture_project(tmp_path, contract=FIXTURES_CONTRACT_YAML)

    result = compile_journeys(tmp_path, journey="onboarding-first-project")

    manifest = read_compiled_manifest(tmp_path, "onboarding-first-project")
    assert result.error_count == 0, [issue.message for issue in result.issues]
    assert manifest is not None
    text = (tmp_path / manifest.native_output_paths[0]).read_text(encoding="utf-8")
    fixtures_index = text.index('app.launchEnvironment["UI_TEST_JOURNEY_FIXTURES"]')
    launch_index = text.index("        app.launch()")
    ready_index = text.index('waitForJourneyBootstrap(app, "ui-test-bootstrap-ready", timeout: 20)')
    screen_index = text.index('waitForJourneyBootstrap(app, "iphone-session-page", timeout: 20)')
    marker_indices = [
        text.index(f'waitForJourneyBootstrap(app, "{marker}", timeout: 20)')
        for marker in ("boundary-marker", "session-exercise-list", "zz-last-marker")
    ]
    first_step_index = text.index('openJourneyURL("myapp://signup", in: app)')
    assert fixtures_index < launch_index < ready_index < screen_index
    assert screen_index < marker_indices[0] < marker_indices[1] < marker_indices[2]
    assert marker_indices[2] < first_step_index
    assert "private func waitForJourneyBootstrap(" in text
    assert (
        "XCTFail(\"JOURNEY_BOOTSTRAP_FAILURE: marker '\\(marker)' "
        'not found within \\(Int(timeout))s")' in text
    )


def test_compile_v2_xcuitest_seed_only_fixture_waits_ready_only(tmp_path: Path) -> None:
    """AC-002: a fixture without navigation derives a ready-marker-only wait."""
    contract = """
schema_version: 1
bootstrap:
  ready_marker:
    ios: ui-test-bootstrap-ready
fixtures:
  imported-workout:
    surfaces: [ios]
  short-workout-boundaries:
    surfaces: [ios]
mocks:
  storekit-pro:
    surfaces: [ios]
""".lstrip()
    _setup_xcuitest_fixture_project(tmp_path, contract=contract)

    result = compile_journeys(tmp_path, journey="onboarding-first-project")

    manifest = read_compiled_manifest(tmp_path, "onboarding-first-project")
    assert result.error_count == 0, [issue.message for issue in result.issues]
    assert manifest is not None
    text = (tmp_path / manifest.native_output_paths[0]).read_text(encoding="utf-8")
    assert text.count("waitForJourneyBootstrap(app, ") == 1
    assert 'waitForJourneyBootstrap(app, "ui-test-bootstrap-ready", timeout: 15)' in text


def test_compile_v2_fixture_less_codegen_is_identity_snapshot(tmp_path: Path) -> None:
    """AC-014 / SC-005: fixture-less journeys keep byte-identical codegen."""
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

    result = compile_journeys(tmp_path, journey="onboarding-first-project")

    manifest = read_compiled_manifest(tmp_path, "onboarding-first-project")
    assert result.error_count == 0, [issue.message for issue in result.issues]
    assert manifest is not None
    text = (tmp_path / manifest.native_output_paths[0]).read_text(encoding="utf-8")
    # Snapshot captured from the journeys-v2-2 compiler before this feature:
    # the artifact body must stay byte-identical (only the manifest version moves).
    expected = f"""// livespec-journey-id: onboarding-first-project
// livespec-journey-source-hash: {manifest.source_hash}
// livespec-journey-source: .specs/journeys/onboarding-first-project/journey.yaml
import Foundation
import XCTest

final class OnboardingFirstProjectJourney: XCTestCase {{
    func testOnboardingFirstProjectJourney() throws {{
        let app = XCUIApplication()
        app.launch()
        openJourneyURL("myapp://signup", in: app)
    }}

    private func openJourneyURL(_ urlString: String, in app: XCUIApplication) {{
        guard let url = URL(string: urlString) else {{
            XCTFail("invalid journey URL: \\(urlString)")
            return
        }}
        app.open(url)
    }}
}}
"""
    assert text == expected
    assert "waitForJourneyBootstrap" not in text


def test_compile_v2_manifest_records_version_bump_and_contract_hash(tmp_path: Path) -> None:
    """AC-008 / AC-009: manifests record journeys-v2-3 and the contract sha256."""
    _setup_xcuitest_fixture_project(tmp_path, contract=FIXTURES_CONTRACT_YAML)
    contract_path = tmp_path / ".specs" / "journeys" / "fixtures.yaml"

    result = compile_journeys(tmp_path, journey="onboarding-first-project")

    manifest = read_compiled_manifest(tmp_path, "onboarding-first-project")
    assert result.error_count == 0, [issue.message for issue in result.issues]
    assert manifest is not None
    assert manifest.compiler_version == "journeys-v2-3"
    expected_hash = hashlib.sha256(contract_path.read_bytes()).hexdigest()
    assert manifest.fixtures_contract_hash == expected_hash


def test_compile_v2_manifest_contract_hash_empty_without_contract(tmp_path: Path) -> None:
    """AC-009: fixture-less projects record an empty contract hash."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    _write_v2_journey(specs)

    result = compile_journeys(tmp_path, journey="onboarding-first-project")

    manifest = read_compiled_manifest(tmp_path, "onboarding-first-project")
    assert result.error_count == 0, [issue.code for issue in result.issues]
    assert manifest is not None
    assert manifest.compiler_version == "journeys-v2-3"
    assert manifest.fixtures_contract_hash == ""


def test_manifest_reader_tolerates_missing_contract_hash_field(tmp_path: Path) -> None:
    """AC-009: manifests written without the field parse with "" and schema 1."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    source = _write_v2_journey(specs)
    compile_journeys(tmp_path, journey="onboarding-first-project")
    manifest_path = source.parent / "compiled" / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    del data["fixtures_contract_hash"]
    manifest_path.write_text(json.dumps(data), encoding="utf-8")

    manifest = read_compiled_manifest(tmp_path, "onboarding-first-project")

    assert manifest is not None
    assert manifest.fixtures_contract_hash == ""
    assert manifest.schema_version == 1


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
