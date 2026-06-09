#!/usr/bin/env python3
# LiveSpec traceability anchors
# @spec(FR-008)
# @spec(FR-009)
# @spec(FR-010)
# @spec(FR-011)
# @spec(FR-012)

"""Migration v17: report and safely backfill root ``penflow/`` artifacts."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BackfillReport:
    """Mutable report assembled by the migration."""

    verdict: str
    sources: list[str] = field(default_factory=list)
    preserved: list[str] = field(default_factory=list)
    created: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)


REQUIRED_ARTIFACTS = (
    "flow-ui-contract",
    "ui.pen",
    "semantic-ui-tree.json",
    "expected-ui-tree.json",
    "code-ir.json",
)


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Usage: migrate-penflow-backfill.py <project-dir> <livespec-dir>", file=sys.stderr)
        return 2
    project = Path(argv[1]).resolve()
    report = build_report(project)
    write_report(project, report)
    print(f"Penflow backfill verdict: {report.verdict}")
    return 0


def build_report(project: Path) -> BackfillReport:
    """Build the Penflow backfill report without unsafe generation.

    # @spec FR-008: Penflow backfill report
    # @spec FR-009: Preserve complete root penflow workspace
    # @spec FR-010: Block when runtime UI source is absent
    # @spec FR-011: Report legacy .specs/design/ui.pen
    # @spec FR-012: Prevent secondary .pen creation
    #   - .specs/features/054-migration-planner-penflow-backfill/spec.md#fr-008
    """
    penflow = project / "penflow"
    legacy_ui_pen = project / ".specs" / "design" / "ui.pen"
    legacy_screens = project / ".specs" / "design" / "screens"
    report = BackfillReport(verdict="BLOCKED")
    if legacy_ui_pen.exists():
        report.sources.append(".specs/design/ui.pen - non-canonical legacy evidence")
    if legacy_screens.is_dir():
        report.sources.append(".specs/design/screens/ - legacy visual evidence")
    if _workspace_ready(penflow):
        report.verdict = "PASS"
        report.preserved.append("preserved existing complete root penflow workspace")
        report.preserved.extend(f"penflow/{name}" for name in REQUIRED_ARTIFACTS)
        return report
    if penflow.exists():
        report.preserved.extend(
            path.relative_to(project).as_posix()
            for path in sorted(penflow.rglob("*"))
            if path.is_file()
        )
        report.blockers.append("root penflow workspace is incomplete; no artifact overwritten")
    else:
        report.blockers.append("runtime UI source not detected")
    if not report.sources:
        report.sources.append("none")
    return report


def write_report(project: Path, report: BackfillReport) -> Path:
    """Write ``.specs/migrations/017-penflow-backfill-report.md``."""
    report_path = project / ".specs" / "migrations" / "017-penflow-backfill-report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(report), encoding="utf-8")
    return report_path


def render_report(report: BackfillReport) -> str:
    """Render the deterministic Markdown report body."""
    return "\n".join(
        [
            "# Migration 017 - Penflow Backfill Report",
            "",
            f"- **Verdict:** {report.verdict}",
            f"- **Verdict: {report.verdict}**",
            "",
            "## Sources Detected",
            *_bullets(report.sources),
            "",
            "## Artifacts Created",
            *_bullets(report.created or ["none"]),
            "",
            "## Artifacts Preserved",
            *_bullets(report.preserved or ["none"]),
            "",
            "## Blockers",
            *_bullets(report.blockers or ["none"]),
            "",
        ]
    )


def _workspace_ready(penflow: Path) -> bool:
    return all(_artifact_exists(penflow, name) for name in REQUIRED_ARTIFACTS)


def _artifact_exists(penflow: Path, name: str) -> bool:
    path = penflow / name
    return path.is_dir() if name == "flow-ui-contract" else path.is_file()


def _bullets(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
