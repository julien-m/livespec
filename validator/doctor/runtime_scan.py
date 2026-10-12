"""Runtime drift findings for ``livespec doctor`` (category ``runtime``).

The package-level ``validator.doctor.run_doctor`` is this module's wrapper: it runs
the existing project scanner unchanged, appends the shared runtime scanner findings
and recomputes the verdict with the scanner's status rules.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from validator.runtime.home import executing_root, resolve_home
from validator.runtime.inspection import runtime_findings

from . import scanner
from .models import DoctorFinding, DoctorReport, DoctorSeverity, DoctorStatus


# @spec FR-012: Runtime scanner and doctor
#   — .specs/features/083-pinned-runtime-isolation/spec.md#fr-012
def scan_runtime(project_root: Path) -> list[DoctorFinding]:
    """Return the shared runtime scanner findings as doctor findings.

    Args:
        project_root: Project root containing ``.specs/``.

    Returns:
        Findings identical to ``livespec runtime status`` for the default home.
    """
    home = resolve_home(None)
    return [
        DoctorFinding(
            code=finding.code,
            severity=DoctorSeverity(finding.severity.value),
            category="runtime",
            message=finding.message,
            path=finding.path,
            suggested_action=finding.suggested_action,
        )
        for finding in runtime_findings(project_root.resolve(), home, executing_root())
    ]


def _combined_status(
    base: DoctorStatus, extra: list[DoctorFinding], *, strict: bool
) -> DoctorStatus:
    # Scanner rules: any ERROR fails; a WARNING fails under --strict, else warns.
    has_error = any(item.severity == DoctorSeverity.ERROR for item in extra)
    has_warning = any(item.severity == DoctorSeverity.WARNING for item in extra)
    if base == DoctorStatus.FAIL or has_error or (has_warning and strict):
        return DoctorStatus.FAIL
    if base == DoctorStatus.WARN or has_warning:
        return DoctorStatus.WARN
    return DoctorStatus.OK


def run_doctor(
    project_root: Path,
    *,
    strict: bool = False,
    fix_plan: bool = False,
    apply_cleanup: bool = False,
) -> DoctorReport:
    """Run the project doctor audit including runtime drift findings.

    Args:
        project_root: Root containing ``.specs/``.
        strict: Promote warnings to errors.
        fix_plan: Include non-destructive cleanup proposals.
        apply_cleanup: Refuse destructive cleanup actions while reporting them.

    Returns:
        The scanner report with runtime findings appended and its status recomputed.
    """
    report = scanner.run_doctor(
        project_root, strict=strict, fix_plan=fix_plan, apply_cleanup=apply_cleanup
    )
    extra = scan_runtime(project_root)
    return replace(
        report,
        status=_combined_status(report.status, extra, strict=strict),
        findings=[*report.findings, *extra],
    )
