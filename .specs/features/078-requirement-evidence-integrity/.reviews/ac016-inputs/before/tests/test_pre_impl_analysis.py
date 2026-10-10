"""Tests for validator.pre_impl_analysis — read-only pre-implementation analyzer (Feature B).

Protected invariants:
- Severity is bounded: CRITICAL is reserved for constitution MUST violations and a
  missing spec.md/plan.md; an uncovered requirement is HIGH, never CRITICAL (C3).
- Coverage is token-presence based: a requirement is covered iff its ID appears in
  plan.md or implementation.md; coverage_percent = covered/total*100.
- Finding IDs are deterministic — identical across runs on unchanged artifacts (L1).
- A missing implementation.md is NOT a failure on its own.
"""

# 070-analyze-gate anchors: @spec(FR-002) @spec(FR-003) @spec(FR-004) @spec(FR-005)
# @spec(FR-006) @spec(FR-007) @spec(FR-009) @spec(FR-011)

from __future__ import annotations

from pathlib import Path

from validator.pre_impl_analysis import (
    AnalyzeSeverity,
    analyze_feature_artifacts,
)


def _feature(tmp_path: Path, *, spec: str, plan: str | None, impl: str | None = None) -> Path:
    feature_dir = tmp_path / "001-feature"
    feature_dir.mkdir()
    (feature_dir / "spec.md").write_text(spec, encoding="utf-8")
    if plan is not None:
        (feature_dir / "plan.md").write_text(plan, encoding="utf-8")
    if impl is not None:
        (feature_dir / "implementation.md").write_text(impl, encoding="utf-8")
    return feature_dir


def _clean_constitution(tmp_path: Path) -> Path:
    path = tmp_path / "constitution.md"
    path.write_text("# Constitution\n\n- Keep modules small.\n", encoding="utf-8")
    return path


def test_uncovered_requirement_is_high_and_coverage_is_fifty_percent(tmp_path: Path) -> None:
    feature_dir = _feature(
        tmp_path,
        spec="## Functional Requirements\n- FR-001: Export CSV.\n- FR-002: Email report.\n",
        plan="## Implementation Plan\n- Build FR-001 exporter in reports module.\n",
    )

    report = analyze_feature_artifacts(feature_dir, _clean_constitution(tmp_path))

    assert report.coverage_percent == 50.0
    high = [f for f in report.findings if f.severity is AnalyzeSeverity.HIGH]
    assert any("FR-002" in f.summary for f in high)
    # An uncovered requirement must never escalate to CRITICAL.
    assert all(f.severity is not AnalyzeSeverity.CRITICAL for f in report.findings)


def test_constitution_must_not_violation_is_critical(tmp_path: Path) -> None:
    feature_dir = _feature(
        tmp_path,
        spec="## Functional Requirements\n- FR-001: Run user scripts.\n",
        plan="## Implementation Plan\n- Implement FR-001 by calling use eval() on input.\n",
    )
    constitution = tmp_path / "constitution.md"
    constitution.write_text(
        "# Constitution\n\n- The system MUST NOT use eval().\n",
        encoding="utf-8",
    )

    report = analyze_feature_artifacts(feature_dir, constitution)

    critical = [f for f in report.findings if f.severity is AnalyzeSeverity.CRITICAL]
    assert critical
    assert any(f.category == "constitution" for f in critical)


def test_finding_ids_are_stable_across_runs(tmp_path: Path) -> None:
    feature_dir = _feature(
        tmp_path,
        spec="## Functional Requirements\n- FR-001: A.\n- FR-002: B.\n- AC-001: C.\n",
        plan="## Implementation Plan\n- Build FR-001.\n",
    )
    constitution = _clean_constitution(tmp_path)

    first = analyze_feature_artifacts(feature_dir, constitution)
    second = analyze_feature_artifacts(feature_dir, constitution)

    assert [f.finding_id for f in first.findings] == [f.finding_id for f in second.findings]
    assert first.findings  # non-empty so the stability assertion is meaningful
    assert all(f.finding_id.startswith("AN-") for f in first.findings)


def test_missing_plan_is_critical(tmp_path: Path) -> None:
    feature_dir = _feature(
        tmp_path,
        spec="## Functional Requirements\n- FR-001: A.\n",
        plan=None,
    )

    report = analyze_feature_artifacts(feature_dir, _clean_constitution(tmp_path))

    assert any(
        f.severity is AnalyzeSeverity.CRITICAL and f.category == "artifact" for f in report.findings
    )


def test_missing_implementation_is_not_a_failure(tmp_path: Path) -> None:
    feature_dir = _feature(
        tmp_path,
        spec="## Functional Requirements\n- FR-001: A.\n",
        plan="## Implementation Plan\n- Build FR-001.\n",
        impl=None,
    )

    report = analyze_feature_artifacts(feature_dir, _clean_constitution(tmp_path))

    assert report.metrics["implementation_present"] == 0
    # FR-001 is covered by plan.md, constitution is clean -> no CRITICAL/HIGH findings.
    assert all(
        f.severity not in (AnalyzeSeverity.CRITICAL, AnalyzeSeverity.HIGH) for f in report.findings
    )
