"""Formatting for coherence validation results."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from rich.console import Console
from rich.text import Text

from .violation import Severity, Violation

if TYPE_CHECKING:  # Circular: rule_engine imports from report indirectly
    from pathlib import Path

    from .rule_engine import CoherenceResult


_SEVERITY_STYLE = {
    Severity.ERROR: ("ERROR ", "bold red"),
    Severity.WARNING: ("WARN  ", "bold yellow"),
    Severity.INFO: ("INFO  ", "dim"),
}


def report_coherence(
    result: CoherenceResult,
    output_format: str = "compact",
) -> str | None:
    """Format and display coherence validation results.

    Args:
        result: CoherenceResult containing violations and graph data.
        output_format: Output format (compact, full, or json).

    Returns:
        JSON string for json format, None for terminal formats.
    """
    if output_format == "json":
        return _report_json(result)
    else:
        _report_console(result)
        return None


def _report_console(result: CoherenceResult) -> None:
    """Rich console output grouped by rule group."""
    console = Console(stderr=True)

    # Header
    n_features = len(result.graph.features)
    n_roadmap = len(result.graph.roadmap)
    console.print(f"\n[bold]LiveSpec — Coherence inter-fichiers[/]")
    console.print(
        f"Graph : {n_features} features — "
        f"{n_roadmap} roadmap items — "
        f"{len(result.graph.readme_entries)} README entries"
    )
    console.print()

    if not result.violations and not result.suppressed:
        console.print("[bold green]No coherence issues found.[/]\n")
        return

    # Group violations by rule group (R1, R2, etc.)
    groups: dict[str, list[Violation]] = {}
    for v in result.violations:
        group = v.rule_id.split(".")[0]
        groups.setdefault(group, []).append(v)

    # Also add suppressed violations
    for v in result.suppressed:
        group = v.rule_id.split(".")[0]
        groups.setdefault(group, []).append(v)

    group_names = {
        "R1": "Roadmap <-> Features",
        "R2": "Status <-> Files",
        "R3": "@spec anchors",
        "R4": "README sync",
        "R5": "Stack <-> Preflight",
        "R6": "Changelog refs",
    }

    for group_id in sorted(groups.keys()):
        name = group_names.get(group_id, group_id)
        console.print(f"[bold]{group_id} — {name}[/]")
        for v in groups[group_id]:
            label, style = _SEVERITY_STYLE.get(
                v.severity, ("???   ", "dim")
            )
            line = Text()
            line.append(f"  [{v.rule_id}] ", style="bold")
            line.append(label, style=style)
            line.append(v.message)
            console.print(line)
            if v.fix_hint:
                console.print(f"           [dim]Fix : {v.fix_hint}[/]")
        console.print()

    # Summary
    n_errors = len(result.errors)
    n_warnings = len(result.warnings)
    n_infos = len(result.infos)
    n_suppressed = len(result.suppressed)

    summary = Text()
    summary.append("Summary : ", style="bold")
    summary.append(f"{n_errors} error(s)", style="red" if n_errors else "green")
    summary.append(f" — {n_warnings} warning(s)", style="yellow" if n_warnings else "dim")
    summary.append(f" — {n_infos} info(s)", style="dim")
    if n_suppressed:
        summary.append(f" — {n_suppressed} suppressed (in-progress)", style="dim")
    console.print(summary)
    console.print()


def _report_json(result: CoherenceResult) -> str:
    """Machine-readable JSON output."""
    violations = []
    for v in result.violations:
        violations.append({
            "rule_id": v.rule_id,
            "severity": v.severity.value,
            "message": v.message,
            "context": v.context,
            "fix_hint": v.fix_hint,
        })

    suppressed = []
    for v in result.suppressed:
        suppressed.append({
            "rule_id": v.rule_id,
            "severity": v.severity.value,
            "message": v.message,
        })

    output = {
        "graph": {
            "features": len(result.graph.features),
            "roadmap_items": len(result.graph.roadmap),
            "readme_entries": len(result.graph.readme_entries),
        },
        "violations": violations,
        "suppressed": suppressed,
        "summary": {
            "errors": len(result.errors),
            "warnings": len(result.warnings),
            "infos": len(result.infos),
            "suppressed": len(result.suppressed),
        },
    }

    return json.dumps(output, indent=2)
