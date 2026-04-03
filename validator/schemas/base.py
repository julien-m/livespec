"""Base frontmatter model shared by all spec types."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


class BaseFrontmatter(BaseModel):
    """Base frontmatter model shared by all spec types."""

    model_config = ConfigDict(extra="ignore")
    title: str

    @field_validator("title")
    @classmethod
    def validate_title_not_empty(cls, v: str) -> str:
        """Ensure title is not empty or whitespace."""
        if not v.strip():
            raise ValueError("title cannot be empty")
        return v
