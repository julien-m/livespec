"""Core types for coherence validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


class Severity(Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class Violation:
    """A single coherence violation."""

    rule_id: str
    severity: Severity
    message: str
    context: dict[str, Any] = field(default_factory=dict)
    fix_hint: str | None = None
    suppress_if_creating: bool = False


class CoherenceRule(Protocol):
    """Interface for coherence rules."""

    rule_id: str
    description: str
    wave: int

    def check(self, graph: Any) -> list[Violation]: ...
