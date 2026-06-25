"""Swift candidate rewrite helpers for XCUITest tree inspection."""

from __future__ import annotations

import re
from pathlib import Path

KIND_PATTERN = re.compile(r"^\s*(?P<kind>\w+)[,\s]")
IDENTIFIER_PATTERN = re.compile(r"identifier:\s*'(?P<value>[^']*)'")
LABEL_PATTERN = re.compile(r"label:\s*'(?P<value>[^']*)'")
TAP_PATTERN = re.compile(r"(?P<call>tap(?:FirstAvailable|AnyTab))\(\s*\[(?P<args>[^\]]*)\]")
SNAPSHOT_PATTERN = re.compile(r"snapshot\(\"(?P<name>[^\"]+)\"\)")


def parse_tree_elements(tree_text: str) -> dict[str, list[str]]:
    """Parse XCUIApplication.debugDescription into element inventories."""
    inventory: dict[str, list[str]] = {"tabs": [], "buttons": [], "cells": [], "statictexts": []}
    seen: dict[str, set[str]] = {key: set() for key in inventory}
    tabbar_indent: int | None = None
    for raw_line in tree_text.splitlines():
        tabbar_indent = _process_tree_line(raw_line, inventory, seen, tabbar_indent)
    return inventory


def _process_tree_line(
    raw_line: str,
    inventory: dict[str, list[str]],
    seen: dict[str, set[str]],
    tabbar_indent: int | None,
) -> int | None:
    """Classify one tree line and append its identifier/label values."""
    line = raw_line.rstrip()
    if not line:
        return tabbar_indent
    indent = len(line) - len(line.lstrip())
    kind, ident, label = _classify_line(line)
    tabbar_indent = _next_tabbar_indent(kind, indent, tabbar_indent)
    if kind is None:
        return tabbar_indent
    bucket = _bucket_for_kind(kind, in_tabbar=tabbar_indent is not None)
    if bucket is not None:
        _append_values(bucket, (ident, label), inventory, seen)
    return tabbar_indent


def _classify_line(line: str) -> tuple[str | None, str | None, str | None]:
    """Extract `(kind, identifier, label)` from one debugDescription line."""
    kind_match = KIND_PATTERN.match(line)
    if not kind_match:
        return (None, None, None)
    ident_match = IDENTIFIER_PATTERN.search(line)
    label_match = LABEL_PATTERN.search(line)
    return (
        kind_match.group("kind"),
        ident_match.group("value") if ident_match else None,
        label_match.group("value") if label_match else None,
    )


def _next_tabbar_indent(kind: str | None, indent: int, current: int | None) -> int | None:
    """Update TabBar nesting state for one tree line."""
    if kind == "TabBar":
        return indent
    if current is not None and indent <= current:
        return None
    return current


def _bucket_for_kind(kind: str, *, in_tabbar: bool) -> str | None:
    """Map an XCUIElement kind to its inventory bucket."""
    if kind == "Button" and in_tabbar:
        return "tabs"
    if kind == "Button":
        return "buttons"
    if kind == "Cell":
        return "cells"
    if kind == "StaticText":
        return "statictexts"
    return None


def _append_values(
    bucket: str,
    values: tuple[str | None, str | None],
    inventory: dict[str, list[str]],
    seen: dict[str, set[str]],
) -> None:
    """Append unseen identifier and label values to one inventory bucket."""
    for value in values:
        if value and value not in seen[bucket]:
            seen[bucket].add(value)
            inventory[bucket].append(value)


def rewrite_swift_candidates(swift_path: Path, inventories: dict[str, dict[str, list[str]]]) -> int:
    """Rewrite Swift tap candidate lists from discovered screen inventories."""
    text = swift_path.read_text(encoding="utf-8")
    methods = [_rewrite_method(method, inventories) for method in _split_methods(text)]
    swift_path.write_text("".join(method for method, _updated in methods), encoding="utf-8")
    return sum(1 for _method, updated in methods if updated)


def _split_methods(text: str) -> list[str]:
    """Split a Swift file into method-sized chunks for surgical rewriting."""
    parts: list[str] = []
    pattern = re.compile(r"(\s*func\s+\w+\([^)]*\)\s*throws\s*\{)")
    last = 0
    for match in pattern.finditer(text):
        parts.append(text[last : match.start()])
        last = match.start()
    parts.append(text[last:])
    return parts


def _rewrite_method(
    method_text: str,
    inventories: dict[str, dict[str, list[str]]],
) -> tuple[str, bool]:
    """Rewrite one Swift method when it contains a known snapshot screen."""
    snap = SNAPSHOT_PATTERN.search(method_text)
    if not snap:
        return method_text, False
    inventory = inventories.get(snap.group("name"))
    if not inventory:
        return method_text, False
    return _replace_taps_in_method(method_text, inventory)


def _replace_taps_in_method(method_text: str, inventory: dict[str, list[str]]) -> tuple[str, bool]:
    """Replace tap candidate lists in one method with discovered labels."""
    changed = False

    def replace(match: re.Match[str]) -> str:
        """Render one rewritten tap call and track whether it changed."""
        nonlocal changed
        rendered, did_change = _render_tap_replacement(match, inventory)
        changed = changed or did_change
        return rendered

    return TAP_PATTERN.sub(replace, method_text), changed


def _render_tap_replacement(
    match: re.Match[str],
    inventory: dict[str, list[str]],
) -> tuple[str, bool]:
    """Return replacement text for one tap helper call."""
    call = match.group("call")
    discovered = inventory.get("tabs", []) if call == "tapAnyTab" else _button_candidates(inventory)
    if not discovered:
        return match.group(0), False
    existing = _parse_string_list(match.group("args").strip())
    new_values = [value for value in discovered if value and value not in set(existing)]
    if not new_values:
        return match.group(0), False
    rendered = ", ".join(f'"{value}"' for value in (existing + new_values)[:8])
    return f"{call}([{rendered}]", True


def _button_candidates(inventory: dict[str, list[str]]) -> list[str]:
    """Return button-like candidate labels for tapFirstAvailable."""
    return inventory.get("buttons", []) + inventory.get("statictexts", [])


def _parse_string_list(args: str) -> list[str]:
    """Parse string literals from an existing Swift array argument."""
    return [match.group(1) for match in re.finditer(r'"([^"]*)"', args)]
