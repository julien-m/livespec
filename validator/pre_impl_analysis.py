"""Read-only structural references and independently verified semantic readiness."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

# Preserve the original public renderer imports while keeping analysis focused.
from validator.pre_impl_render import render_report_json, render_report_markdown

if TYPE_CHECKING:  # Review types stay lazy until semantic evaluation is requested.
    from validator.semantic.review_context import PreparedReview

__all__ = [
    "AnalyzeFinding",
    "AnalyzeSeverity",
    "PreImplAnalysisReport",
    "RequirementCoverage",
    "analyze_feature_artifacts",
    "has_blocking_findings",
    "render_report_json",
    "render_report_markdown",
]

_REQUIREMENT_RE = re.compile(r"\b(?:FR|AC|SC)-\d+\b")


# @spec(FR-007): severity domain CRITICAL/HIGH/MEDIUM/LOW (070-analyze-gate)
class AnalyzeSeverity(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True)
class AnalyzeFinding:
    finding_id: str
    category: str
    severity: AnalyzeSeverity
    locations: tuple[str, ...]
    summary: str
    recommendation: str


@dataclass(frozen=True)
class RequirementCoverage:
    requirement_id: str
    has_plan_task: bool
    task_refs: tuple[str, ...]
    notes: str


@dataclass(frozen=True)
class PreImplAnalysisReport:
    """Independent structural coverage and semantic readiness observations.

    Attributes:
        findings: Artifact, structural and requested semantic findings with severity.
        coverage: Feature-qualified requirements and their literal plan or implementation
            references; references do not certify semantic compliance.
        coverage_percent: Percentage of requirements with plan or implementation
            references, or 100 when the inventory is empty; not a semantic readiness score.
        metrics: Requirement and finding counts, structural coverage percentage,
            and implementation presence represented as zero or one.
        semantic_status: ``not_requested`` for structural diagnostics, ``incomplete``
            for unavailable evidence, ``blocked`` for adverse verified conclusions,
            or ``covered`` for a current ready semantic receipt.
        coverage_kind: ``structural_reference``, the interpretation of coverage data.
    """

    findings: tuple[AnalyzeFinding, ...]
    coverage: tuple[RequirementCoverage, ...]
    coverage_percent: float
    metrics: dict[str, int | float]
    semantic_status: str = "incomplete"
    coverage_kind: str = "structural_reference"


# @spec(FR-006): deterministic AN-<cat>-<sha1[:8]> finding id (070-analyze-gate)
def _finding_id(
    category: str, severity: AnalyzeSeverity, locations: tuple[str, ...], summary: str
) -> str:
    token = f"{category}|{severity.value}|{'|'.join(locations)}|{summary}"
    digest = hashlib.sha1(token.encode("utf-8")).hexdigest()[:8]
    return f"AN-{category.upper()}-{digest}"


def _ordered_unique(tokens: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            ordered.append(token)
    return ordered


# @spec(FR-002): read-only cross-artifact analysis, never writes a file (070-analyze-gate)
def analyze_feature_artifacts(
    feature_dir: Path,
    constitution_path: Path,
    *,
    review_receipt: Path | None = None,
    structural_only: bool = False,
    prepared_review: PreparedReview | None = None,
) -> PreImplAnalysisReport:
    """Read structural coverage and semantic readiness without writing files.

    Args:
        feature_dir: Directory containing spec, plan and optional implementation.
        constitution_path: Constitution used to bind the semantic review context.
        review_receipt: Plan receipt override; defaults to .reviews/plan.json.
        structural_only: Skip semantic checks; references cannot certify readiness.
        prepared_review: Prepared context to verify; otherwise prepare from disk.
    Returns:
        Separate reference coverage and semantic findings; invalid receipts are incomplete.
    Raises:
        OSError: An existing feature artifact cannot be read.
        UnicodeError: An existing feature artifact is not valid UTF-8.
    """
    spec_path = feature_dir / "spec.md"
    plan_path = feature_dir / "plan.md"
    impl_path = feature_dir / "implementation.md"

    spec_text = spec_path.read_text(encoding="utf-8") if spec_path.is_file() else ""
    plan_text = plan_path.read_text(encoding="utf-8") if plan_path.is_file() else ""
    impl_present = impl_path.is_file()
    impl_text = impl_path.read_text(encoding="utf-8") if impl_present else ""

    findings = _missing_artifact_findings(spec_path, plan_path)

    semantic_status = "not_requested"
    if not structural_only:
        from validator.semantic_analysis import analyze_semantic_readiness

        semantic_status, semantic_findings = analyze_semantic_readiness(
            feature_dir,
            constitution_path,
            review_receipt,
            prepared_review,
        )
        findings.extend(semantic_findings)

    coverage, coverage_findings = _structural_coverage(
        feature_dir.name, spec_text, plan_text, impl_text, impl_present, semantic_status
    )
    findings.extend(coverage_findings)
    return _analysis_report(coverage, findings, impl_present, semantic_status)


def _analysis_report(
    coverage: list[RequirementCoverage],
    findings: list[AnalyzeFinding],
    impl_present: bool,
    semantic_status: str,
) -> PreImplAnalysisReport:
    """Summarize the same independent structural and semantic observations."""
    covered_count = sum(item.has_plan_task for item in coverage)
    total = len(coverage)
    # @spec(FR-011): coverage_percent closed-form, 100.0 when no requirements (070-analyze-gate)
    coverage_percent = round(covered_count / total * 100, 2) if total else 100.0

    metrics: dict[str, int | float] = {
        "total_requirements": total,
        "covered_requirements": covered_count,
        "coverage_percent": coverage_percent,
        "critical_count": sum(1 for f in findings if f.severity is AnalyzeSeverity.CRITICAL),
        "high_count": sum(1 for f in findings if f.severity is AnalyzeSeverity.HIGH),
        "implementation_present": 1 if impl_present else 0,
    }

    return PreImplAnalysisReport(
        findings=tuple(findings),
        coverage=tuple(coverage),
        coverage_percent=coverage_percent,
        metrics=metrics,
        semantic_status=semantic_status,
    )


def _missing_artifact_findings(spec_path: Path, plan_path: Path) -> list[AnalyzeFinding]:
    findings: list[AnalyzeFinding] = []
    # Missing canonical artifacts are CRITICAL.
    # @spec(FR-003): missing spec.md/plan.md -> CRITICAL artifact finding (070-analyze-gate)
    for name, present in (("spec.md", spec_path.is_file()), ("plan.md", plan_path.is_file())):
        if not present:
            summary = f"Missing required artifact: {name}"
            locations: tuple[str, ...] = (name,)
            findings.append(
                AnalyzeFinding(
                    finding_id=_finding_id(
                        "artifact", AnalyzeSeverity.CRITICAL, locations, summary
                    ),
                    category="artifact",
                    severity=AnalyzeSeverity.CRITICAL,
                    locations=locations,
                    summary=summary,
                    recommendation=f"Generate {name} before running the Analyze gate",
                )
            )

    return findings


def _structural_coverage(
    feature_name: str,
    spec_text: str,
    plan_text: str,
    impl_text: str,
    impl_present: bool,
    semantic_status: str,
) -> tuple[list[RequirementCoverage], list[AnalyzeFinding]]:
    findings: list[AnalyzeFinding] = []
    # Requirement coverage: covered iff the ID token appears in plan.md or implementation.md.
    # Missing references are diagnostic when a fresh grounded review covers the obligation.
    coverage_severity = (
        AnalyzeSeverity.LOW if semantic_status == "covered" else AnalyzeSeverity.HIGH
    )
    requirement_ids = _ordered_unique(_REQUIREMENT_RE.findall(spec_text))
    coverage: list[RequirementCoverage] = []
    plan_ids = set(_REQUIREMENT_RE.findall(plan_text))
    impl_ids = set(_REQUIREMENT_RE.findall(impl_text))
    for requirement_id in requirement_ids:
        refs: list[str] = []
        if requirement_id in plan_ids:
            refs.append("plan.md")
        if impl_present and requirement_id in impl_ids:
            refs.append("implementation.md")
        has_task = bool(refs)
        if has_task:
            notes = "structural reference present; semantic compliance is separate"
        else:
            notes = "no plan task references this requirement"
            findings.append(_coverage_gap(f"{feature_name}:{requirement_id}", coverage_severity))
        coverage.append(
            RequirementCoverage(
                requirement_id=f"{feature_name}:{requirement_id}",
                has_plan_task=has_task,
                task_refs=tuple(refs),
                notes=notes,
            )
        )

    return coverage, findings


def _coverage_gap(requirement_id: str, severity: AnalyzeSeverity) -> AnalyzeFinding:
    # Repair guidance retains the local anchor; finding identity remains feature-qualified.
    local_id = requirement_id.rsplit(":", 1)[-1]
    summary = f"Requirement {requirement_id} has no plan-task reference"
    locations = ("spec.md", "plan.md")
    return AnalyzeFinding(
        finding_id=_finding_id("coverage", severity, locations, summary),
        category="coverage",
        severity=severity,
        locations=locations,
        summary=summary,
        recommendation=f"Add a plan task that references {local_id}, or cite it explicitly",
    )


# @spec(FR-008): blocking iff any finding is CRITICAL or HIGH (070-analyze-gate)
def has_blocking_findings(report: PreImplAnalysisReport) -> bool:
    """True iff any finding is CRITICAL or HIGH (drives exit 1 — H3)."""
    return any(
        f.severity in (AnalyzeSeverity.CRITICAL, AnalyzeSeverity.HIGH) for f in report.findings
    )
