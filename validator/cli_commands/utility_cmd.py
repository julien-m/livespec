"""Deterministic utility command backends for LiveSpec."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import typer

from ..cli_commands._common import emit_summary

REPO_OPTION = typer.Option(Path("."), "--repo", help="Project repository root.")
JSON_OPTION = typer.Option(False, "--json", help="Emit JSON.")
SOURCE_DIR_OPTION = typer.Option(Path("."), "--source-dir", help="Source dir to scan.")
FEATURE_OPTION = typer.Option("", "--feature", help="Feature slug for the payload.")
NO_OPEN_OPTION = typer.Option(False, "--no-open", help="Do not open a browser.")
FULL_OPTION = typer.Option(False, "--full", help="Regenerate even when present.")

conventions_app = typer.Typer(name="conventions", help="Manage LiveSpec conventions.")


def register(app: typer.Typer) -> None:
    """Register deterministic utility commands."""
    app.command(name="status", help="Show a read-only LiveSpec project status.")(
        status_command
    )
    app.command(
        name="play-coverage",
        help="Build spec anchor coverage data for the coverage playground.",
    )(play_coverage_command)
    app.command(
        name="refresh-conventions",
        help="Refresh .conventions/index.md and manifest.yaml.",
    )(refresh_conventions_command)
    app.add_typer(conventions_app, name="conventions")


def status_command(
    repo: Path = REPO_OPTION,
    json_out: bool = JSON_OPTION,
) -> None:
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

    roadmap = _roadmap_counts(specs / "roadmap.md")
    return {
        "project_root": str(repo_root),
        "features": {"total": total, "by_status": statuses},
        "roadmap": roadmap,
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


@conventions_app.command("refresh")
def refresh_conventions_command(
    repo: Path = REPO_OPTION,
    full: bool = FULL_OPTION,
) -> None:
    """Refresh the project conventions bundle.

    # @spec FR-009: deterministic conventions refresh backend
    #   — .specs/features/048-command-validation-hardening/spec.md#fr-009
    """
    repo_root = repo.resolve()
    stack_path = repo_root / ".specs" / "stacks" / "_default.md"
    if not stack_path.is_file():
        typer.echo("Error: .specs/stacks/_default.md not found", err=True)
        raise typer.Exit(2)
    conventions_dir = repo_root / ".conventions"
    index_path = conventions_dir / "index.md"
    manifest_path = conventions_dir / "manifest.yaml"
    if index_path.is_file() and manifest_path.is_file() and not full:
        typer.echo("conventions already present")
        raise typer.Exit(0)

    conventions_dir.mkdir(parents=True, exist_ok=True)
    stack_text = stack_path.read_text(encoding="utf-8").lower()
    domains = ["code"]
    if _is_web_ui_stack(stack_text):
        domains.extend(
            [
                "design-tokens",
                "design-components",
                "design-views",
                "design-quality",
            ]
        )
    index_path.write_text(_render_conventions_index(repo_root.name, domains), encoding="utf-8")
    manifest_path.write_text(_render_conventions_manifest(domains, stack_text), encoding="utf-8")
    typer.echo("conventions refreshed")
    typer.echo(f"  updated  {index_path.relative_to(repo_root)}")
    typer.echo(f"  updated  {manifest_path.relative_to(repo_root)}")
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


def _render_conventions_index(project_name: str, domains: list[str]) -> str:
    lines = [
        f"# Conventions · {project_name}",
        "",
        "> Generated by `livespec conventions refresh`.",
        "",
    ]
    if "code" in domains:
        lines.extend(
            [
                "## code [code, tests, logging, naming, Python, CLI, architecture]",
                "→ $AIRESOURCES/code-conventions/general.md, python.md, "
                "javascript.md, cli.md, stack-commands.md",
                "",
            ]
        )
    if "design-tokens" in domains:
        lines.extend(
            [
                "## design-tokens [CSS, colors, spacing, typography, motion, dark mode]",
                "→ $AIRESOURCES/design/tokens/colors.md, spacing.md, typography.md, "
                "motion.md, cross-platform.md",
                "",
            ]
        )
    if "design-components" in domains:
        lines.extend(
            [
                "## design-components [button, input, form, toast, modal, nav, list, badge]",
                "→ $AIRESOURCES/design/components/buttons.md, forms.md, navigation.md, "
                "lists.md, modals.md, feedback.md",
                "",
            ]
        )
    if "design-views" in domains:
        lines.extend(
            [
                "## design-views [page layout, dashboard, settings, auth, mockup specs]",
                "→ $AIRESOURCES/design/references/app-views.md, app-views-catalog.md, "
                "app-ui.md, mockup-specs.md",
                "",
            ]
        )
    if "design-quality" in domains:
        lines.extend(
            [
                "## design-quality [a11y audit, WCAG, keyboard nav, ARIA, visual QA]",
                "→ $AIRESOURCES/design/quality/accessibility.md, ui-rules.md",
                "",
            ]
        )
    return "\n".join(lines)


def _render_conventions_manifest(domains: list[str], stack_text: str) -> str:
    if _is_web_ui_stack(stack_text):
        stack_hint = "web"
    elif "python" in stack_text:
        stack_hint = "python"
    else:
        stack_hint = "generic"
    lines = ["version: 1", f"stack_hint: {stack_hint}", "domains:"]
    for domain in domains:
        lines.append(f"  - name: {domain}")
        lines.append("    files:")
        if domain == "code":
            lines.append("      - $AIRESOURCES/code-conventions/general.md")
            lines.append("      - $AIRESOURCES/code-conventions/python.md")
            lines.append("      - $AIRESOURCES/code-conventions/javascript.md")
            lines.append("      - $AIRESOURCES/code-conventions/cli.md")
            lines.append("      - $AIRESOURCES/code-conventions/stack-commands.md")
        elif domain == "design-tokens":
            lines.append("      - $AIRESOURCES/design/tokens/colors.md")
            lines.append("      - $AIRESOURCES/design/tokens/spacing.md")
            lines.append("      - $AIRESOURCES/design/tokens/typography.md")
            lines.append("      - $AIRESOURCES/design/tokens/motion.md")
            lines.append("      - $AIRESOURCES/design/tokens/cross-platform.md")
        elif domain == "design-components":
            lines.append("      - $AIRESOURCES/design/components/buttons.md")
            lines.append("      - $AIRESOURCES/design/components/forms.md")
            lines.append("      - $AIRESOURCES/design/components/navigation.md")
            lines.append("      - $AIRESOURCES/design/components/lists.md")
            lines.append("      - $AIRESOURCES/design/components/modals.md")
            lines.append("      - $AIRESOURCES/design/components/feedback.md")
        elif domain == "design-views":
            lines.append("      - $AIRESOURCES/design/references/app-views.md")
            lines.append("      - $AIRESOURCES/design/references/app-views-catalog.md")
            lines.append("      - $AIRESOURCES/design/references/app-ui.md")
            lines.append("      - $AIRESOURCES/design/references/mockup-specs.md")
        elif domain == "design-quality":
            lines.append("      - $AIRESOURCES/design/quality/accessibility.md")
            lines.append("      - $AIRESOURCES/design/quality/ui-rules.md")
    return "\n".join(lines) + "\n"


def _is_web_ui_stack(stack_text: str) -> bool:
    web_markers = (
        "web",
        "frontend",
        "react",
        "vite",
        "next",
        "dashboard",
        "browser",
        "typescript",
    )
    return any(marker in stack_text for marker in web_markers)


__all__ = [
    "build_status_report",
    "conventions_app",
    "play_coverage_command",
    "refresh_conventions_command",
    "register",
    "status_command",
]
