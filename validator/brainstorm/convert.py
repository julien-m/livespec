"""Flow.md → Feature spec.md converter.

Strips the brainstorm YAML frontmatter, rewrites the H1, injects the
LiveSpec header (Feature/Branch/Date/Status/Input), and preserves AC/FR/SC
IDs and section bodies verbatim. Also injects the per-feature `## Screens`
section with mockup snapshot paths or the "À designer" placeholder.
"""

from __future__ import annotations

import re
from pathlib import Path

import frontmatter  # type: ignore[import-untyped]

from .schemas import FlowFrontmatter

_H1_FLOW_RE = re.compile(r"^#\s+Flow Spec:\s*(.+)$", re.MULTILINE)
_INPUT_SECTION_RE = re.compile(
    r"^##\s+Input\s*\n(.+?)(?=^##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)
_SCREENS_SECTION_RE = re.compile(
    r"^##\s+Screens\s*\n.*?(?=^##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)


def _extract_input_text(body: str, fm: FlowFrontmatter) -> str:
    """Pull the `## Input` section if present, else fall back to title."""
    m = _INPUT_SECTION_RE.search(body)
    if m:
        return m.group(1).strip()
    return f"{fm.title}".strip()


# @spec FR-004: H1 rewrite + header inject — .specs/features/012-brainstorm-ingestion/spec.md#fr-004
def convert_flow_to_spec(
    flow_path: Path,
    nnn: str,
    slug: str,
    today: str,
) -> str:
    """Convert a flow.md to a LiveSpec feature spec.md string.

    Strips frontmatter, rewrites `# Flow Spec: X` → `# Feature Spec: X`,
    injects the LiveSpec header block, preserves AC/FR/SC IDs verbatim.
    """
    parsed = frontmatter.load(str(flow_path))
    raw_meta: dict[str, object] = dict(parsed.metadata)

    def _as_list(v: object) -> list[object]:
        if isinstance(v, list):
            return list(v)  # type: ignore[arg-type]
        return []

    fm = FlowFrontmatter.model_validate(
        {
            "flow": raw_meta.get("flow", slug),
            "title": raw_meta.get("title", slug),
            "status": raw_meta.get("status", "Draft"),
            "priority": raw_meta.get("priority"),
            "mockups": _as_list(raw_meta.get("mockups")),
            "surfaces": _as_list(raw_meta.get("surfaces")),
            "source": _as_list(raw_meta.get("source")),
            "generated_at": raw_meta.get("generated_at"),
        }
    )
    body = parsed.content

    # H1 rewrite
    new_body, n = _H1_FLOW_RE.subn(r"# Feature Spec: \1", body, count=1)
    if n == 0:
        # No `# Flow Spec: X` found — prepend a fresh H1.
        new_body = f"# Feature Spec: {fm.title}\n\n{body}"

    input_text = _extract_input_text(new_body, fm)

    header = (
        f"- **Feature:** {fm.title}\n"
        f"- **Branch:** `feature/{nnn}-{slug}`\n"
        f"- **Date:** {today}\n"
        f"- **Status:** Draft\n"
        f"- **Input:** {input_text}\n"
        f"- **Feature Number:** {nnn}\n"
        f"\n---\n"
    )

    # Insert header right after the H1 line.
    lines = new_body.split("\n", 1)
    if len(lines) == 2:
        new_body = f"{lines[0]}\n\n{header}\n{lines[1]}"
    else:
        new_body = f"{new_body}\n\n{header}\n"

    return new_body.lstrip("\n")


# @spec FR-006: Screens section injection — .specs/features/012-brainstorm-ingestion/spec.md#fr-006
def inject_screens_section(
    spec_md: str,
    mockup_refs: list[str],
    nnn: str,
    slug: str,
) -> str:
    """Append (or replace) the `## Screens` section in the generated spec.

    Empty `mockup_refs` → "À designer" placeholder per AC-010.
    """
    if not mockup_refs:
        section = "## Screens\n\n> À designer\n"
    else:
        rows = "\n".join(
            f"| {ref} | `design/screens/{nnn}-{slug}/{_ensure_png(ref)}` |"
            for ref in mockup_refs
        )
        section = (
            "## Screens\n\n"
            "| Mockup | Path |\n"
            "|---|---|\n"
            f"{rows}\n"
        )

    if _SCREENS_SECTION_RE.search(spec_md):
        return _SCREENS_SECTION_RE.sub(section, spec_md, count=1)
    if not spec_md.endswith("\n"):
        spec_md += "\n"
    return f"{spec_md}\n{section}"


def _ensure_png(name: str) -> str:
    return name if name.endswith(".png") else f"{name}.png"


# @spec FR-005: Changelog seed — .specs/features/012-brainstorm-ingestion/spec.md#fr-005
def build_changelog(slug: str, today: str) -> str:
    """Initial `changelog.md` body for an ingested feature."""
    return (
        f"# Changelog: {slug}\n\n"
        f"## {today}\n\n"
        f"- Feature created from brainstorm flow `{slug}`.\n"
    )
