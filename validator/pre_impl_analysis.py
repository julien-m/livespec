"""Read-only pre-implementation artifact analyzer (Feature B — Analyze gate).

Cross-checks a feature's ``spec.md`` and ``plan.md`` (and optional
``implementation.md``) BEFORE implementation, surfacing coverage gaps and
constitution violations. Pure analysis: ``analyze_feature_artifacts`` never
writes a file. All scoring is closed-form so findings are stable across reruns
on unchanged artifacts.

Severity contract (C3):
- CRITICAL — constitution MUST violation, or a missing ``spec.md``/``plan.md``.
  Nothing else is CRITICAL.
- HIGH — a requirement (``FR-###``/``AC-###``/``SC-###``) whose ID token appears
  in neither ``plan.md`` nor ``implementation.md``.

Exit semantics live in the CLI: exit 1 iff any finding is CRITICAL or HIGH.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

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
_MUST_NOT_RE = re.compile(r"MUST\s+NOT\s+(.+?)(?:[.\n]|$)", re.IGNORECASE)


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
    findings: tuple[AnalyzeFinding, ...]
    coverage: tuple[RequirementCoverage, ...]
    coverage_percent: float
    metrics: dict[str, int | float]


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


# @spec(FR-004): constitution MUST NOT phrase in spec/plan -> CRITICAL (070-analyze-gate)
def _constitution_violations(
    constitution_text: str, *, spec_text: str, plan_text: str
) -> list[AnalyzeFinding]:
    findings: list[AnalyzeFinding] = []
    haystack = f"{spec_text}\n{plan_text}".lower()
    for raw in _MUST_NOT_RE.findall(constitution_text):
        phrase = raw.strip()
        if not phrase:
            continue
        if phrase.lower() in haystack:
            summary = f"Constitution MUST NOT violation: '{phrase}' appears in spec or plan"
            locations = ("constitution.md",)
            findings.append(
                AnalyzeFinding(
                    finding_id=_finding_id(
                        "constitution", AnalyzeSeverity.CRITICAL, locations, summary
                    ),
                    category="constitution",
                    severity=AnalyzeSeverity.CRITICAL,
                    locations=locations,
                    summary=summary,
                    recommendation=f"Remove or rework the prohibited approach: {phrase}",
                )
            )
    return findings


# @spec(FR-002): read-only cross-artifact analysis, never writes a file (070-analyze-gate)
def analyze_feature_artifacts(feature_dir: Path, constitution_path: Path) -> PreImplAnalysisReport:
    """Analyze spec.md, plan.md, optional implementation.md WITHOUT writing files."""
    spec_path = feature_dir / "spec.md"
    plan_path = feature_dir / "plan.md"
    impl_path = feature_dir / "implementation.md"

    spec_text = spec_path.read_text(encoding="utf-8") if spec_path.is_file() else ""
    plan_text = plan_path.read_text(encoding="utf-8") if plan_path.is_file() else ""
    impl_present = impl_path.is_file()
    impl_text = impl_path.read_text(encoding="utf-8") if impl_present else ""
    constitution_text = (
        constitution_path.read_text(encoding="utf-8") if constitution_path.is_file() else ""
    )

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

    # Constitution MUST violations are CRITICAL.
    findings.extend(
        _constitution_violations(constitution_text, spec_text=spec_text, plan_text=plan_text)
    )

    # Requirement coverage: covered iff the ID token appears in plan.md or implementation.md.
    # @spec(FR-005): requirement covered iff token in plan/impl, else HIGH (070-analyze-gate)
    requirement_ids = _ordered_unique(_REQUIREMENT_RE.findall(spec_text))
    coverage: list[RequirementCoverage] = []
    covered_count = 0
    for requirement_id in requirement_ids:
        refs: list[str] = []
        if requirement_id in plan_text:
            refs.append("plan.md")
        if impl_present and requirement_id in impl_text:
            refs.append("implementation.md")
        has_task = bool(refs)
        if has_task:
            covered_count += 1
            notes = "covered"
        else:
            notes = "no plan task references this requirement"
            summary = f"Requirement {requirement_id} has no plan-task reference"
            locations = ("spec.md", "plan.md")
            findings.append(
                AnalyzeFinding(
                    finding_id=_finding_id("coverage", AnalyzeSeverity.HIGH, locations, summary),
                    category="coverage",
                    severity=AnalyzeSeverity.HIGH,
                    locations=locations,
                    summary=summary,
                    recommendation=(
                        f"Add a plan task that references {requirement_id}, or cite it explicitly"
                    ),
                )
            )
        coverage.append(
            RequirementCoverage(
                requirement_id=requirement_id,
                has_plan_task=has_task,
                task_refs=tuple(refs),
                notes=notes,
            )
        )

    total = len(requirement_ids)
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
    )


# @spec(FR-008): blocking iff any finding is CRITICAL or HIGH (070-analyze-gate)
def has_blocking_findings(report: PreImplAnalysisReport) -> bool:
    """True iff any finding is CRITICAL or HIGH (drives exit 1 — H3)."""
    return any(
        f.severity in (AnalyzeSeverity.CRITICAL, AnalyzeSeverity.HIGH) for f in report.findings
    )


# @spec(FR-009): render report as json + markdown report (070-analyze-gate)
def render_report_json(report: PreImplAnalysisReport) -> str:
    payload = {
        "findings": [
            {
                "finding_id": f.finding_id,
                "category": f.category,
                "severity": f.severity.value,
                "locations": list(f.locations),
                "summary": f.summary,
                "recommendation": f.recommendation,
            }
            for f in report.findings
        ],
        "coverage": [
            {
                "requirement_id": c.requirement_id,
                "has_plan_task": c.has_plan_task,
                "task_refs": list(c.task_refs),
                "notes": c.notes,
            }
            for c in report.coverage
        ],
        "coverage_percent": report.coverage_percent,
        "metrics": report.metrics,
    }
    return json.dumps(payload, indent=2)


def render_report_markdown(report: PreImplAnalysisReport) -> str:
    lines = ["## Specification Analysis Report", ""]
    lines.append("### Findings")
    if report.findings:
        lines.append("| ID | Category | Severity | Location(s) | Summary | Recommendation |")
        lines.append("|----|----------|----------|-------------|---------|----------------|")
        for f in report.findings:
            lines.append(
                f"| {f.finding_id} | {f.category} | {f.severity.value} | "
                f"{', '.join(f.locations)} | {f.summary} | {f.recommendation} |"
            )
    else:
        lines.append("_No findings._")
    lines.append("")
    lines.append("### Coverage Matrix")
    lines.append("| Requirement Key | Has Plan Task? | Task IDs | Notes |")
    lines.append("|-----------------|----------------|----------|-------|")
    for c in report.coverage:
        lines.append(
            f"| {c.requirement_id} | {'yes' if c.has_plan_task else 'no'} | "
            f"{', '.join(c.task_refs) or '—'} | {c.notes} |"
        )
    lines.append("")
    lines.append("### Metrics")
    for key, value in report.metrics.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"
