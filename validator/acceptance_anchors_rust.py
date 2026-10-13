"""Rust targets of `@spec AC-xxx` anchors and their Cargo test paths (feature 087)."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from .execution_rust_source import rust_assertions, rust_functions

if TYPE_CHECKING:
    from .acceptance_anchors import AnchorIssue, _Anchor  # pyright: ignore[reportPrivateUsage]


def _rust_is_test(lines: list[str], header: int) -> bool:
    """A `#[...test]` attribute among the attribute/comment lines above a function."""
    index = header - 2
    while index >= 0 and lines[index].lstrip().startswith(("#[", "//")):
        line = lines[index].lstrip()
        if line.startswith("#[") and re.match(r"#\[[\w:]*test\b", line):
            return True
        index -= 1
    return False


def rust_target(anchor: _Anchor, text: str) -> tuple[str, int, int] | AnchorIssue | None:
    """Bind an anchor to a `#[test]` function's last assertion or to one assertion in it."""
    from .acceptance_anchors import AnchorIssue

    where = f"{anchor.path}:{anchor.line}"
    lines = text.splitlines()
    target = anchor.target
    while 0 < target <= len(lines) and lines[target - 1].lstrip().startswith("#["):
        target += 1
    assertions = rust_assertions(text)
    integration = "tests" in PurePosixPath(anchor.path).parts[:-1]
    for function in rust_functions(text):
        if not (function.line == target or function.line < anchor.line <= function.end_line):
            continue
        if not _rust_is_test(lines, function.line):
            return None  # An anchor on production code: not a test binding.
        test_id = "::".join([*_rust_module(anchor.path), *function.modules, function.name])
        owned = [
            item
            for item in assertions
            if item.function == function.name and function.line <= item.line <= function.end_line
        ]
        if function.line == target:
            if not owned:
                return AnchorIssue("anchor_test_without_assert", f"{where} {function.name}")
            return test_id, owned[-1].line, owned[-1].end_line
        for item in owned:
            if item.line == anchor.target:
                return test_id, item.line, item.end_line
        return AnchorIssue("anchor_target_unresolved", f"{where} precedes no assertion")
    if integration:
        return AnchorIssue("anchor_target_unresolved", f"{where} precedes no test or assertion")
    return None


def _rust_module(path: str) -> list[str]:
    """Module path of a crate source file; integration test files are crate roots."""
    parts = list(PurePosixPath(path).with_suffix("").parts)
    for root_dir in ("src", "tests"):
        if root_dir in parts:
            index = len(parts) - 1 - parts[::-1].index(root_dir)
            module = parts[index + 1 :]
            if root_dir == "tests":
                return []
            if module in (["lib"], ["main"]):
                return []
            return module[:-1] if module and module[-1] == "mod" else module
    return parts[-1:]
