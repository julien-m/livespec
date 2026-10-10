"""Pure JSON and Markdown rendering for pre-implementation analysis reports."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # The analyzer re-exports renderers; annotations must not create a cycle.
    from validator.pre_impl_analysis import PreImplAnalysisReport


# @spec(FR-009): render report as json + markdown report (070-analyze-gate)
def render_report_json(report: PreImplAnalysisReport) -> str:
    """Serialize the analysis report as JSON without side effects.

    Args:
        report: Completed structural and semantic analysis.

    Returns:
        The complete report encoded as indented JSON.
    """
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
        "coverage_kind": report.coverage_kind,
        "semantic_status": report.semantic_status,
        "metrics": report.metrics,
    }
    return json.dumps(payload, indent=2)


def render_report_markdown(report: PreImplAnalysisReport) -> str:
    """Render the analysis report as Markdown without side effects.

    Args:
        report: Completed structural and semantic analysis.

    Returns:
        The findings, structural coverage and metrics with a trailing newline.
    """
    lines = [
        "## Specification Analysis Report",
        "",
        f"Semantic readiness: {report.semantic_status}",
        "",
    ]
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
    lines.append("### Structural Reference Coverage Matrix")
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
