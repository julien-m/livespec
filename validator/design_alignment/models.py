"""Data model for the design alignment gate.

# @spec FR-003: Design alignment module
#   — .specs/features/047-design-alignment-gate/spec.md#fr-003
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

Verdict = Literal["PASS", "FAIL", "BLOCKED"]


@dataclass(frozen=True)
class AlignmentIssue:
    """One actionable support or design/runtime mismatch."""

    severity: Verdict
    field: str
    expected: object
    actual: object
    message: str
    node_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""
        return asdict(self)


@dataclass(frozen=True)
class AlignmentResult:
    """Result returned by the design alignment comparator."""

    screen: str
    verdict: Verdict
    issues: list[AlignmentIssue] = field(default_factory=lambda: [])
    report_path: Path | None = None
    manifest_path: Path | None = None

    @property
    def exit_code(self) -> int:
        """Map verdicts to process exit codes."""
        if self.verdict == "PASS":
            return 0
        if self.verdict == "FAIL":
            return 1
        return 2

    @property
    def summary(self) -> str:
        """Machine-readable summary line consumed by orchestrators."""
        return f"Design Alignment Verdict: {self.verdict}"

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe result payload."""
        return {
            "screen": self.screen,
            "verdict": self.verdict,
            "summary": self.summary,
            "exit_code": self.exit_code,
            "issues": [issue.to_dict() for issue in self.issues],
            "report_path": str(self.report_path) if self.report_path else None,
            "manifest_path": str(self.manifest_path) if self.manifest_path else None,
        }


@dataclass(frozen=True)
class NormalizedContract:
    """Normalized design or runtime contract for one screen."""

    screen: str
    support: dict[str, Any]
    nodes: dict[str, dict[str, Any]]
    source_path: Path
    source_hash: str
