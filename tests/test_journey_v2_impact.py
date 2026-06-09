# LiveSpec traceability anchors
# @spec(AC-007)
# @spec(AC-020)
# @spec(AC-021)
# @spec(AC-022)
# @spec(AC-036)

"""Tests for JourneyImpactAnalyzer."""

from __future__ import annotations

from pathlib import Path

from tests.test_journey_v2_validation import _write_feature
from validator.journeys.impact import analyze_journey_impacts


def _write_text_target_journey(specs: Path) -> None:
    journey_dir = specs / "journeys" / "onboarding-first-project"
    journey_dir.mkdir(parents=True, exist_ok=True)
    (journey_dir / "journey.yaml").write_text(
        """
schema_version: 2
id: onboarding-first-project
title: Onboarding first project
status: active
description: New user creates a first project.
covers:
  - feature: 001-onboarding
    kind: ac
    ref: AC-001
    reason: Signup starts the path.
run_policy:
  local: impacted
targets:
  - surface: web
    runner: playwright
steps:
  - action: click
    target:
      text: Create project
      product_contract: true
visual_checks:
  - id: project-card-margin
    mode: native
    assertion: min_margin
    target:
      semantic_id: project.success_card
    min_px: 16
""".lstrip(),
        encoding="utf-8",
    )
    (journey_dir / "changelog.md").write_text("# Changelog\n", encoding="utf-8")


def test_impact_detects_changed_file_touching_journey_text_target(tmp_path: Path) -> None:
    """FR-019: product-contract labels touched by a diff impact old journeys."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_text_target_journey(specs)
    changed = tmp_path / "src" / "ProjectButton.tsx"
    changed.parent.mkdir()
    changed.write_text(
        '<button aria-label="Create project">Start project</button>',
        encoding="utf-8",
    )

    impacts = analyze_journey_impacts(tmp_path, changed_files=[changed])

    assert [impact.journey_id for impact in impacts] == ["onboarding-first-project"]
    assert impacts[0].required_classification == "intentional_update"
    assert "$spec-journey edit onboarding-first-project" in impacts[0].recommended_command


def test_impact_detects_changed_file_touching_visual_semantic_id(tmp_path: Path) -> None:
    """FR-020: semantic IDs used by visual checks impact journeys before tests fail."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_text_target_journey(specs)
    changed = tmp_path / "penflow" / "semantic-ui-tree.json"
    changed.parent.mkdir()
    changed.write_text('{"semantic_id":"project.success_card","padding":24}', encoding="utf-8")

    impacts = analyze_journey_impacts(tmp_path, changed_files=[changed])

    assert {impact.source_signal for impact in impacts} == {"visual_check_semantic_id"}
    assert impacts[0].blocking is True


def test_impact_uses_smart_test_selector_feature_signal(tmp_path: Path) -> None:
    """AC-020: SmartTestSelector output impacts journeys covering matched features."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_text_target_journey(specs)
    changed = tmp_path / "src" / "onboarding.py"
    changed.parent.mkdir()
    changed.write_text(
        "# @spec FR-001: Onboarding — .specs/features/001-onboarding/spec.md#fr-001\n",
        encoding="utf-8",
    )

    impacts = analyze_journey_impacts(tmp_path, changed_files=[changed])

    assert {impact.source_signal for impact in impacts} == {"smart_test_selector"}
    assert impacts[0].affected_features == ["001-onboarding"]


def test_impact_detects_changed_file_touching_stable_selector_fields(
    tmp_path: Path,
) -> None:
    """AC-020: stable selector fields impact journeys before tests fail."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_text_target_journey(specs)
    source = specs / "journeys" / "onboarding-first-project" / "journey.yaml"
    source.write_text(
        source.read_text(encoding="utf-8").replace(
            "product_contract: true",
            "product_contract: true\n"
            "      test_id: create-project\n"
            "      i18n_key: project.create\n"
            "      accessibility_label: Create project",
        ),
        encoding="utf-8",
    )
    changed = tmp_path / "src" / "ProjectButton.tsx"
    changed.parent.mkdir()
    changed.write_text(
        '<button data-testid="create-project" aria-label="Create project">'
        '{t("project.create")}</button>',
        encoding="utf-8",
    )

    impacts = analyze_journey_impacts(tmp_path, changed_files=[changed])

    signals = {impact.source_signal for impact in impacts}
    assert "target_test_id" in signals
    assert "target_i18n_key" in signals
    assert "target_accessibility_label" in signals
