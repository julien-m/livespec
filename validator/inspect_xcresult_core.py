"""XCUITest xcresult tree extraction helpers."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, cast

TREE_SUFFIX = ".tree.txt"


def extract_screen_trees(xcresult_path: Path) -> dict[str, str]:
    """Return raw accessibility trees keyed by screen identifier."""
    if shutil.which("xcrun") is None:
        return {}
    graph = _load_xcresult_graph(xcresult_path)
    if graph is None:
        return {}
    refs = _all_attachment_refs(xcresult_path, graph)
    return _export_tree_refs(xcresult_path, refs)


def _load_xcresult_graph(xcresult_path: Path) -> object | None:
    """Load the top-level legacy xcresult JSON graph."""
    try:
        result = subprocess.run(
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
        return None
    if result.returncode != 0:
        return None
    return _parse_json(result.stdout)


def _parse_json(text: str) -> object | None:
    """Parse JSON text, returning None for malformed payloads."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _all_attachment_refs(xcresult_path: Path, graph: object) -> list[tuple[str, str]]:
    """Collect direct and summary attachment refs from an xcresult graph."""
    refs = _collect_attachment_refs(graph)
    summary_refs: list[str] = []
    for tests_ref in _collect_named_refs(graph, "testsRef"):
        payload = _fetch_subrecord(xcresult_path, tests_ref)
        if payload is not None:
            summary_refs.extend(_collect_named_refs(payload, "summaryRef"))
    for summary_ref in summary_refs:
        payload = _fetch_subrecord(xcresult_path, summary_ref)
        if payload is not None:
            refs.extend(_collect_attachment_refs(payload))
    return refs


def _collect_named_refs(node: object, ref_name: str) -> list[str]:
    """Walk a JSON graph collecting `<ref_name>.id._value` strings."""
    out: list[str] = []
    _visit_named_refs(node, ref_name, out)
    return out


def _visit_named_refs(node: object, ref_name: str, out: list[str]) -> None:
    """Recursive worker for named reference collection."""
    if isinstance(node, dict):
        node_dict = cast(dict[str, Any], node)
        _append_named_ref(node_dict, ref_name, out)
        for value in node_dict.values():
            _visit_named_refs(value, ref_name, out)
    elif isinstance(node, list):
        for item in cast(list[Any], node):
            _visit_named_refs(item, ref_name, out)


def _append_named_ref(node: dict[str, Any], ref_name: str, out: list[str]) -> None:
    """Append one named ref from a mapping when present."""
    ref = node.get(ref_name)
    if not isinstance(ref, dict):
        return
    rid_field = cast(dict[str, Any], ref).get("id")
    if isinstance(rid_field, dict):
        value = cast(dict[str, Any], rid_field).get("_value")
        if isinstance(value, str):
            out.append(value)


def _fetch_subrecord(xcresult_path: Path, ref_id: str) -> object | None:
    """Fetch one xcresult sub-record by reference id."""
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
    return _parse_json(result.stdout)


def _collect_attachment_refs(node: object) -> list[tuple[str, str]]:
    """Walk an xcresult JSON graph collecting `(name, payloadRefId)` tuples."""
    out: list[tuple[str, str]] = []
    _visit_attachment_refs(node, out)
    return out


def _visit_attachment_refs(node: object, out: list[tuple[str, str]]) -> None:
    """Recursive worker for attachment reference collection."""
    if isinstance(node, dict):
        node_dict = cast(dict[str, Any], node)
        _append_attachment_ref(node_dict, out)
        for value in node_dict.values():
            _visit_attachment_refs(value, out)
    elif isinstance(node, list):
        for item in cast(list[Any], node):
            _visit_attachment_refs(item, out)


def _append_attachment_ref(node: dict[str, Any], out: list[tuple[str, str]]) -> None:
    """Append one ActionTestAttachment ref when the mapping carries one."""
    type_field = node.get("_type")
    if not (isinstance(type_field, dict) and type_field.get("_name") == "ActionTestAttachment"):
        return
    filename = _string_value(node.get("name"))
    payload = node.get("payloadRef")
    ref_id = _string_value(payload.get("id") if isinstance(payload, dict) else None)
    if filename and ref_id:
        out.append((filename, ref_id))


def _string_value(field: object) -> str | None:
    """Return a `_value` string from an xcresult field mapping."""
    if isinstance(field, dict):
        value = cast(dict[str, Any], field).get("_value")
        if isinstance(value, str):
            return value
    return None


def _export_tree_refs(xcresult_path: Path, refs: list[tuple[str, str]]) -> dict[str, str]:
    """Export tree attachment refs into a `{screen: text}` mapping."""
    trees: dict[str, str] = {}
    for name, ref_id in refs:
        if not name.endswith(TREE_SUFFIX):
            continue
        text = _export_attachment_text(xcresult_path, ref_id)
        if text is not None:
            trees[name[: -len(TREE_SUFFIX)]] = text
    return trees


def _export_attachment_text(xcresult_path: Path, ref_id: str) -> str | None:
    """Export and decode one text attachment by payload ref id."""
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
    return result.stdout.decode("utf-8", errors="replace")
