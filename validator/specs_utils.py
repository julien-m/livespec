"""Shared utility for finding the .specs/ root directory."""

from __future__ import annotations

from pathlib import Path

from .exceptions import SpecsRootNotFoundError


def find_specs_root(start: Path | None = None) -> Path:
    """Find the .specs/ directory starting from the given path or cwd.

    Args:
        start: Starting path to search from, or None for cwd.

    Returns:
        Path to the .specs/ directory.

    Raises:
        SpecsRootNotFoundError: If .specs/ cannot be found.
    """
    search = start or Path.cwd()
    if search.is_file():
        search = search.parent
    for parent in [search, *search.parents]:
        if parent.name == ".specs":
            return parent
        specs_dir = parent / ".specs"
        if specs_dir.is_dir():
            return specs_dir
    raise SpecsRootNotFoundError(str(search))
