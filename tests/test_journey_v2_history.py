# LiveSpec traceability anchors
# @spec(AC-008)
# @spec(AC-009)
# @spec(AC-010)
# @spec(AC-011)

"""Tests for User Journeys v2 history and decision governance."""

from __future__ import annotations

import json
from pathlib import Path

from tests.test_journey_v2_validation import _write_feature, _write_v2_journey
from validator.journeys.validator import validate_journeys


def _write_stale_manifest(specs: Path, journey_id: str) -> None:
    manifest_dir = specs / "journeys" / journey_id / "compiled"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "journey_id": journey_id,
                "source_hash": "old-hash",
                "compiler_version": "test",
                "artifacts": [],
            }
        ),
        encoding="utf-8",
    )


def test_changed_existing_journey_requires_decision_and_changelog_entry(tmp_path: Path) -> None:
    """FR-009: changed compiled journeys require explicit decision history."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    _write_v2_journey(specs)
    _write_stale_manifest(specs, "onboarding-first-project")

    result = validate_journeys(tmp_path)

    codes = {issue.code for issue in result.issues}
    assert "journey_history_missing" in codes


def test_changed_existing_journey_accepts_intentional_update_decision(tmp_path: Path) -> None:
    """FR-010: intentional updates are accepted when decision and changelog cite the new hash."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    source = _write_v2_journey(specs)
    _write_stale_manifest(specs, "onboarding-first-project")
    current_hash = source.read_text(encoding="utf-8")
    digest = __import__("hashlib").sha256(current_hash.encode("utf-8")).hexdigest()
    journey_dir = specs / "journeys" / "onboarding-first-project"
    decisions = journey_dir / "decisions"
    decisions.mkdir()
    (decisions / "2026-06-04-012-projects-label-update.md").write_text(
        f"""# Intentional update

- classification: intentional_update
- trigger_feature: 012-projects
- affected_features: 001-onboarding, 012-projects
- source_hash: {digest}
- validation_run: runs/2026-06-04T120000Z.json
- reason: Product label changed intentionally.
""",
        encoding="utf-8",
    )
    (journey_dir / "changelog.md").write_text(
        f"# Changelog\n\n## 2026-06-04 - Intentional update\n\n- source_hash: {digest}\n",
        encoding="utf-8",
    )

    result = validate_journeys(tmp_path)

    assert "journey_history_missing" not in {issue.code for issue in result.issues}
