"""Scorecard reporting — compact table and JSON output."""

from __future__ import annotations

import json

from rich.console import Console
from rich.table import Table
from rich.text import Text

from .scorecard import AXIS_WEIGHTS, ProjectScore

# Short labels for table headers
_AXIS_LABELS: dict[str, str] = {
    "structural_completeness": "L1:Struct",
    "artifact_quality": "L2:Quality",
    "ac_fr_coverage": "L2:Coverage",
    "semantic_coherence": "L4:Semantic",
    "mermaid_richness": "L2+4:Mermaid",
}


def _progress_bar(value: float, width: int = 20) -> str:
    """Render a text progress bar."""
    filled = int(value / 100 * width)
    bar = "\u2588" * filled + "\u2591" * (width - filled)
    return f"[{bar}] {value:5.1f}"


def _score_color(value: int | float) -> str:
    """Return a Rich color name based on score."""
    if value >= 80:
        return "green"
    if value >= 60:
        return "yellow"
    if value >= 40:
        return "bright_red"
    return "red"


def report_scorecard(project_score: ProjectScore, format: str = "compact") -> str | None:
    """Format and display the scorecard.

    Returns JSON string for json format, None for compact (printed to terminal).
    """
    if format == "json":
        return _report_json(project_score)

    _report_compact(project_score)
    return None


def _report_compact(project_score: ProjectScore) -> None:
    """Print a Rich table to the terminal."""
    console = Console(stderr=True)

    if not project_score.features:
        console.print("[dim]No features to score.[/dim]")
        return

    table = Table(title="LiveSpec Scorecard", show_lines=True)
    table.add_column("Feature", style="bold")
    for axis_key, label in _AXIS_LABELS.items():
        weight = AXIS_WEIGHTS[axis_key]
        table.add_column(f"{label} ({weight:.0%})", justify="right")
    table.add_column("Total", justify="right", style="bold")

    for fs in project_score.features:
        row: list[str | Text] = [fs.feature_name]
        for axis_key in _AXIS_LABELS:
            val = fs.axes.get(axis_key, 0)
            color = _score_color(val)
            row.append(Text(str(val), style=color))
        color = _score_color(fs.total)
        row.append(Text(f"{fs.total:.1f}", style=color))
        table.add_row(*row)

    console.print(table)

    # Project total with progress bar
    bar = _progress_bar(project_score.total)
    color = _score_color(project_score.total)
    console.print(f"\n  Project score: [{color}]{bar}[/{color}]\n")

    # Axis 4 note
    console.print("  [dim]L4:Semantic = 50 (stub, LLM not configured)[/dim]\n")


def _report_json(project_score: ProjectScore) -> str:
    """Return machine-readable JSON."""
    data = {
        "total": project_score.total,
        "features": [
            {
                "name": fs.feature_name,
                "axes": fs.axes,
                "weights": fs.weights,
                "total": fs.total,
            }
            for fs in project_score.features
        ],
    }
    return json.dumps(data, indent=2)
