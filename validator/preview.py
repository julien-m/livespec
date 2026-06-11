# LiveSpec traceability anchors
# @spec(AC-010)

"""Project-aware preview renderer for ``livespec verify-output --preview``.

# @spec FR-008: render_preview 4 sources + save_preview
#   — .specs/features/039.1-goal-archive-run-artifacts/spec.md#fr-008
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

# PyYAML is a runtime dependency in this repo, but the local environment lacks
# typed stubs, so pyright needs an explicit boundary here.
import yaml  # type: ignore[import-untyped]

from .expectations import ExpectationsFile

NOT_CONFIGURED = "[not configured]"

# Matches the first level-1 Markdown heading; its text is the stack name line.
_H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class ProjectContext:
    """Snapshot of the 4 project sources used for placeholder resolution."""

    stack_name: str | None
    feature_slugs: list[str]
    screen_names: list[str]
    convention_subdomains: list[str]


def build_project_context(project_root: Path) -> ProjectContext:
    """Read the 4 documented preview sources; each is independently optional."""
    return ProjectContext(
        stack_name=_read_stack_name(project_root / ".specs" / "stacks" / "_default.md"),
        feature_slugs=_scan_dir_names(project_root / ".specs" / "features"),
        screen_names=_scan_screen_names(project_root / ".specs" / "design" / "screens"),
        convention_subdomains=_read_convention_subdomains(
            project_root / ".conventions" / "manifest.yaml"
        ),
    )


def render_preview(expectations: ExpectationsFile, project_root: Path) -> str:
    """Render the Section 13 Demo Session with real project values.

    Args:
        expectations: Parsed expectations file (Section 13 guaranteed by the
            parser — missing/empty sub-sections raise before this point).
        project_root: LiveSpec project root (parent of ``.specs/``).

    Returns:
        Markdown preview where ``<feature>``/``<screen>``/``<stack>``
        placeholders carry real values and missing sources are annotated
        ``[not configured]`` (AC-010, EC-009).
    """
    context = build_project_context(project_root)
    lines = [
        f"# Preview — {expectations.command} on {project_root.name}",
        "",
        f"- **Stack:** {context.stack_name or NOT_CONFIGURED}",
        f"- **Features ({len(context.feature_slugs)}):** "
        + (", ".join(context.feature_slugs) or NOT_CONFIGURED),
        f"- **Screens ({len(context.screen_names)}):** "
        + (", ".join(context.screen_names) or NOT_CONFIGURED),
        "- **Convention sub-domains:** "
        + (", ".join(context.convention_subdomains) or NOT_CONFIGURED),
        "",
        "## Demo Session (project-aware)",
        "",
    ]
    demo = expectations.demo_session
    if demo is not None:
        for heading, body in demo.as_mapping().items():
            lines.append(f"### {heading}")
            lines.append("")
            lines.append(_substitute(body, context))
            lines.append("")
    return "\n".join(lines)


def save_preview(markdown: str, command: str, project_root: Path) -> Path:
    """Persist a rendered preview under ``.specs/.previews/``.

    Args:
        markdown: Rendered preview content (written verbatim).
        command: Command name used in the filename.
        project_root: LiveSpec project root.

    Returns:
        Path of the written ``.specs/.previews/<command>-<ISO>.md`` file.
    """
    previews_dir = project_root / ".specs" / ".previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    # Colon-free timestamp keeps the filename portable across filesystems.
    iso_fs = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S")
    path = previews_dir / f"{command}-{iso_fs}.md"
    path.write_text(markdown, encoding="utf-8")
    return path


def _substitute(body: str, context: ProjectContext) -> str:
    """Replace Section 13 placeholders with project values or annotations."""
    # 040 EC-005: <feature> resolves to the LATEST slug (highest NNN prefix).
    feature_value = context.feature_slugs[-1] if context.feature_slugs else NOT_CONFIGURED
    screen_value = ", ".join(context.screen_names) or NOT_CONFIGURED
    stack_value = context.stack_name or NOT_CONFIGURED
    return (
        body.replace("<feature>", feature_value)
        .replace("<screen>", screen_value)
        .replace("<stack>", stack_value)
    )


def _read_stack_name(stack_file: Path) -> str | None:
    """Extract the stack name from the first h1 heading of ``_default.md``."""
    if not stack_file.is_file():
        return None
    match = _H1_RE.search(stack_file.read_text(encoding="utf-8", errors="replace"))
    return match.group(1) if match else None


def _scan_dir_names(features_dir: Path) -> list[str]:
    if not features_dir.is_dir():
        return []
    return sorted(entry.name for entry in features_dir.iterdir() if entry.is_dir())


def _scan_screen_names(screens_dir: Path) -> list[str]:
    if not screens_dir.is_dir():
        return []
    return sorted(entry.name for entry in screens_dir.glob("*.png"))


def _read_convention_subdomains(manifest_file: Path) -> list[str]:
    if not manifest_file.is_file():
        return []
    try:
        raw: object = yaml.safe_load(manifest_file.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        # A malformed manifest is treated as a missing source, not a failure:
        # the preview must stay best-effort across all 4 sources (EC-009).
        return []
    if not isinstance(raw, dict):
        return []
    domains = cast(dict[str, object], raw).get("domains")
    if not isinstance(domains, dict):
        return []
    return sorted(str(key) for key in cast(dict[str, object], domains))


__all__ = [
    "NOT_CONFIGURED",
    "ProjectContext",
    "build_project_context",
    "render_preview",
    "save_preview",
]
