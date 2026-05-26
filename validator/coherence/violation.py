"""Core types for coherence validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:  # Circular: graph_builder imports Violation from this module
    from pathlib import Path

    from validator.coherence.graph_builder import SpecGraph


class Severity(Enum):
    """Severity levels for coherence violations.

    Attributes:
        ERROR: Critical coherence violation blocking validation.
        WARNING: Non-critical coherence issue requiring attention.
        INFO: Informational message without blocking impact.
    """

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class Violation:
    """A single coherence violation."""

    rule_id: str
    severity: Severity
    message: str
    context: dict[str, object] = field(default_factory=dict)
    fix_hint: str | None = None
    suppress_if_creating: bool = False


class CoherenceRule(Protocol):
    """Interface for coherence rules."""

    rule_id: str
    description: str
    wave: int

    def check(self, graph: SpecGraph, specs_root: Path) -> list[Violation]:
        """Check coherence violations.

        Args:
            graph: SpecGraph containing all parsed spec artifacts.
            specs_root: Root directory of the .specs/ tree for file access.

        Returns:
            List of Violation objects found by this rule.
        """
        ...
