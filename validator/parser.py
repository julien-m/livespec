"""Parse Markdown files: frontmatter + AST extraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import frontmatter
import mistune


@dataclass
class ParsedFile:
    """Result of parsing a Markdown file."""

    metadata: dict
    content: str
    headings: list[str] = field(default_factory=list)
    code_blocks: list[dict] = field(default_factory=list)


def _extract_headings_and_blocks(ast_nodes: list[dict]) -> tuple[list[str], list[dict]]:
    """Walk the AST and extract H2/H3 headings and fenced code blocks."""
    headings: list[str] = []
    code_blocks: list[dict] = []

    for node in ast_nodes:
        node_type = node.get("type", "")

        if node_type == "heading":
            level = node.get("attrs", {}).get("level", 0)
            if level in (2, 3):
                text = _extract_text(node.get("children", []))
                headings.append(text.strip())

        elif node_type == "block_code":
            info = node.get("attrs", {}).get("info", "") or ""
            raw = node.get("raw", "") or ""
            # Also check children for raw text
            if not raw:
                raw = _extract_text(node.get("children", []))
            code_blocks.append({"lang": info.strip(), "code": raw})

        # Recurse into children
        children = node.get("children")
        if children and isinstance(children, list):
            sub_headings, sub_blocks = _extract_headings_and_blocks(children)
            headings.extend(sub_headings)
            code_blocks.extend(sub_blocks)

    return headings, code_blocks


def _extract_text(children: list[dict]) -> str:
    """Extract raw text from AST children nodes."""
    parts: list[str] = []
    for child in children:
        if "raw" in child:
            parts.append(child["raw"])
        elif "children" in child and isinstance(child["children"], list):
            parts.append(_extract_text(child["children"]))
        elif "text" in child:
            parts.append(child["text"])
    return "".join(parts)


def parse_file(path: Path) -> ParsedFile:
    """Parse a Markdown file into metadata, content, headings, and code blocks.

    Uses python-frontmatter for YAML frontmatter and mistune 3.x for AST.
    """
    post = frontmatter.load(str(path))
    metadata = dict(post.metadata)
    content = post.content

    # Parse Markdown AST with mistune 3.x
    md = mistune.create_markdown(renderer="ast")
    ast_nodes = md(content)

    headings, code_blocks = _extract_headings_and_blocks(ast_nodes)

    return ParsedFile(
        metadata=metadata,
        content=content,
        headings=headings,
        code_blocks=code_blocks,
    )
