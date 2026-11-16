"""Identify actual feature requirement definitions for journey coverage checks."""

from __future__ import annotations

import re
from typing import cast

import mistune

Node = dict[str, object]
_IDENTIFIER = re.compile(r"(?:AC|FR)-[0-9]+")
_DECLARATION = re.compile(r"^((?:AC|FR)-[0-9]+)\s*:\s*(.*)$", re.DOTALL)
_REQUIREMENT_HEADING = re.compile(r"^((?:AC|FR)-[0-9]+)(?:\s|:|$)")
_FRONTMATTER = re.compile(
    r"\A\ufeff?---[ \t]*\r?\n.*?\r?\n(?:---|\.\.\.)[ \t]*(?:\r?\n|\Z)", re.DOTALL
)
_EMPTY_ANCHOR = re.compile(r"<a\s+(?:id|name)\s*=\s*(?:\"[^\"]*\"|'[^']*')\s*>", re.I)
_EXCLUDED_SECTION = re.compile(
    r"^(?:references?|examples?|testing|tests?|evidence|"
    r"(?:implementation )?mappings?|traceability|coverage)\b"
)
_SECTIONS = {
    "acceptance criteria": frozenset({"AC"}),
    "functional requirements": frozenset({"FR"}),
    "acceptance criteria and requirements": frozenset({"AC", "FR"}),
}
# A forbidden inline node must not disappear and expose a later identifier as a declaration.
_OPAQUE = "\ufffc"


def _nodes(value: object) -> list[Node]:
    """Narrow the Markdown parser's external token collections."""
    if not isinstance(value, list):
        return []
    return [cast(Node, item) for item in cast(list[object], value) if isinstance(item, dict)]


def _inline_text(node: Node) -> str:
    """Keep literal text/emphasis and empty ID anchors, never links or inline code."""
    if node.get("type") == "text":
        raw = node.get("raw")
        return raw if isinstance(raw, str) else ""
    if node.get("type") in {"softbreak", "linebreak"}:
        return "\n"
    if node.get("type") not in {
        "strong",
        "emphasis",
        "heading",
        "paragraph",
        "block_text",
        "table_cell",
    }:
        return _OPAQUE
    children = _nodes(node.get("children"))
    parts: list[str] = []
    index = 0
    while index < len(children):
        child = children[index]
        raw = child.get("raw")
        if (
            child.get("type") == "inline_html"
            and isinstance(raw, str)
            and _EMPTY_ANCHOR.fullmatch(raw)
            and index + 1 < len(children)
            and children[index + 1].get("type") == "inline_html"
            and str(children[index + 1].get("raw", "")).casefold() == "</a>"
        ):
            index += 2
            continue
        parts.append(_inline_text(child))
        index += 1
    return "".join(parts)


def _has_description(text: str) -> bool:
    """Require visible definition content rather than an anchor or an incidental link."""
    return bool(text.replace(_OPAQUE, "").strip())


def _scope(stack: list[tuple[int, str]]) -> frozenset[str]:
    """Resolve the nearest canonical section while honoring excluded ancestors."""
    if any(_EXCLUDED_SECTION.match(title) for _, title in stack):
        return frozenset()
    for _, title in reversed(stack):
        if title in _SECTIONS:
            return _SECTIONS[title]
    return frozenset({"AC", "FR"})


def _is_requirement_section(stack: list[tuple[int, str]]) -> bool:
    return any(title in _SECTIONS for _, title in stack)


