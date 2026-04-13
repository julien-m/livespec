"""Implementation frontmatter schema."""

from __future__ import annotations

from .base import BaseFrontmatter


class ImplementationFrontmatter(BaseFrontmatter):
    """Frontmatter schema for implementation.md files."""

    feature: str
