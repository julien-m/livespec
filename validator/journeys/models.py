# LiveSpec traceability anchors
# @spec(FR-002)

"""Typed models for canonical executable user journeys."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TypeAlias

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


class JourneySeverity(StrEnum):
    """Validation and doctor finding severity."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class JourneyIssue:
    """Validation issue for one journey source file."""

    code: str
    severity: JourneySeverity
    message: str
    path: Path


@dataclass(frozen=True)
class JourneyFile:
    """Canonical journey source loaded from a `.journey.yaml` file."""

    path: Path
    journey_id: str
    feature: str
    title: str
    target_surface: str
    run_policy: str
    runner: str
    steps: list[dict[str, JsonValue]]
    schema_version: int = 1
    covered_features: list[str] = field(default_factory=list)
    covers_ac: list[str] = field(default_factory=list)
    covers_fr: list[str] = field(default_factory=list)
    disabled: bool = False
    manual_reason: str | None = None
    source_hash: str = ""

    @property
    def is_manual(self) -> bool:
        """Return True when the journey is a manual obligation."""
        return self.run_policy == "manual"

    @property
    def is_executable(self) -> bool:
        """Return True when the journey should compile and execute."""
        return not self.disabled and not self.is_manual


@dataclass(frozen=True)
class ValidationResult:
    """Validation result for all scanned journey files."""

    journeys: list[JourneyFile] = field(default_factory=list)
    issues: list[JourneyIssue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        """Return the number of validation errors."""
        return sum(1 for issue in self.issues if issue.severity == JourneySeverity.ERROR)

    @property
    def warning_count(self) -> int:
        """Return the number of validation warnings."""
        return sum(1 for issue in self.issues if issue.severity == JourneySeverity.WARNING)


@dataclass(frozen=True)
class CompiledJourneyArtifact:
    """Native test artifact generated from a canonical journey."""

    source_path: Path
    output_path: Path
    source_hash: str
    runner: str


@dataclass(frozen=True)
class CompileResult:
    """Result of an ahead-of-time journey compilation run."""

    artifacts: list[CompiledJourneyArtifact] = field(default_factory=list)
    issues: list[JourneyIssue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        """Return the number of blocking compilation issues."""
        return sum(1 for issue in self.issues if issue.severity == JourneySeverity.ERROR)


@dataclass(frozen=True)
class JourneyFinding:
    """Doctor finding emitted by journey scanning."""

    code: str
    severity: JourneySeverity
    message: str
    path: Path
    feature: str | None = None
    requirement: str | None = None


@dataclass(frozen=True)
class JourneyReport:
    """Aggregated journey health and coverage category report."""

    journeys: list[JourneyFile] = field(default_factory=list)
    findings: list[JourneyFinding] = field(default_factory=list)

    @property
    def executable_count(self) -> int:
        """Return the number of executable journeys."""
        return sum(1 for journey in self.journeys if journey.is_executable)

    @property
    def manual_count(self) -> int:
        """Return the number of manual journeys."""
        return sum(1 for journey in self.journeys if journey.is_manual)

    @property
    def disabled_count(self) -> int:
        """Return the number of disabled journeys."""
        return sum(1 for journey in self.journeys if journey.disabled)
