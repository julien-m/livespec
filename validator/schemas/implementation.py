"""Implementation frontmatter schema."""
from __future__ import annotations

from .base import BaseFrontmatter


class ImplementationFrontmatter(BaseFrontmatter):
    feature: str
