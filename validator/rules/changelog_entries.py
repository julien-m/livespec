"""Validate changelog entry format."""

from __future__ import annotations

import re

ENTRY_PATTERN = re.compile(r"^## \d{4}-\d{2}-\d{2} — \[.+\]:", re.MULTILINE)


def validate_changelog_entries(content: str) -> list[str]:
    """Return errors if no valid changelog entry is found.

    Args:
        content: Raw markdown content of the changelog file.

    Returns:
        List of error messages (empty if at least one valid entry exists).
    """
    if not ENTRY_PATTERN.search(content):
        return ["No valid changelog entry found (expected '## YYYY-MM-DD — [tag]:')"]
    return []
