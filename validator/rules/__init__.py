"""Rule dispatch for LiveSpec file validation."""

from __future__ import annotations

import re

from .changelog_entries import validate_changelog_entries
from .roadmap_markers import validate_roadmap_markers
from .sections import validate_sections

__all__ = ["validate_by_type", "validate_sections"]

_PLACEHOLDER_PATTERN = re.compile(r"\[(?:TBD|PLACEHOLDER|TODO)\]", re.IGNORECASE)


def validate_by_type(
    content: str, file_type: str, code_blocks: list[dict]
) -> list[str]:
    """Run type-specific validation rules and return errors.

    Args:
        content: Raw markdown content of the file.
        file_type: Spec file type (e.g. "roadmap", "changelog", "plan").
        code_blocks: Parsed code blocks with at least a "lang" key each.

    Returns:
        List of validation error messages (empty if valid).
    """
    errors: list[str] = []

    if file_type == "roadmap":
        errors.extend(validate_roadmap_markers(content))

    elif file_type == "changelog":
        errors.extend(validate_changelog_entries(content))

    elif file_type == "plan":
        has_mermaid = any(cb.get("lang") == "mermaid" for cb in code_blocks)
        if not has_mermaid:
            errors.append("Plan requires at least one mermaid code block")

    elif file_type == "implementation":
        if "@spec" not in content:
            errors.append("Implementation requires at least one @spec anchor")

    elif file_type == "progress":
        if "| Step" not in content and "|Step" not in content:
            errors.append("Progress requires a table with a 'Step' column")

    elif file_type in ("constitution", "project"):
        if len(content) <= 100:
            errors.append("Content too short (must be >100 characters)")
        if _PLACEHOLDER_PATTERN.search(content):
            errors.append("Content contains placeholder tags ([TBD], [PLACEHOLDER], or [TODO])")

    return errors
