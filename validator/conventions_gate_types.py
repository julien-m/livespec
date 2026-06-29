# @spec(FR-006)

# LiveSpec traceability anchors
# @spec(FR-002)
# @spec(FR-003)

"""Shared types for deterministic conventions verification."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

GateSeverityInput = Literal["warning", "error"]
SourceKind = Literal["builtin", "linter", "system", "ast"]


class GateSeverity(StrEnum):
    """Violation severity."""

    WARNING = "warning"
    ERROR = "error"


class GateVerdict(StrEnum):
    """Overall conventions verdict."""

    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class GateViolation:
    """One convention violation."""

    rule_id: str
    path: str
    line: int
    severity: GateSeverity | GateSeverityInput
    message: str
    source: SourceKind
    fix_hint: str = ""

    def to_dict(self) -> dict[str, object]:
        """Return JSON-serializable violation payload."""
        severity = self.severity.value if isinstance(self.severity, GateSeverity) else self.severity
        return {
            "rule_id": self.rule_id,
            "path": self.path,
            "line": self.line,
            "severity": severity,
            "message": self.message,
            "source": self.source,
            "fix_hint": self.fix_hint,
        }


@dataclass(frozen=True)
class GateBlocker:
    """One BLOCKED condition."""

    code: str
    message: str
    fix_hint: str = ""

    def to_dict(self) -> dict[str, str]:
        """Return JSON-serializable blocker payload."""
        return {"code": self.code, "message": self.message, "fix_hint": self.fix_hint}


@dataclass(frozen=True)
class GateResult:
    """Complete conventions verification result."""

    verdict: GateVerdict
    violations: list[GateViolation]
    blockers: list[GateBlocker]
    ast_summary: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        """Return JSON-serializable result payload."""
        payload: dict[str, object] = {
            "verdict": self.verdict.value,
            "violations": [violation.to_dict() for violation in self.violations],
            "blockers": [blocker.to_dict() for blocker in self.blockers],
        }
        if self.ast_summary is not None:
            payload["ast_summary"] = self.ast_summary
        return payload
