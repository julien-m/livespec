"""Public facade for XCUITest .xcresult inspection helpers."""

from __future__ import annotations

from validator.runner_inspect_impl import (
    extract_screen_trees,
    parse_tree_elements,
    rewrite_swift_candidates,
)

__all__ = [
    "extract_screen_trees",
    "parse_tree_elements",
    "rewrite_swift_candidates",
]
