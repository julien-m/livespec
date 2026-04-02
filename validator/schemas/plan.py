"""Plan frontmatter schema."""
from __future__ import annotations

from datetime import date

from .base import BaseFrontmatter


class PlanFrontmatter(BaseFrontmatter):
    spec_ref: str
    created: date
