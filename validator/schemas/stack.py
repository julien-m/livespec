"""Stack frontmatter schema."""

from __future__ import annotations

from datetime import date

from .base import BaseFrontmatter


class StackFrontmatter(BaseFrontmatter):
    """Frontmatter schema for stack.md files."""

    updated: date
