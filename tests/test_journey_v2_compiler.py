"""Tests for User Journeys v2 compiler registry and manifest semantics."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from tests.test_journey_v2_validation import _write_feature, _write_v2_journey
from validator.journeys.compiler import compile_journeys
from validator.journeys.manifest import read_compiled_manifest


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
    source.write_text(base.replace("runner: playwright", "runner: xcuitest"), encoding="utf-8")
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
