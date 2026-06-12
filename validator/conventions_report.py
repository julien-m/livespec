# LiveSpec traceability anchors
# @spec(FR-004)

"""Debt report rendering for conventions verification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from .conventions_gate import GateResult, GateSeverity, GateViolation

_SEVERITY_RANK = {"error": 0, "warning": 1}
_MAX_REPORTED_FILES = 200
_MAX_REPORTED_VIOLATIONS_PER_FILE = 20


def write_debt_report(project_root: Path, result: GateResult) -> tuple[Path, Path]:
    """Write Markdown and JSON debt reports.

    Args:
        project_root: Project root.
        result: Verification result.

    Returns:
        Tuple of `(markdown_path, json_path)`.
    """
    output_dir = project_root / ".specs" / "conventions"
    output_dir.mkdir(parents=True, exist_ok=True)
    grouped = _group_debt(result.violations)
    payload: dict[str, object] = {
        "verdict": result.verdict.value,
        "files": grouped,
        "blockers": [blocker.to_dict() for blocker in result.blockers],
        "summary": _summary(result.violations, grouped),
    }
    debt_json = output_dir / "debt.json"
    debt_md = output_dir / "debt-report.md"
    debt_json.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    debt_md.write_text(_render_debt_markdown(payload), encoding="utf-8")
    return debt_md, debt_json


def _group_debt(violations: list[GateViolation]) -> list[dict[str, object]]:
    grouped: dict[str, list[GateViolation]] = {}
    for violation in violations:
        grouped.setdefault(violation.path, []).append(violation)
    ranked = sorted(grouped.items(), key=lambda pair: _sort_key(pair[0], pair[1]))
    return [
        {
            "path": path,
            "worst_severity": _worst_severity(items),
            "violation_count": len(items),
            "violations": [item.to_dict() for item in _reported_violations(items)],
            "omitted_violations": max(0, len(items) - _MAX_REPORTED_VIOLATIONS_PER_FILE),
            "suppressions": sum(
                1 for item in items if item.rule_id == "builtin.suppression_directives"
            ),
        }
        for path, items in ranked[:_MAX_REPORTED_FILES]
    ]


def _summary(
    violations: list[GateViolation],
    grouped: list[dict[str, object]],
) -> dict[str, int]:
    included_violations = sum(cast(int, file_entry["violation_count"]) for file_entry in grouped)
    reported_violations = sum(
        len(cast(list[dict[str, object]], file_entry["violations"])) for file_entry in grouped
    )
    paths = {violation.path for violation in violations}
    return {
        "total_files": len(paths),
        "reported_files": len(grouped),
        "omitted_files": max(0, len(paths) - _MAX_REPORTED_FILES),
        "total_violations": len(violations),
        "included_violations": included_violations,
        "reported_violations": reported_violations,
    }


def _reported_violations(items: list[GateViolation]) -> list[GateViolation]:
    return sorted(items, key=lambda item: (_SEVERITY_RANK[_severity_value(item)], item.line))[
        :_MAX_REPORTED_VIOLATIONS_PER_FILE
    ]


def _sort_key(path: str, items: list[GateViolation]) -> tuple[int, int, str]:
    return (_SEVERITY_RANK[_worst_severity(items)], -len(items), path)


def _worst_severity(items: list[GateViolation]) -> str:
    return min(
        (_severity_value(item) for item in items),
        key=lambda severity: _SEVERITY_RANK[severity],
    )


def _severity_value(violation: GateViolation) -> str:
    return (
        violation.severity.value
        if isinstance(violation.severity, GateSeverity)
        else violation.severity
    )


def _render_debt_markdown(payload: dict[str, object]) -> str:
    files = cast(list[dict[str, object]], payload["files"])
    summary = cast(dict[str, int], payload["summary"])
    lines = [
        "# Conventions Debt Report",
        "",
        f"Verdict: {payload['verdict']}",
        "",
        f"Files: {summary['reported_files']}/{summary['total_files']} reported",
        f"Violations: {summary['reported_violations']}/{summary['total_violations']} listed",
        "",
    ]
    for file_entry in files:
        lines.append(
            f"## {file_entry['path']} ({file_entry['worst_severity']}, "
            f"{file_entry['violation_count']} total)"
        )
        for violation in cast(list[dict[str, object]], file_entry["violations"]):
            lines.append(
                f"- {violation['severity']} {violation['rule_id']}:{violation['line']} "
                f"{violation['message']}"
            )
        omitted = cast(int, file_entry["omitted_violations"])
        if omitted > 0:
            lines.append(f"- ... {file_entry['omitted_violations']} more violation(s) omitted")
        lines.append("")
    return "\n".join(lines)
