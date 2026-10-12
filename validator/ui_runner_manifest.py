# LiveSpec traceability anchors
# @spec(FR-001)
# @spec(AC-002)

"""Evaluate the `detect:` block of a built-in UI runner manifest."""

# @spec FR-001: Runner manifest drives project detection
# — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-001
# @spec AC-002: detect.files markers (OR logic) select the iOS runner
# — .specs/features/030-ui-runner-ios-watchos/spec.md#ac-002
# @spec AC-002: web.yaml detect (package.json AND playwright config) drives the web runner
# — .specs/features/028-ui-runner-web/spec.md#ac-002

from __future__ import annotations

import re
from collections.abc import Mapping
from fnmatch import fnmatchcase
from pathlib import Path


def _string_list(value: object, key: str) -> list[str]:
    """Return a list of strings or reject a malformed manifest entry."""
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"UI runner manifest detect.{key} must be a list of strings")
    return list(value)


_BRACE_RE = re.compile(r"\{([^{}]*)\}")


def _expand_braces(pattern: str) -> list[str]:
    """Expand ``a.{ts,js}`` into ``a.ts`` and ``a.js`` (nested groups expand recursively)."""
    match = _BRACE_RE.search(pattern)
    if match is None:
        return [pattern]
    head, tail = pattern[: match.start()], pattern[match.end() :]
    return [
        expanded
        for option in match.group(1).split(",")
        for expanded in _expand_braces(head + option + tail)
    ]


def manifest_detects(project_dir: Path, detect: Mapping[str, object]) -> bool:
    """Return whether a project matches a manifest ``detect`` block.

    ``files`` entries are top-level names or ``fnmatch`` globs (``*.xcodeproj``,
    ``playwright*.config.{ts,js}`` with brace alternatives);
    ``dirs`` entries are project-relative paths. ``logic`` is ``OR`` (default)
    or ``AND`` across every declared marker.

    Args:
        project_dir: Project root inspected without traversing subdirectories.
        detect: Parsed ``detect`` mapping from the runner manifest.

    Returns:
        True when the markers satisfy the declared logic.

    Raises:
        ValueError: The detect block declares no markers or an unknown logic.
    """
    files = _string_list(detect.get("files"), "files")
    dirs = _string_list(detect.get("dirs"), "dirs")
    logic = str(detect.get("logic", "OR")).upper()
    if logic not in {"OR", "AND"}:
        raise ValueError(f"UI runner manifest detect.logic must be OR or AND, got {logic!r}")
    if not files and not dirs:
        raise ValueError("UI runner manifest detect block declares no markers")
    if not project_dir.is_dir():
        return False
    names = [entry.name for entry in project_dir.iterdir()]
    results = [
        any(fnmatchcase(name, option) for name in names for option in _expand_braces(pattern))
        for pattern in files
    ]
    results.extend((project_dir / rel).exists() for rel in dirs)
    return all(results) if logic == "AND" else any(results)


__all__ = ["manifest_detects"]
