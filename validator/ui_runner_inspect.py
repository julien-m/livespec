"""XCUITest .xcresult inspector — auto-fix accessibility identifier mismatches.

When the LiveSpec Swift template captures a screen, it attaches both the PNG
and an accessibility tree dump (`<screen>.tree.txt`). This module parses those
dumps and exposes utilities to:

  * list interactive elements per screen (`parse_tree_elements`)
  * rewrite Swift `tapFirstAvailable`/`tapAnyTab` candidate lists with the
    labels actually present on screen (`rewrite_swift_candidates`)

The rewrite is conservative: it only edits the candidate string lists and
leaves the test method body untouched, so user-authored navigation logic
(deep-linking, mock launch flags) is preserved.

# @spec FR-009: developer-friendly diagnostics — feature 030
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, cast

# A screen identifier ends with `.tree.txt` in the .xcresult attachment list.
_TREE_SUFFIX = ".tree.txt"


def extract_screen_trees(xcresult_path: Path) -> dict[str, str]:
    """Return `{screen_id: tree_text}` for every snapshot's tree dump.

    Args:
        xcresult_path: Path to a `.xcresult` bundle.

    Returns:
        Mapping from screen identifier to the raw debugDescription string.
        Empty dict if no `<screen>.tree.txt` attachments are found.
    """
    if shutil.which("xcrun") is None:
        return {}

    # First: list all attachment refs via xcresulttool. Xcode 26 deprecated
    # `xcresulttool get` (no subcommand) and requires `--legacy` for the JSON
    # graph dump. We try the legacy form first since it returns the rich
    # ActionTestAttachment shape we already parse below.
    try:
        graph_raw = subprocess.run(
            [
                "xcrun",
                "xcresulttool",
                "get",
                "--legacy",
                "--path",
                str(xcresult_path),
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {}
    if graph_raw.returncode != 0:
        return {}

    try:
        graph = json.loads(graph_raw.stdout)
    except json.JSONDecodeError:
        return {}

    # The top-level graph only contains the ActionsInvocationRecord, which
    # points to test metadata via `testsRef`. We have to fetch the testsRef
    # payload first to discover per-test `summaryRef` ids, and THEN fetch each
    # summary record — that's where ActionTestAttachment entries actually live.
    refs: list[tuple[str, str]] = []
    refs.extend(_collect_attachment_refs(graph))

    tests_refs = _collect_named_refs(graph, "testsRef")
    summary_refs: list[str] = []
    for tref in tests_refs:
        tests_payload = _fetch_subrecord(xcresult_path, tref)
        if tests_payload is None:
            continue
        summary_refs.extend(_collect_summary_refs(tests_payload))

    for sref in summary_refs:
        sub = _fetch_subrecord(xcresult_path, sref)
        if sub is not None:
            refs.extend(_collect_attachment_refs(sub))

    trees: dict[str, str] = {}
    for name, ref_id in refs:
        if not name.endswith(_TREE_SUFFIX):
            continue
        screen = name[: -len(_TREE_SUFFIX)]
        text = _export_attachment_text(xcresult_path, ref_id)
        if text is not None:
            trees[screen] = text
    return trees


def _collect_summary_refs(node: object) -> list[str]:
    """Walk the graph and return every `summaryRef.id._value` it carries."""
    return _collect_named_refs(node, "summaryRef")


def _collect_named_refs(node: object, ref_name: str) -> list[str]:
    """Walk the graph collecting `<ref_name>.id._value` strings.

    Args:
        node: Root of the JSON subtree to search.
        ref_name: Field name to follow (e.g. "summaryRef", "testsRef").

    Returns:
        List of reference id strings, in document order.
    """
    out: list[str] = []

    def visit(obj: object) -> None:
        if isinstance(obj, dict):
            d = cast(dict[str, Any], obj)
            ref = d.get(ref_name)
            if isinstance(ref, dict):
                rid_field = cast(dict[str, Any], ref).get("id")
                if isinstance(rid_field, dict):
                    rv = cast(dict[str, Any], rid_field).get("_value")
                    if isinstance(rv, str):
                        out.append(rv)
            for v in d.values():
                visit(v)
        elif isinstance(obj, list):
            for v in cast(list[Any], obj):
                visit(v)

    visit(node)
    return out


def _fetch_subrecord(xcresult_path: Path, ref_id: str) -> object | None:
    """Fetch a sub-record from the xcresult bundle by its reference id."""
    try:
        result = subprocess.run(
            [
                "xcrun",
                "xcresulttool",
                "get",
                "--legacy",
                "--path",
                str(xcresult_path),
                "--id",
                ref_id,
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def _collect_attachment_refs(node: object) -> list[tuple[str, str]]:
    """Walk the xcresult JSON graph collecting (name, payloadId) tuples.

    Args:
        node: Root of the xcresult JSON tree (or a nested subtree).

    Returns:
        List of `(filename, payloadRefId)` tuples for every attachment.
    """
    out: list[tuple[str, str]] = []

    def visit(obj: object) -> None:
        if isinstance(obj, dict):
            d = cast(dict[str, Any], obj)
            type_field = d.get("_type")
            type_name: str | None = None
            if isinstance(type_field, dict):
                tn = cast(dict[str, Any], type_field).get("_name")
                if isinstance(tn, str):
                    type_name = tn
            if type_name == "ActionTestAttachment":
                # `filename` carries Xcode's auto-generated suffix
                # (e.g. "watch-home.tree_0_<uuid>.txt"). The user-facing
                # identifier we set via `attachment.name` is in the `name`
                # field — that's what matches our `<screen>.tree.txt` convention.
                name_field = d.get("name")
                fname: str | None = None
                if isinstance(name_field, dict):
                    nv = cast(dict[str, Any], name_field).get("_value")
                    if isinstance(nv, str):
                        fname = nv
                payload = d.get("payloadRef")
                if isinstance(payload, dict):
                    rid_field = cast(dict[str, Any], payload).get("id")
                    rid: str | None = None
                    if isinstance(rid_field, dict):
                        rv = cast(dict[str, Any], rid_field).get("_value")
                        if isinstance(rv, str):
                            rid = rv
                    if fname and rid:
                        out.append((fname, rid))
            for value in d.values():
                visit(value)
        elif isinstance(obj, list):
            for item in cast(list[Any], obj):
                visit(item)

    visit(node)
    return out


def _export_attachment_text(xcresult_path: Path, ref_id: str) -> str | None:
    """Export a single text attachment via xcresulttool.

    Args:
        xcresult_path: Path to the `.xcresult` bundle.
        ref_id: Attachment payload reference id.

    Returns:
        Decoded UTF-8 text, or None on failure.
    """
    try:
        result = subprocess.run(
            [
                "xcrun",
                "xcresulttool",
                "get",
                "--legacy",
                "--path",
                str(xcresult_path),
                "--id",
                ref_id,
            ],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    try:
        return result.stdout.decode("utf-8", errors="replace")
    except (UnicodeDecodeError, AttributeError):
        return None


# Each line in `app.debugDescription` looks like:
#     Button, 0x..., {{x, y}, {w, h}}, identifier: 'foo', label: 'Foo'
# Frames contain commas, so we extract identifier/label via independent
# patterns rather than position-based parsing. The kind is the first \w+
# token on the line, ignoring any `0x...` prefix that might appear.
_KIND_PATTERN = re.compile(r"^\s*(?P<kind>\w+)[,\s]")
_IDENTIFIER_PATTERN = re.compile(r"identifier:\s*'(?P<value>[^']*)'")
_LABEL_PATTERN = re.compile(r"label:\s*'(?P<value>[^']*)'")


def parse_tree_elements(tree_text: str) -> dict[str, list[str]]:
    """Parse XCUIApplication.debugDescription into per-kind label/identifier lists.

    Args:
        tree_text: Raw `app.debugDescription` output captured by the Swift snapshot.

    Returns:
        Dict with keys `tabs`, `buttons`, `cells`, `statictexts`. Each maps to
        a list of strings (labels and identifiers, deduplicated, in document
        order). Other element kinds are ignored.
    """
    inv: dict[str, list[str]] = {
        "tabs": [],
        "buttons": [],
        "cells": [],
        "statictexts": [],
    }
    seen: dict[str, set[str]] = {k: set() for k in inv}

    in_tabbar = False
    tabbar_indent = -1

    for raw_line in tree_text.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        indent = len(line) - len(line.lstrip())
        kind, ident, label = _classify_line(line)

        # Track tabbar children: any Button immediately under a TabBar block
        # is mapped into the `tabs` bucket.
        if kind == "TabBar":
            in_tabbar = True
            tabbar_indent = indent
        elif in_tabbar and indent <= tabbar_indent:
            in_tabbar = False
            tabbar_indent = -1

        if kind is None:
            continue

        bucket = _bucket_for_kind(kind, in_tabbar=in_tabbar)
        if bucket is None:
            continue

        for value in (ident, label):
            if value and value not in seen[bucket]:
                seen[bucket].add(value)
                inv[bucket].append(value)

    return inv


def _classify_line(line: str) -> tuple[str | None, str | None, str | None]:
    """Extract (kind, identifier, label) from one debugDescription line.

    Args:
        line: One stripped line of debugDescription output.

    Returns:
        Tuple of (kind, identifier, label). Any field may be None.
    """
    kind_match = _KIND_PATTERN.match(line)
    if not kind_match:
        return (None, None, None)
    ident_match = _IDENTIFIER_PATTERN.search(line)
    label_match = _LABEL_PATTERN.search(line)
    return (
        kind_match.group("kind"),
        ident_match.group("value") if ident_match else None,
        label_match.group("value") if label_match else None,
    )


def _bucket_for_kind(kind: str, *, in_tabbar: bool) -> str | None:
    """Map an XCUIElement kind to its inventory bucket.

    Args:
        kind: Element kind reported in debugDescription (e.g. "Button").
        in_tabbar: True when this element is nested under a TabBar.

    Returns:
        Bucket name or None if the kind is not collected.
    """
    if kind == "Button" and in_tabbar:
        return "tabs"
    if kind == "Button":
        return "buttons"
    if kind == "Cell":
        return "cells"
    if kind == "StaticText":
        return "statictexts"
    return None


# Match a `tapFirstAvailable([...])` or `tapAnyTab([...])` call
# inside a test method whose body contains `snapshot("<screen>")`.
_TAP_PATTERN = re.compile(
    r"(?P<call>tap(?:FirstAvailable|AnyTab))\(\s*\[(?P<args>[^\]]*)\]"
)
_SNAPSHOT_PATTERN = re.compile(r"snapshot\(\"(?P<name>[^\"]+)\"\)")


def rewrite_swift_candidates(
    swift_path: Path, inventories: dict[str, dict[str, list[str]]]
) -> int:
    """Rewrite the candidate lists of `tapFirstAvailable`/`tapAnyTab` calls.

    For each test method that contains `snapshot("<screen>")`, look up the
    discovered tabs/buttons for that screen and update every preceding
    `tapFirstAvailable([...])` / `tapAnyTab([...])` call to use those labels
    as the candidate list.

    Args:
        swift_path: Path to the Swift UI test file.
        inventories: `{screen: {tabs|buttons|cells|statictexts: [labels]}}`.

    Returns:
        Number of test methods whose candidate lists were updated.
    """
    text = swift_path.read_text(encoding="utf-8")
    methods = list(_split_methods(text))
    new_methods: list[str] = []
    changed = 0

    for method_text in methods:
        snap = _SNAPSHOT_PATTERN.search(method_text)
        if not snap:
            new_methods.append(method_text)
            continue
        screen = snap.group("name")
        inv = inventories.get(screen)
        if not inv:
            new_methods.append(method_text)
            continue

        rewritten, updated = _replace_taps_in_method(method_text, inv)
        if updated:
            changed += 1
        new_methods.append(rewritten)

    swift_path.write_text("".join(new_methods), encoding="utf-8")
    return changed


def _split_methods(text: str) -> list[str]:
    """Split a Swift file into method-sized chunks for surgical rewriting.

    The split keeps method boundaries intact so we can rewrite one method at
    a time without disturbing surrounding code.

    Args:
        text: Full Swift file contents.

    Returns:
        List of method-or-prelude chunks. Concatenating them re-yields `text`.
    """
    parts: list[str] = []
    pattern = re.compile(r"(\s*func\s+\w+\([^)]*\)\s*throws\s*\{)")
    last = 0
    for m in pattern.finditer(text):
        parts.append(text[last : m.start()])
        last = m.start()
    parts.append(text[last:])
    return parts


def _replace_taps_in_method(
    method_text: str, inv: dict[str, list[str]]
) -> tuple[str, bool]:
    """Replace tap candidate lists in one method with the discovered labels.

    `tapAnyTab(...)` is updated with `tabs`. `tapFirstAvailable(...)` prefers
    `buttons` but falls back to `statictexts` when the first call returns no
    button hits. We keep the existing user-provided candidates and just merge
    discovered ones at the front (so the test still works if the user later
    adds explicit accessibilityIdentifier values).

    Args:
        method_text: One method chunk produced by `_split_methods`.
        inv: Inventory for this screen.

    Returns:
        Tuple of (new method text, was-changed).
    """
    changed = False

    def repl(match: re.Match[str]) -> str:
        nonlocal changed
        call = match.group("call")
        original_args = match.group("args").strip()
        if call == "tapAnyTab":
            discovered = inv.get("tabs", [])
        else:
            discovered = inv.get("buttons", []) + inv.get("statictexts", [])
        if not discovered:
            return match.group(0)
        existing = _parse_string_list(original_args)
        # Only flag "changed" when discovery brings NEW labels. Preserve the
        # user's original ordering so any intentional priority is kept; append
        # discovered-but-missing labels at the end.
        existing_set = set(existing)
        new_values = [v for v in discovered if v and v not in existing_set]
        if not new_values:
            return match.group(0)
        merged = existing + new_values
        changed = True
        rendered = ", ".join(f'"{v}"' for v in merged[:8])
        return f"{call}([{rendered}]"

    new_text = _TAP_PATTERN.sub(repl, method_text)
    return new_text, changed


def _parse_string_list(args: str) -> list[str]:
    """Parse `"a", "b", "c"` from an existing call's argument string.

    Args:
        args: Inner contents of the array literal (without brackets).

    Returns:
        List of decoded string literals.
    """
    return [m.group(1) for m in re.finditer(r'"([^"]*)"', args)]


__all__ = [
    "extract_screen_trees",
    "parse_tree_elements",
    "rewrite_swift_candidates",
]
