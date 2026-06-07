"""Tests for v1 to v2 journey migration."""

from __future__ import annotations

from pathlib import Path

from tests.test_journey_v2_validation import _write_feature
from validator.journeys.migration import migrate_v1_journeys


def test_migrate_v1_journey_creates_v2_artifacts_and_backlinks(tmp_path: Path) -> None:
    """FR-040: v1 migration converts feature-scoped journeys into v2 directories."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    v1_dir = specs / "journeys" / "001-onboarding"
    v1_dir.mkdir(parents=True)
    (v1_dir / "happy.journey.yaml").write_text(
        """
id: onboarding-first-project
feature: 001-onboarding
title: Onboarding first project
run_policy: always
covers:
  ac: [AC-001]
target:
  surface: web
steps:
  - open: /signup
""".lstrip(),
        encoding="utf-8",
    )

    result = migrate_v1_journeys(tmp_path, apply=True)

    source = specs / "journeys" / "onboarding-first-project" / "journey.yaml"
    assert result.migrated == ["onboarding-first-project"]
    assert source.exists()
    assert "schema_version: 2" in source.read_text(encoding="utf-8")
    assert (source.parent / "decisions").exists()
    assert (source.parent / "changelog.md").exists()
    assert (specs / "features" / "001-onboarding" / "journeys.md").exists()


def test_migrate_v1_journey_blocks_when_feature_spec_missing(tmp_path: Path) -> None:
    """AC-044: migration does not fabricate refs when source feature is missing."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    v1_dir = specs / "journeys" / "999-missing"
    v1_dir.mkdir(parents=True)
    (v1_dir / "happy.journey.yaml").write_text(
        "id: missing\nfeature: 999-missing\ntitle: Missing\ncovers:\n  ac: [AC-001]\n",
        encoding="utf-8",
    )

    result = migrate_v1_journeys(tmp_path, apply=True)

    assert result.migrated == []
    assert result.issues[0].code == "journey_migration_feature_missing"
