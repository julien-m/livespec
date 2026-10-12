"""Idempotent bugfix traceability in the owner feature files (feature 084 FR-010)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .gate import GateRequest, evaluate_gate
from .models import GateReport

_SECTION = "## Bugfix Receipts"
_TABLE_HEADER = (
    "| Date | Requirement | Regression tests | RED receipt | GREEN receipt |\n"
    "|---|---|---|---|---|\n"
)


@dataclass(frozen=True)
class RecordResult:
    """Closing gate report (None when already recorded) and the files actually changed."""

    report: GateReport | None
    written: tuple[str, ...]
    already_recorded: bool = False


def _receipt(invocation: str) -> str:
    return f".specs/.execution/{invocation}/receipt.json"


def _changelog_entry(report: GateReport, request: GateRequest, summary: str, today: date) -> str:
    # The entry follows the spec-system changelog format, plus both receipts and a
    # marker keyed by the GREEN invocation that makes a second record a no-op.
    files = ", ".join(report.counted_files) or "none"
    requirements = ", ".join(request.requirements) or "implementation"
    spec_modified = (
        "Yes (non-requirement lines only)"
        if any(path.endswith("/spec.md") for path in report.counted_files)
        else "No"
    )
    return (
        f"\n## {today.isoformat()} — [Bugfix]: {summary}\n\n"
        "- **Type:** Bugfix\n"
        f"- **Spec modified:** {spec_modified}\n"
        f"- **Code modified:** {files}\n"
        f"- **AC impacted:** {requirements}\n"
        "- **Author:** livespec bugfix record\n"
        f"- **Base revision:** {request.base}\n"
        f"- **Regression tests:** {', '.join(report.regression_tests)}\n"
        f"- **RED receipt:** `{_receipt(report.red_invocation)}`\n"
        f"- **GREEN receipt:** `{_receipt(report.green_invocation)}`\n"
        f"<!-- bugfix:{report.green_invocation} -->\n"
    )


def _receipts_row(report: GateReport, request: GateRequest, today: date) -> str:
    requirements = ", ".join(request.requirements) or "implementation"
    tests = ", ".join(f"`{test}`" for test in report.regression_tests)
    return (
        f"| {today.isoformat()} | {requirements} | {tests} | "
        f"`{_receipt(report.red_invocation)}` | `{_receipt(report.green_invocation)}` |\n"
    )


def _with_row(text: str, row: str) -> str:
    """Append the row to the Bugfix Receipts table, creating the section when absent."""
    lines = text.splitlines(keepends=True)
    if not any(line.strip() == _SECTION for line in lines):
        separator = "" if text.endswith("\n") else "\n"
        return f"{text}{separator}\n{_SECTION}\n\n{_TABLE_HEADER}{row}"
    start = next(i for i, line in enumerate(lines) if line.strip() == _SECTION)
    insert_at = start + 1
    # Insert after the last table line of the section, before the next heading.
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("#"):
            break
        if lines[index].lstrip().startswith("|"):
            insert_at = index + 1
    lines.insert(insert_at, row)
    return "".join(lines)


# @spec FR-010: Idempotent bugfix trace
#   — .specs/features/084-bugfix-lane/spec.md#fr-010
def record_bugfix(request: GateRequest, summary: str, today: date) -> RecordResult:
    """Append the trace once; write nothing when ineligible.

    When both files already reference the GREEN invocation, return without re-running
    the gate: the first record may itself have made GREEN stale (for example when
    spec.md links implementation.md), and a repeat must stay a no-op (AC-012).
    """
    feature_dir = request.project_root / ".specs" / "features" / request.feature
    changelog = feature_dir / "changelog.md"
    implementation = feature_dir / "implementation.md"
    invocation = _invocation(request.green)
    if invocation and _references(changelog, implementation, invocation) == (True, True):
        return RecordResult(None, (), already_recorded=True)
    report = evaluate_gate(request)
    if report.verdict != "ELIGIBLE":
        return RecordResult(report, ())
    marker = f"<!-- bugfix:{report.green_invocation} -->"
    written: list[str] = []
    changelog_text = changelog.read_text(encoding="utf-8") if changelog.exists() else ""
    if marker not in changelog_text:
        entry = _changelog_entry(report, request, summary, today)
        changelog.write_text(changelog_text.rstrip("\n") + "\n" + entry, encoding="utf-8")
        written.append(str(changelog))
    implementation_text = implementation.read_text(encoding="utf-8")
    if _receipt(report.green_invocation) not in implementation_text:
        row = _receipts_row(report, request, today)
        implementation.write_text(_with_row(implementation_text, row), encoding="utf-8")
        written.append(str(implementation))
    return RecordResult(report, tuple(written))


def _invocation(receipt: Path | None) -> str:
    """Return the invocation id declared by a receipt file, or "" when unreadable."""
    if receipt is None:
        return ""
    try:
        value: object = json.loads(receipt.read_text(encoding="utf-8")).get("invocation", "")
    except (OSError, UnicodeError, ValueError, AttributeError):
        # Unreadable receipts cannot shortcut anything; the gate reports them.
        return ""
    return value if isinstance(value, str) else ""


def _references(changelog: Path, implementation: Path, invocation: str) -> tuple[bool, bool]:
    marker = f"<!-- bugfix:{invocation} -->"
    in_changelog = changelog.exists() and marker in changelog.read_text(encoding="utf-8")
    in_map = implementation.exists() and _receipt(invocation) in implementation.read_text(
        encoding="utf-8"
    )
    return in_changelog, in_map
