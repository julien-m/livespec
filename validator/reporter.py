"""Output formatting for validation results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.text import Text

if TYPE_CHECKING:  # Circular: engine imports reporter indirectly
    from .engine import FileResult


def report(
    results: list[FileResult],
    excluded: list[str],
    output_format: str = "compact",
    specs_root: Path | None = None,
) -> str | None:
    """Format and display validation results.

    Args:
        results: Validation results to display.
        excluded: List of excluded relative paths.
        output_format: One of "compact", "full", or "json".
        specs_root: Root directory for relative path display.

    Returns:
        JSON string for json format, None for terminal formats.
    """
    if output_format == "json":
        return _report_json(results, excluded, specs_root)
    elif output_format == "full":
        _report_full(results, specs_root)
        return None
    else:
        _report_compact(results, specs_root)
        return None


def _rel_path(path: Path, specs_root: Path | None) -> str:
    """Get display path relative to specs_root or cwd."""
    if specs_root:
        try:
            return str(path.relative_to(specs_root.parent))
        except ValueError:
            pass
    return str(path)


def _report_compact(results: list[FileResult], specs_root: Path | None) -> None:
    """One-line-per-file output for hooks."""
    console = Console(stderr=True)

    for r in results:
        rel = _rel_path(r.path, specs_root)
        if r.has_errors:
            line = Text()
            line.append("ERROR   ", style="bold red")
            line.append(f"{rel} ", style="bold")
            line.append(f"({len(r.errors)} error(s)", style="red")
            if r.has_warnings:
                line.append(f", {len(r.warnings)} warning(s)", style="yellow")
            line.append(f") Score: {r.score}/100")
            console.print(line)
        elif r.has_warnings:
            line = Text()
            line.append("WARN    ", style="bold yellow")
            line.append(f"{rel} ", style="bold")
            line.append(f"({len(r.warnings)} warning(s)) ", style="yellow")
            line.append(f"Score: {r.score}/100")
            console.print(line)
        else:
            line = Text()
            line.append("OK      ", style="bold green")
            line.append(f"{rel} ", style="bold")
            line.append(f"Score: {r.score}/100")
            console.print(line)


def _report_full(results: list[FileResult], specs_root: Path | None) -> None:
    """Detailed grouped output."""
    console = Console(stderr=True)

    for r in results:
        rel = _rel_path(r.path, specs_root)

        if r.has_errors:
            console.print(f"\n[bold red]ERROR[/]  [bold]{rel}[/]")
        elif r.has_warnings:
            console.print(f"\n[bold yellow]WARN[/]  [bold]{rel}[/]")
        else:
            console.print(f"\n[bold green]OK[/]      [bold]{rel}[/]")
            continue

        for err in r.errors:
            console.print(f"  [red]\\[{err.category}][/] {err.message}")
        for warn in r.warnings:
            console.print(f"  [yellow]\\[{warn.category}][/] {warn.message}")

        console.print(f"  Score: {r.score}/100")

    # Summary
    total_errors = sum(len(r.errors) for r in results)
    total_warnings = sum(len(r.warnings) for r in results)
    console.print(
        f"\n[bold]Total: {len(results)} file(s),"
        f" {total_errors} error(s),"
        f" {total_warnings} warning(s)[/]"
    )


def _report_json(results: list[FileResult], excluded: list[str], specs_root: Path | None) -> str:
    """Machine-readable JSON output."""
    files = []
    for r in results:
        files.append(
            {
                "path": _rel_path(r.path, specs_root),
                "type": r.file_type,
                "errors": [{"category": e.category, "message": e.message} for e in r.errors],
                "warnings": [{"category": w.category, "message": w.message} for w in r.warnings],
                "score": r.score,
            }
        )

    output = {
        "files": files,
        "excluded": excluded,
        "summary": {
            "total_files": len(results),
            "total_errors": sum(len(r.errors) for r in results),
            "total_warnings": sum(len(r.warnings) for r in results),
            "files_with_errors": sum(1 for r in results if r.has_errors),
        },
    }

    return json.dumps(output, indent=2)


def report_score_only(results: list[FileResult], specs_root: Path | None) -> None:
    """Show only scores per file.

    Args:
        results: Validation results to display.
        specs_root: Root directory for relative path display.
    """
    console = Console(stderr=True)
    for r in results:
        rel = _rel_path(r.path, specs_root)
        color = "green" if r.score >= 80 else "yellow" if r.score >= 50 else "red"
        console.print(f"[{color}]{r.score:3d}/100[/]  {rel}")


def report_excluded(excluded: list[str]) -> None:
    """Show list of excluded files.

    Args:
        excluded: List of excluded relative paths.
    """
    console = Console(stderr=True)
    if not excluded:
        console.print("[dim]No files excluded[/]")
        return
    console.print(f"[bold]Excluded files ({len(excluded)}):[/]")
    for path in sorted(excluded):
        console.print(f"  [dim]{path}[/]")
