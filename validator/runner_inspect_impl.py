"""XCUITest .xcresult inspector public helpers."""

from __future__ import annotations

from pathlib import Path

from validator.inspect_swift_core import (
    parse_tree_elements,
)
from validator.inspect_swift_core import (
    rewrite_swift_candidates as _rewrite_swift_candidates,
)
from validator.inspect_xcresult_core import extract_screen_trees


def rewrite_swift_candidates(swift_path: Path, inventories: dict[str, dict[str, list[str]]]) -> int:
    """Rewrite Swift tap candidate lists from discovered screen inventories."""
    return _rewrite_swift_candidates(swift_path, inventories)


__all__ = [
    "extract_screen_trees",
    "parse_tree_elements",
    "rewrite_swift_candidates",
]
