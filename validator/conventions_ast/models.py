# @spec FR-002: Separate AST layer — .specs/features/072-conventions-ast-rule-engine/spec.md#fr-002

"""Typed contracts for AST convention rules, matches, and backend status."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from validator.conventions_gate_types import GateBlocker, GateViolation

AstBackendStatus = Literal["available", "unavailable", "error", "skipped"]
AstDecidability = Literal["ast", "graph", "semantic", "external", "visual"]
AstPrecision = Literal["high", "medium", "low"]


@dataclass(frozen=True)
class AstPattern:
    """One backend-specific structural pattern."""

    kind: str
    value: str


@dataclass(frozen=True)
class AstFixtures:
    """Required PASS and FAIL fixtures for an active AST rule."""

    pass_path: str
    fail_path: str


@dataclass(frozen=True)
class AstJustification:
    """Nearby justification policy for a rule match."""

    required: bool = False
    accepted_window: Literal["adjacent_comment_block"] = "adjacent_comment_block"
    rule_id_required: bool = True


@dataclass(frozen=True)
class AstRule:
    """One traceable AST convention rule."""

    id: str
    title: str
    language: str
    decidability: AstDecidability
    precision: AstPrecision
    severity: Literal["warning", "error"]
    source_path: str
    source_anchor: str
    source_hash: str
    backend: str
    patterns: tuple[AstPattern, ...]
    fixtures: AstFixtures
    justification: AstJustification

    def metadata_payload(self) -> dict[str, object]:
        """Return stable rule metadata included in receipt hash inputs."""
        return {
            "id": self.id,
            "language": self.language,
            "decidability": self.decidability,
            "precision": self.precision,
            "severity": self.severity,
            "source_path": self.source_path,
            "source_anchor": self.source_anchor,
            "source_hash": self.source_hash,
            "backend": self.backend,
            "justification": {
                "required": self.justification.required,
                "accepted_window": self.justification.accepted_window,
                "rule_id_required": self.justification.rule_id_required,
            },
        }


@dataclass(frozen=True)
class AstCatalog:
    """A loaded AST rule catalogue."""

    path: Path
    rules: tuple[AstRule, ...]
    sha256: str


@dataclass(frozen=True)
class AstSourceFile:
    """Source file metadata consumed from the existing language layer."""

    path: Path
    language: str
    text: str


@dataclass(frozen=True)
class AstMatch:
    """One structural match returned by an AST backend."""

    rule_id: str
    path: Path
    line: int
    message: str


@dataclass(frozen=True)
class AstBackendInfo:
    """Normalized AST backend availability and version status."""

    name: str
    command: str
    status: AstBackendStatus
    version: str | None = None
    message: str = ""

    def to_dict(self) -> dict[str, object]:
        """Return JSON-ready backend status."""
        return {
            "name": self.name,
            "command": self.command,
            "status": self.status,
            "version": self.version,
            "message": self.message,
        }


@dataclass(frozen=True)
class AstBackendResult:
    """Backend scan output with normalized status."""

    info: AstBackendInfo
    matches: tuple[AstMatch, ...]


@dataclass(frozen=True)
class AstEngineResult:
    """AST engine output merged into the conventions gate."""

    summary: dict[str, object] | None
    violations: list[GateViolation]
    blockers: list[GateBlocker]
