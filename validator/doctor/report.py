"""Output renderers for ``livespec doctor``."""

from __future__ import annotations

import json

from .models import DoctorReport, DoctorSeverity


def render_doctor_json(report: DoctorReport) -> str:
    """Render a stable JSON report."""
    # @spec AC-010: JSON — .specs/features/055-spec-doctor-project-health/spec.md#ac-010
    return json.dumps(report.to_dict(), indent=2)


def render_doctor_text(report: DoctorReport, *, full: bool = False) -> str:
    """Render a compact or full terminal report."""
    findings = report.effective_findings
    errors = sum(1 for finding in findings if finding.severity == DoctorSeverity.ERROR)
    warnings = sum(1 for finding in findings if finding.severity == DoctorSeverity.WARNING)
    infos = sum(1 for finding in findings if finding.severity == DoctorSeverity.INFO)
    lines = [
        f"LiveSpec doctor: {report.status.value}",
        f"summary: errors={errors} warnings={warnings} infos={infos} findings={len(findings)}",
    ]
    for finding in findings:
        target = f" {finding.feature}" if finding.feature else ""
        lines.append(f"{finding.severity.value} {finding.code}{target}: {finding.message}")
        if full and finding.suggested_action:
            lines.append(f"  fix: {finding.suggested_action}")
    if report.cleanup_actions:
        lines.append("cleanup plan:")
        for action in report.cleanup_actions:
            suffix = " refused" if action.refused else ""
            lines.append(f"- {action.code} {action.path}:{suffix} {action.description}")
    return "\n".join(lines)


__all__ = ["render_doctor_json", "render_doctor_text"]
