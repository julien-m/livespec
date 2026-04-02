"""Base frontmatter model shared by all spec types."""
from __future__ import annotations

from pydantic import BaseModel, field_validator


class BaseFrontmatter(BaseModel):
    model_config = {"extra": "allow"}
    title: str

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title cannot be empty")
        return v
