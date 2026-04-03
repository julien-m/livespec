"""Schema registry for LiveSpec file types."""
from __future__ import annotations

from typing import TYPE_CHECKING

# Avoid runtime pydantic import for lightweight module loading
if TYPE_CHECKING:
    from pydantic import BaseModel

from .implementation import ImplementationFrontmatter
from .plan import PlanFrontmatter
from .spec import SpecFrontmatter
from .stack import StackFrontmatter

_SCHEMA_MAP: dict[str, type[BaseModel]] = {
    "spec": SpecFrontmatter,
    "plan": PlanFrontmatter,
    "implementation": ImplementationFrontmatter,
    "stack": StackFrontmatter,
}


def get_schema(file_type: str) -> type[BaseModel] | None:
    """Return the Pydantic model for a file type, or None if no schema applies.

    Args:
        file_type: Spec file type (e.g. "spec", "plan", "implementation").

    Returns:
        Pydantic model class, or None for types without a schema.
    """
    return _SCHEMA_MAP.get(file_type)
