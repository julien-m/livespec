"""Project-aware preview renderer for ``livespec verify-output --preview``.

# @spec FR-005: --preview CLI mode
#   — .specs/features/040-expectations-rich-and-verify-preview/spec.md#fr-005
# @spec FR-006: render_preview implementation
#   — .specs/features/040-expectations-rich-and-verify-preview/spec.md#fr-006
# @spec FR-007: placeholder resolver
#   — .specs/features/040-expectations-rich-and-verify-preview/spec.md#fr-007
# @spec AC-006: 4 project sources
#   — .specs/features/040-expectations-rich-and-verify-preview/spec.md#ac-006
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]

from .expectations import ExpectationsFile

# Canonical error substrings (must match spec.md AC-008/009/010 verbatim).
ERR_NO_SPECS_DIR = "preview requires a LiveSpec project (no .specs/ found)"


def _empty_str_list() -> list[str]:
    """Typed default factory for ``list[str]`` dataclass fields."""
    return []


@dataclass(frozen=True)
class ProjectContext:
    """Snapshot of project data used for placeholder substitution."""

    stack_name: str | None = None
    feature_slugs: list[str] = field(default_factory=_empty_str_list)
    screen_names: list[str] = field(default_factory=_empty_str_list)
    convention_subdomains: list[str] = field(default_factory=_empty_str_list)
    notes: list[str] = field(default_factory=_empty_str_list)

    @property
    def latest_feature(self) -> str | None:
        if not self.feature_slugs:
            return None
        return sorted(self.feature_slugs)[-1]


@dataclass(frozen=True)
class PreviewReport:
    """Rendered project-aware preview."""

    command: str
    project_root: Path
    timestamp: str  # ISO 8601 UTC
    markdown: str
    context: ProjectContext


# ---------- Project context builder ----------


def build_project_context(project_root: Path) -> ProjectContext:
    """Read up to four project-level data sources to build a context.

    All sources are independently optional. Missing or malformed sources
    contribute a note rather than raising.
    """
    specs_root = project_root / ".specs"
    stack_name = _read_stack_name(specs_root)
    feature_slugs = _read_feature_slugs(specs_root)
    screen_names = _read_screen_names(specs_root)
    convention_subdomains, conv_notes = _read_convention_subdomains(project_root)

    notes: list[str] = []
    if stack_name is None:
        notes.append("[stack: not configured]")
    if not feature_slugs:
        notes.append("[features: not configured]")
    if not screen_names:
        notes.append("[screens: not configured]")
    notes.extend(conv_notes)

    return ProjectContext(
        stack_name=stack_name,
        feature_slugs=feature_slugs,
        screen_names=screen_names,
        convention_subdomains=convention_subdomains,
        notes=notes,
    )


def _read_stack_name(specs_root: Path) -> str | None:
    """Extract the stack identifier from .specs/stacks/_default.md."""
    path = specs_root / "stacks" / "_default.md"
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
        if stripped.startswith("**Stack:**") or stripped.startswith("Stack:"):
            return stripped.split(":", 1)[1].strip().strip("*").strip()
    # Fall back to first non-empty content line.
    for line in text.splitlines():
        if line.strip() and not line.strip().startswith("#"):
            return line.strip()[:80]
    return None


def _read_feature_slugs(specs_root: Path) -> list[str]:
    features_dir = specs_root / "features"
    if not features_dir.is_dir():
        return []
    slugs: list[str] = []
    for entry in features_dir.iterdir():
        if entry.is_dir() and re.match(r"^\d{3}-", entry.name):
            slugs.append(entry.name)
    return sorted(slugs)


def _read_screen_names(specs_root: Path) -> list[str]:
    screens_dir = specs_root / "design" / "screens"
    if not screens_dir.is_dir():
        return []
    names: list[str] = []
    for entry in screens_dir.iterdir():
        if entry.is_file() and entry.suffix.lower() == ".png":
            names.append(entry.stem)
    return sorted(names)


def _read_convention_subdomains(project_root: Path) -> tuple[list[str], list[str]]:
    path = project_root / ".conventions" / "manifest.yaml"
    if not path.exists():
        return [], []
    try:
        text = path.read_text(encoding="utf-8")
        raw_any: Any = yaml.safe_load(text)
    except (OSError, yaml.YAMLError):
        return [], ["[conventions: malformed manifest]"]
    if not isinstance(raw_any, dict):
        return [], ["[conventions: malformed manifest]"]
    raw_dict = cast(dict[Any, Any], raw_any)
    subdomains_raw: Any = raw_dict.get("subdomains") or raw_dict.get("domains") or []
    subdomains: list[str] = []
    if isinstance(subdomains_raw, list):
        entries = cast(list[Any], subdomains_raw)
        for entry in entries:
            if isinstance(entry, dict):
                entry_dict = cast(dict[Any, Any], entry)
                if "name" in entry_dict:
                    subdomains.append(str(entry_dict["name"]))
            elif isinstance(entry, str):
                subdomains.append(entry)
    elif isinstance(subdomains_raw, dict):
        keys = cast(dict[Any, Any], subdomains_raw)
        subdomains.extend(str(k) for k in keys)
    return subdomains, []


# ---------- Placeholder substitution ----------


_PLACEHOLDER_RE = re.compile(r"<(feature|screen|stack|path)>")


def resolve_placeholders(markdown: str, ctx: ProjectContext) -> str:
    """Substitute placeholders in a Markdown string using project context.

    Substitutions:
      - ``<feature>`` -> latest feature slug or ``[no features configured]``
      - ``<screen>`` -> first screen name or ``[no screens configured]``
      - ``<stack>``  -> stack name or ``[no stack configured]``
      - ``<path>``   -> passthrough (no substitution).
    """

    def repl(match: re.Match[str]) -> str:
        token = match.group(1)
        if token == "feature":
            return ctx.latest_feature or "[no features configured]"
        if token == "screen":
            return ctx.screen_names[0] if ctx.screen_names else "[no screens configured]"
        if token == "stack":
            return ctx.stack_name or "[no stack configured]"
        # path: passthrough
        return match.group(0)

    return _PLACEHOLDER_RE.sub(repl, markdown)


# ---------- Preview rendering ----------


def render_preview(
    expectations: ExpectationsFile,
    project_root: Path,
    *,
    now: datetime | None = None,
) -> PreviewReport:
    """Render a project-aware preview Markdown report.

    The Markdown mirrors Section 13 (Demo Session) of the expectations file,
    with placeholders substituted from a freshly-built :class:`ProjectContext`.
    """
    if expectations.demo_session is None:
        raise ValueError(
            f"expectations file has no demo session: {expectations.source_path}"
        )
    ctx = build_project_context(project_root)
    timestamp = (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H-%M-%SZ")
    markdown = _render_markdown(expectations, ctx, timestamp)
    return PreviewReport(
        command=expectations.command,
        project_root=project_root,
        timestamp=timestamp,
        markdown=markdown,
        context=ctx,
    )


def _render_markdown(
    expectations: ExpectationsFile,
    ctx: ProjectContext,
    timestamp: str,
) -> str:
    """Build the full Markdown body of the preview."""
    demo = expectations.demo_session
    assert demo is not None  # narrowed by render_preview pre-condition

    sub_blocks: list[str] = []
    for canonical, body in demo.as_mapping().items():
        rendered_body = resolve_placeholders(body, ctx)
        sub_blocks.append(f"### {canonical}\n\n{rendered_body}".rstrip())

    notes_block = ""
    if ctx.notes:
        notes_block = "\n\n> **Context notes:** " + "; ".join(ctx.notes)

    header = (
        f"# Preview — /{expectations.command}\n\n"
        f"- **Command:** `{expectations.command}`\n"
        f"- **Project root:** `{ctx_project_summary(ctx)}`\n"
        f"- **Generated:** {timestamp}\n"
        f"- **Source:** `{expectations.source_path.as_posix()}`\n"
        f"- **Stack:** {ctx.stack_name or '[no stack configured]'}\n"
        f"- **Feature count:** {len(ctx.feature_slugs)}"
        + (f" (latest: `{ctx.latest_feature}`)" if ctx.latest_feature else "")
        + "\n"
        f"- **Screens detected:** {len(ctx.screen_names)}\n"
        f"- **Convention sub-domains:** {len(ctx.convention_subdomains)}\n"
        f"{notes_block}\n\n"
    )

    body = "\n\n".join(sub_blocks)
    return header + body + "\n"


def ctx_project_summary(ctx: ProjectContext) -> str:
    """Render a short label for the project context (used in header)."""
    parts: list[str] = []
    if ctx.stack_name:
        parts.append(ctx.stack_name)
    if ctx.feature_slugs:
        parts.append(f"{len(ctx.feature_slugs)} features")
    if ctx.screen_names:
        parts.append(f"{len(ctx.screen_names)} screens")
    if ctx.convention_subdomains:
        parts.append(f"{len(ctx.convention_subdomains)} conv-subdomains")
    if not parts:
        return "[minimal context]"
    return " · ".join(parts)


__all__ = [
    "ERR_NO_SPECS_DIR",
    "PreviewReport",
    "ProjectContext",
    "build_project_context",
    "render_preview",
    "resolve_placeholders",
]
