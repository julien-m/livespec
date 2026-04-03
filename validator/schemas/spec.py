"""Spec frontmatter schema."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import model_validator

from .base import BaseFrontmatter


class SpecFrontmatter(BaseFrontmatter):
    """Frontmatter schema for spec.md files."""

    status: Literal["Draft", "Review", "Approved", "Implemented", "Deprecated"]
    priority: Literal["P1", "P2", "P3"]
    created: date
    updated: date

    @model_validator(mode="after")
    def validate_updated_not_before_created(self) -> SpecFrontmatter:
        """Ensure updated date is not before created date."""
        if self.updated < self.created:
            raise ValueError("updated must be >= created")
        return self
