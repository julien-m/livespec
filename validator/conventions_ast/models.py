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
AstDecisionKind = Literal["executable", "generated-executable"]


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
class AstDeterministicTestEvidence:
    """Executable proof tying a rule to fixtures and a deterministic test."""

    test: str
    pass_fixture: str
    fail_fixture: str

    def to_dict(self) -> dict[str, str]:
        """Return JSON-ready evidence metadata."""
        return {
            "test": self.test,
            "pass_fixture": self.pass_fixture,
            "fail_fixture": self.fail_fixture,
        }


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
    domain: str
    decision_kind: AstDecisionKind
    decidability: AstDecidability
    precision: AstPrecision
    severity: Literal["warning", "error"]
    source_path: str
    source_anchor: str
    source_hash: str
    backend: str
    detector: str
    patterns: tuple[AstPattern, ...]
    fixtures: AstFixtures
    deterministic_test_evidence: tuple[AstDeterministicTestEvidence, ...]
    justification: AstJustification

    def metadata_payload(self) -> dict[str, object]:
        """Return stable rule metadata included in receipt hash inputs."""
        fixture_family = _fixture_family(self.fixtures.fail_path)
        return {
            "id": self.id,
            "language": self.language,
            "domain": self.domain,
            "decision_kind": self.decision_kind,
            "decidability": self.decidability,
            "precision": self.precision,
            "severity": self.severity,
            "source_path": self.source_path,
            "source_anchor": self.source_anchor,
            "source_hash": self.source_hash,
            "backend": self.backend,
            "detector": self.detector,
            "fixture_family": fixture_family,
            "fixtures": {
                "pass": self.fixtures.pass_path,
                "fail": self.fixtures.fail_path,
            },
            "deterministic_test_evidence": [
                evidence.to_dict() for evidence in self.deterministic_test_evidence
            ],
            "justification": {
                "required": self.justification.required,
                "accepted_window": self.justification.accepted_window,
                "rule_id_required": self.justification.rule_id_required,
            },
        }


def _fixture_family(fail_path: str) -> str:
    parts = Path(fail_path).parts
    try:
        index = parts.index("conventions_ast")
    except ValueError:
        # External test catalogues can use any fixture tree; keep their parent as the family.
        return str(Path(fail_path).parent)
    return Path(*parts[index + 1 : -1]).as_posix()


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
