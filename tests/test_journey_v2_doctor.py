# LiveSpec traceability anchors
# @spec(AC-019)
# @spec(AC-044)

"""Doctor scanner tests for User Journeys v2."""

from __future__ import annotations

from pathlib import Path

from tests.test_journey_v2_validation import _write_feature, _write_v2_journey
from validator.journeys.scanner import scan_journeys


def test_scan_journeys_reports_backlink_drift_and_v1_leftovers(tmp_path: Path) -> None:
    """AC-019: doctor reports backlink drift and legacy v1 leftovers."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    _write_v2_journey(specs)
    backlink = specs / "features" / "001-onboarding" / "journeys.md"
    backlink.write_text("# stale\n", encoding="utf-8")
    v1_dir = specs / "journeys" / "001-onboarding"
    v1_dir.mkdir()
    (v1_dir / "legacy.journey.yaml").write_text("id: legacy\n", encoding="utf-8")

    report = scan_journeys(tmp_path)

    codes = {finding.code for finding in report.findings}
    assert "journey_backlink_drift" in codes
    assert "journey_v1_leftover" in codes
    assert "journey_compiled_missing" in codes
