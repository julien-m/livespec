"""Validate changelog entry format."""

from __future__ import annotations

import re

# The one entry format, written by authors, `bugfix record` and `finalize apply`.
ENTRY_PATTERN = re.compile(r"^## \d{4}-\d{2}-\d{2} — \[.+\]:", re.MULTILINE)
# Read-only compatibility: `finalize apply` before 2026-10-13 wrote "### date — line"
# entries, each closed by its finalize marker. Such marked entries stay valid.
_LEGACY_FINALIZE_ENTRY = re.compile(
    r"^### \d{4}-\d{2}-\d{2} — .*\n(?:(?!#{1,3} ).*\n)*?"
    r"<!-- finalize:[^:\n]+:[0-9-]*:[0-9a-f]{8} -->",
    re.MULTILINE,
)


def validate_changelog_entries(content: str) -> list[str]:
    """Return errors if no valid changelog entry is found.

    Args:
        content: Raw markdown content of the changelog file.

    Returns:
        List of error messages (empty if at least one valid entry exists).
    """
    if not ENTRY_PATTERN.search(content) and not _LEGACY_FINALIZE_ENTRY.search(content):
        return ["No valid changelog entry found (expected '## YYYY-MM-DD — [tag]:')"]
    return []
