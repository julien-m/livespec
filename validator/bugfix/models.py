"""Value objects shared by the bugfix gate, record and CLI (feature 084)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Verdict = Literal["READY", "ELIGIBLE", "FALLBACK"]

# Calibrated on the six audit bugs of 2026-10-12 (plan D-06): the largest touched
# about six files; a typical fix is one source file plus one test under 100 lines.
DEFAULT_MAX_FILES = 8
DEFAULT_MAX_LINES = 300


class BugfixConfigError(ValueError):
    """`.specs/bugfix.yaml` is unreadable or declares an invalid threshold."""


class BugfixInputError(ValueError):
    """A command argument cannot be used (unknown feature, unreadable receipt path)."""


@dataclass(frozen=True)
class BugfixLimits:
    """Diff confinement thresholds and where they came from."""

    max_files: int = DEFAULT_MAX_FILES
    max_lines: int = DEFAULT_MAX_LINES
    source: str = "default"


@dataclass(frozen=True)
class FallbackReason:
    """One failed eligibility condition."""

    code: str
    detail: str


@dataclass
class GateReport:
    """Outcome of one gate evaluation; reasons empty means eligible."""

    feature: str
    closing: bool
    limits: BugfixLimits
    reasons: list[FallbackReason] = field(default_factory=lambda: list[FallbackReason]())
    regression_tests: list[str] = field(default_factory=lambda: list[str]())
    counted_files: list[str] = field(default_factory=lambda: list[str]())
    counted_lines: int = 0
    red_invocation: str = ""
    green_invocation: str = ""

    @property
    def verdict(self) -> Verdict:
        """Return FALLBACK on any reason, else READY (pre-edit) or ELIGIBLE (closing)."""
        if self.reasons:
            return "FALLBACK"
        return "ELIGIBLE" if self.closing else "READY"

    @property
    def fallback_command(self) -> str:
        """Return the complete gate that applies when the lane does not."""
        return f"livespec validate .specs/features/{self.feature} --progression implement"

    def to_json(self) -> dict[str, object]:
        """Return the AC-011 JSON object."""
        return {
            "verdict": self.verdict,
            "feature": self.feature,
            "reasons": [{"code": r.code, "detail": r.detail} for r in self.reasons],
            "regression_tests": self.regression_tests,
            "counted_files": self.counted_files,
            "counted_lines": self.counted_lines,
            "limits": {
                "max_files": self.limits.max_files,
                "max_lines": self.limits.max_lines,
                "source": self.limits.source,
            },
            "fallback_command": self.fallback_command,
        }
