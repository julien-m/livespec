"""Typed report models for the LiveSpec project doctor."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypeAlias

JsonValue: TypeAlias = (
    str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
)


class DoctorStatus(StrEnum):
    """Top-level doctor verdict."""

    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"


class DoctorSeverity(StrEnum):
    """Finding severities used by doctor reports."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class DoctorFinding:
    """A categorized project health finding."""

    code: str
    severity: DoctorSeverity
    category: str
    message: str
    feature: str | None = None
    requirement: str | None = None
    path: str | None = None
    suggested_action: str | None = None
    autofixable: bool = False

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a stable JSON-ready representation."""
        return {
            "code": self.code,
            "severity": self.severity.value,
            "category": self.category,
            "message": self.message,
            "feature": self.feature,
            "requirement": self.requirement,
            "path": self.path,
            "suggested_action": self.suggested_action,
            "autofixable": self.autofixable,
        }


@dataclass(frozen=True)
class CleanupAction:
    """A proposed non-destructive cleanup action."""

    code: str
    path: str
    description: str
    destructive: bool = True
    refused: bool = False

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a stable JSON-ready representation."""
        return {
            "code": self.code,
            "path": self.path,
            "description": self.description,
            "destructive": self.destructive,
            "refused": self.refused,
        }


@dataclass(frozen=True)
class DoctorReport:
    """Full project health report."""

    status: DoctorStatus
    findings: list[DoctorFinding] = field(default_factory=list)
    cleanup_actions: list[CleanupAction] = field(default_factory=list)
    strict: bool = False

    @property
    def effective_findings(self) -> list[DoctorFinding]:
        """Return findings after strict warning promotion."""
        if not self.strict:
            return self.findings
        promoted: list[DoctorFinding] = []
        for finding in self.findings:
            if finding.severity == DoctorSeverity.WARNING:
                promoted.append(
                    DoctorFinding(
                        code=finding.code,
                        severity=DoctorSeverity.ERROR,
                        category=finding.category,
                        message=finding.message,
                        feature=finding.feature,
                        requirement=finding.requirement,
                        path=finding.path,
                        suggested_action=finding.suggested_action,
                        autofixable=finding.autofixable,
                    )
                )
            else:
                promoted.append(finding)
        return promoted

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a stable machine-readable report."""
        findings = self.effective_findings
        return {
            "status": self.status.value,
            "summary": {
                "errors": sum(
                    1 for finding in findings if finding.severity == DoctorSeverity.ERROR
                ),
                "warnings": sum(
                    1 for finding in findings if finding.severity == DoctorSeverity.WARNING
                ),
                "infos": sum(1 for finding in findings if finding.severity == DoctorSeverity.INFO),
                "findings": len(findings),
            },
            "findings": [finding.to_dict() for finding in findings],
            "cleanup_actions": [action.to_dict() for action in self.cleanup_actions],
        }


__all__ = [
    "CleanupAction",
    "DoctorFinding",
    "DoctorReport",
    "DoctorSeverity",
    "DoctorStatus",
]
