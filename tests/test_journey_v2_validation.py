"""Tests for User Journeys v2 path, index, backlink, and validation behavior."""

from __future__ import annotations

from pathlib import Path

from validator.journeys.backlinks import render_feature_backlinks, verify_feature_backlinks
from validator.journeys.index import build_journey_index
from validator.journeys.paths import (
    feature_backlink_path,
    iter_journey_source_paths,
    iter_v1_journey_source_paths,
    journey_source_path,
)
from validator.journeys.validator import validate_journeys


def _write_feature(specs: Path, slug: str) -> None:
    feature_dir = specs / "features" / slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text(
        "---\nstatus: Implemented\n---\n"
        f"# {slug}\n\n"
        "## Acceptance Criteria\n\n"
        "- **AC-001:** Requirement one.\n\n"
        "## Functional Requirements\n\n"
        "- **FR-003:** Requirement three.\n",
        encoding="utf-8",
    )


def _write_v2_journey(specs: Path, journey_id: str = "onboarding-first-project") -> Path:
    journey_dir = specs / "journeys" / journey_id
    journey_dir.mkdir(parents=True, exist_ok=True)
    source = journey_dir / "journey.yaml"
    source.write_text(
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
  - feature: 012-projects
    kind: fr
    ref: FR-003
    reason: Project creation completes the path.
run_policy:
  local: impacted
  ci: always
targets:
  - surface: web
    runner: playwright
steps:
  - action: open
    target:
      route: /signup
privacy:
  llm_allowed: false
  retention: none
""".lstrip(),
        encoding="utf-8",
    )
    (journey_dir / "changelog.md").write_text(
        "# Changelog\n\n## 2026-06-04 - Created\n\n- Initial journey.\n",
        encoding="utf-8",
    )
    return source


def test_v2_paths_scan_global_journey_sources_separately_from_v1(tmp_path: Path) -> None:
    """FR-002: v2 source discovery uses global journey IDs, not feature folders."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    source = _write_v2_journey(specs)
    v1_dir = specs / "journeys" / "001-onboarding"
    v1_dir.mkdir(parents=True)
    v1_source = v1_dir / "legacy.journey.yaml"
    v1_source.write_text("id: legacy\nfeature: 001-onboarding\n", encoding="utf-8")

    assert journey_source_path(tmp_path, "onboarding-first-project") == source
    assert iter_journey_source_paths(tmp_path) == [source]
    assert iter_v1_journey_source_paths(tmp_path) == [v1_source]
    assert feature_backlink_path(tmp_path, "001-onboarding") == (
        specs / "features" / "001-onboarding" / "journeys.md"
    )


def test_v2_validation_resolves_qualified_refs_and_builds_index(tmp_path: Path) -> None:
    """FR-007: validation resolves qualified AC/FR refs across features."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    _write_v2_journey(specs)

    result = validate_journeys(tmp_path)
    index = build_journey_index(tmp_path)

    assert result.error_count == 0, [issue.code for issue in result.issues]
    assert [journey.journey_id for journey in result.journeys] == ["onboarding-first-project"]
    assert index.by_feature["001-onboarding"] == {"onboarding-first-project"}
    assert index.by_feature["012-projects"] == {"onboarding-first-project"}


def test_v2_validation_rejects_unqualified_legacy_covers(tmp_path: Path) -> None:
    """AC-004: v2 coverage must use qualified refs instead of local lists."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    source = _write_v2_journey(specs)
    source.write_text(
        """
schema_version: 2
id: onboarding-first-project
title: Onboarding first project
status: active
description: New user creates a first project.
covers:
  ac: [AC-001]
run_policy:
  local: impacted
targets:
  - surface: web
    runner: playwright
steps:
  - action: open
    target:
      route: /signup
""".lstrip(),
        encoding="utf-8",
    )

    result = validate_journeys(tmp_path)

    assert result.error_count == 1
    assert result.issues[0].code == "journey_schema_invalid"


def test_backlinks_are_rendered_and_verified_for_each_covered_feature(tmp_path: Path) -> None:
    """FR-010: feature backlinks are generated from the v2 journey index."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    _write_v2_journey(specs)

    outputs = render_feature_backlinks(tmp_path)

    assert outputs == {
        "001-onboarding": feature_backlink_path(tmp_path, "001-onboarding"),
        "012-projects": feature_backlink_path(tmp_path, "012-projects"),
    }
    assert "onboarding-first-project" in outputs["001-onboarding"].read_text(encoding="utf-8")
    assert verify_feature_backlinks(tmp_path) == []
