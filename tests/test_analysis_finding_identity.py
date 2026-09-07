"""Structural gaps keep feature-qualified identities across reports and repeated analysis."""

import json
from pathlib import Path

import pytest

from tests.review_support import review_existing_project, reviewed_project
from validator.pre_impl_analysis import (
    AnalyzeSeverity,
    analyze_feature_artifacts,
    has_blocking_findings,
    render_report_json,
    render_report_markdown,
)


def _reviewed_gap(root: Path, name: str) -> Path:
    feature = reviewed_project(root, name)
    plan = feature / "plan.md"
    plan.write_text(plan.read_text().replace("FR-001 ", ""))
    review_existing_project(root, name)
    return feature


@pytest.mark.parametrize("structural_only", [True, False])
def test_structural_gap_identity_distinguishes_features_and_preserves_report_semantics(
    tmp_path: Path, structural_only: bool
) -> None:
    features = [_reviewed_gap(tmp_path, name) for name in ("001-first", "002-second")]
    reports = [
        analyze_feature_artifacts(
            feature, tmp_path / ".specs/constitution.md", structural_only=structural_only
        )
        for feature in features
    ]
    gaps = [next(f for f in report.findings if f.category == "coverage") for report in reports]
    assert gaps[0].finding_id != gaps[1].finding_id
    severity = AnalyzeSeverity.HIGH if structural_only else AnalyzeSeverity.LOW
    for feature, report, gap in zip(features, reports, gaps, strict=True):
        repeated = analyze_feature_artifacts(
            feature, tmp_path / ".specs/constitution.md", structural_only=structural_only
        )
        assert repeated == report
        uncovered = [item for item in report.coverage if not item.has_plan_task]
        assert [item.requirement_id for item in uncovered] == [f"{feature.name}:FR-001"]
        assert (
            gap.summary == f"Requirement {uncovered[0].requirement_id} has no plan-task reference"
        )
        assert gap.severity is severity
        assert gap.locations == ("spec.md", "plan.md")
        assert gap.recommendation == "Add a plan task that references FR-001, or cite it explicitly"
        assert has_blocking_findings(report) is structural_only
        assert report.coverage_percent == 50.0
        payload = json.loads(render_report_json(report))
        assert payload["metrics"]["high_count"] == int(structural_only)
        assert set(payload["findings"][0]) == {
            "finding_id",
            "category",
            "severity",
            "locations",
            "summary",
            "recommendation",
        }
        assert payload["findings"][0]["finding_id"] == gap.finding_id
        assert f"| {gap.finding_id} | coverage | {severity.value} |" in render_report_markdown(
            report
        )