def _declarations(node: Node, allowed: frozenset[str], *, explicit: bool) -> set[str]:
    """Read declaration blocks, not nested code, blockquotes or arbitrary mentions."""
    kind = node.get("type")
    if kind == "list":
        return {
            identifier
            for item in _nodes(node.get("children"))
            for block in _nodes(item.get("children"))
            for identifier in _declarations(block, allowed, explicit=True)
        }
    if kind not in {"paragraph", "block_text"}:
        return set()
    # Consecutive source lines can share one Markdown paragraph. Split only at
    # actual AST breaks so link/code contents cannot manufacture declarations.
    lines: list[list[Node]] = [[]]
    for child in _nodes(node.get("children")):
        if child.get("type") in {"softbreak", "linebreak"}:
            lines.append([])
        else:
            lines[-1].append(child)
    identifiers: set[str] = set()
    current: str | None = None
    description: list[str] = []
    for children in lines:
        text = _inline_text({"type": "paragraph", "children": children}).strip()
        match = _DECLARATION.fullmatch(text)
        if match:
            if current is not None and _has_description("\n".join(description)):
                identifiers.add(current)
            has_bold_prefix = any(child.get("type") == "strong" for child in children[:3])
            current = (
                match[1]
                if (explicit or has_bold_prefix) and match[1].split("-")[0] in allowed
                else None
            )
            description = [match[2]]
        elif current is not None:
            description.append(text)
    if current is not None and _has_description("\n".join(description)):
        identifiers.add(current)
    return identifiers


def _table_definitions(node: Node, allowed: frozenset[str]) -> set[str]:
    """Only the first cell of a body row can declare a table requirement."""
    identifiers: set[str] = set()
    for body in _nodes(node.get("children")):
        if body.get("type") != "table_body":
            continue
        for row in _nodes(body.get("children")):
            cells = _nodes(row.get("children"))
            if len(cells) < 2:
                continue
            identifier = _inline_text(cells[0]).strip()
            if (
                _IDENTIFIER.fullmatch(identifier)
                and identifier.split("-")[0] in allowed
                and _has_description(_inline_text(cells[1]))
            ):
                identifiers.add(identifier)
    return identifiers


def _has_body(node: Node) -> bool:
    """Count prose/list content as a heading body; examples and anchors cannot supply it."""
    if node.get("type") in {"paragraph", "block_text"}:
        return _has_description(_inline_text(node))
    if node.get("type") in {"list", "list_item"}:
        return any(_has_body(child) for child in _nodes(node.get("children")))
    return False


# @spec AC-002: Coverage resolves definitions in supported Markdown formats
# — .specs/features/123-existing-test-journeys/spec.md#ac-002
def defined_requirement_ids(text: str) -> set[str]:
    """Return actual AC/FR definitions, excluding reference-only Markdown content.

    Canonical sections support tables, declarations and requirement headings with
    a visible body. Explicit legacy bold/list declarations also work outside those
    sections. References, examples, testing/evidence scopes and opaque Markdown
    nodes never introduce requirement IDs.
    """
    markdown = _FRONTMATTER.sub("", text, count=1)
    ast = mistune.create_markdown(renderer="ast", plugins=["table"])(markdown)
    stack: list[tuple[int, str]] = []
    pending: tuple[str, int] | None = None
    identifiers: set[str] = set()
    for node in _nodes(ast):
        if node.get("type") == "heading":
            attrs = node.get("attrs")
            level = cast(Node, attrs).get("level") if isinstance(attrs, dict) else None
            if not isinstance(level, int):
                continue
            while stack and stack[-1][0] >= level:
                stack.pop()
            if pending is not None and level <= pending[1]:
                pending = None
            title = _inline_text(node).strip()
            allowed = _scope(stack)
            match = _REQUIREMENT_HEADING.match(title)
            if match and match[1].split("-")[0] in allowed:
                pending = (match[1], level)
            stack.append((level, " ".join(title.casefold().split())))
            continue
        allowed = _scope(stack)
        if not allowed:
            continue
        if pending is not None and _has_body(node):
            identifiers.add(pending[0])
            pending = None
        if node.get("type") == "table" and _is_requirement_section(stack):
            identifiers.update(_table_definitions(node, allowed))
        else:
            identifiers.update(
                _declarations(node, allowed, explicit=_is_requirement_section(stack))
            )
    return identifiers
