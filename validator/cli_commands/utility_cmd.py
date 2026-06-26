# @spec(AC-022)
# @spec(FR-010)

# LiveSpec traceability anchors
# @spec(FR-007)
# @spec(FR-008)
# @spec(FR-009)

"""Deterministic utility command backends for LiveSpec."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import typer

from ..cli_commands._common import emit_summary
from .conventions_cmd import conventions_app, refresh_conventions_command

REPO_OPTION = typer.Option(Path("."), "--repo", help="Project repository root.")
JSON_OPTION = typer.Option(False, "--json", help="Emit JSON.")
SOURCE_DIR_OPTION = typer.Option(Path("."), "--source-dir", help="Source dir to scan.")
FEATURE_OPTION = typer.Option("", "--feature", help="Feature slug for the payload.")
NO_OPEN_OPTION = typer.Option(False, "--no-open", help="Do not open a browser.")


def register(app: typer.Typer) -> None:
    """Register deterministic utility commands."""
    app.command(name="status", help="Show a read-only LiveSpec project status.")(status_command)
    app.command(
        name="play-coverage",
        help="Build spec anchor coverage data for the coverage playground.",
    )(play_coverage_command)
    app.command(
        name="refresh-conventions",
        help="Refresh .conventions/index.md and manifest.yaml.",
    )(refresh_conventions_command)
    app.add_typer(conventions_app, name="conventions")


def status_command(repo: Path = REPO_OPTION, json_out: bool = JSON_OPTION) -> None:
    """Show a factual read-only status summary.

    # @spec FR-007: deterministic status backend
    #   — .specs/features/048-command-validation-hardening/spec.md#fr-007
    """
    report = build_status_report(repo.resolve())
    if json_out:
        typer.echo(json.dumps(report, indent=2))
    else:
        typer.echo("LiveSpec status")
        typer.echo(f"features: {report['features']['total']}")
        typer.echo(
            "roadmap: "
            f"{report['roadmap']['mvp']['open']} MVP open, "
            f"{report['roadmap']['postmvp']['open']} Post-MVP open, "
            f"{report['roadmap']['future']['open']} Future open"
        )
        emit_summary("status", "OK", features=report["features"]["total"])
    raise typer.Exit(0)


def build_status_report(repo_root: Path) -> dict[str, Any]:
    """Build the read-only status report for a project."""
    specs = repo_root / ".specs"
    if not specs.is_dir():
        typer.echo("Error: .specs/ directory not found", err=True)
        raise typer.Exit(2)

    features_dir = specs / "features"
    statuses: dict[str, int] = {}
    total = 0
    if features_dir.is_dir():
        for spec_path in sorted(features_dir.glob("*/spec.md")):
            total += 1
            status = _frontmatter_value(spec_path, "status") or "Unknown"
            statuses[status] = statuses.get(status, 0) + 1

    return {
        "project_root": str(repo_root),
        "features": {"total": total, "by_status": statuses},
        "roadmap": _roadmap_counts(specs / "roadmap.md"),
    }


def play_coverage_command(
    repo: Path = REPO_OPTION,
    source_dir: Path = SOURCE_DIR_OPTION,
    feature: str = FEATURE_OPTION,
    no_open: bool = NO_OPEN_OPTION,
    json_out: bool = JSON_OPTION,
) -> None:
    """Build coverage data for the spec coverage playground.

    # @spec FR-008: deterministic play-coverage backend
    #   — .specs/features/048-command-validation-hardening/spec.md#fr-008
    """
    repo_root = repo.resolve()
    if not (repo_root / ".specs").is_dir():
        typer.echo("Error: .specs/ directory not found", err=True)
        raise typer.Exit(2)
    source_root = source_dir.resolve()
    anchors = _scan_spec_anchors(source_root)
    data = {
        "feature": feature,
        "source_dir": str(source_root),
        "anchor_count": len(anchors),
        "anchors": anchors,
        "opened": not no_open,
    }
    target_dir = repo_root / "playground" / "coverage"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "data.json"
    target.write_text(json.dumps(data, indent=2), encoding="utf-8")
    if json_out:
        typer.echo(json.dumps(data, indent=2))
    else:
        typer.echo(f"playground coverage data written: {target}")
        typer.echo(f"anchors: {len(anchors)}")
    raise typer.Exit(0)


def _frontmatter_value(path: Path, key: str) -> str | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    match = re.search(rf"^{re.escape(key)}:\s*\"?([^\"\n]+)\"?", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def _roadmap_counts(path: Path) -> dict[str, dict[str, int]]:
    tiers = {"mvp": "mvp", "postmvp": "postmvp", "future": "future"}
    counts = {name: {"open": 0, "done": 0} for name in tiers.values()}
    if not path.is_file():
        return counts
    current: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        for marker, tier in tiers.items():
            if f"roadmap:{marker}:start" in line:
                current = tier
            elif f"roadmap:{marker}:end" in line:
                current = None
        if current is None:
            continue
        if line.startswith("- [ ]"):
            counts[current]["open"] += 1
        elif line.startswith("- [x]"):
            counts[current]["done"] += 1
    return counts


def _scan_spec_anchors(source_root: Path) -> list[dict[str, Any]]:
    anchors: list[dict[str, Any]] = []
    if not source_root.exists():
        return anchors
    pattern = re.compile(r"@spec\s+(FR|AC)-(\d{3})")
    for path in sorted(p for p in source_root.rglob("*") if p.is_file()):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            for match in pattern.finditer(line):
                anchors.append(
                    {
                        "path": str(path),
                        "line": line_number,
                        "kind": match.group(1),
                        "id": f"{match.group(1)}-{match.group(2)}",
                    }
                )
    return anchors


__all__ = [
    "build_status_report",
    "conventions_app",
    "play_coverage_command",
    "refresh_conventions_command",
    "register",
    "status_command",
]
