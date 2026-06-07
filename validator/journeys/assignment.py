"""Deterministic feature/ref assignment for journey creation intents."""

# @spec FR-013, FR-014, FR-016: journey assignment and implemented features
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#fr-013

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .schema import CoverageRef, CoverageRefKind

_REF_LINE_RE = re.compile(r"- \*\*((?:AC|FR)-\d+):\*\*\s*(.+)")
_NON_SLUG_RE = re.compile(r"[^0-9A-Za-z]+")


@dataclass(frozen=True)
class AssignmentEvidence:
    """Source evidence used to infer a journey coverage ref."""

    feature: str
    ref: str
    source_path: str
    excerpt: str
    score: int


@dataclass(frozen=True)
class JourneyAssignmentCandidate:
    """Candidate generated from a journey intent or existing project scan."""

    journey_id: str
    title: str
    covers: list[CoverageRef] = field(default_factory=list)
    evidence: list[AssignmentEvidence] = field(default_factory=list)
    confidence: int = 0
    ambiguous: bool = False


def infer_journey_assignment(project_root: Path, intent: str) -> JourneyAssignmentCandidate:
    """Infer feature/AC/FR refs from a free-form journey intent.

    Args:
        project_root: Project root containing `.specs/`.
        intent: Natural-language journey description.

    Returns:
        Candidate assignment with evidence for interactive confirmation.
    """
    evidence = _collect_matching_evidence(project_root, intent)
    covers = [
        CoverageRef(
            feature=item.feature,
            kind=CoverageRefKind.AC if item.ref.startswith("AC-") else CoverageRefKind.FR,
            ref=item.ref,
            reason=item.excerpt,
        )
        for item in evidence
    ]
    return JourneyAssignmentCandidate(
        journey_id=_slugify(intent),
        title=intent.strip().capitalize(),
        covers=covers,
        evidence=evidence,
        confidence=sum(item.score for item in evidence),
        ambiguous=not evidence,
    )


def _collect_matching_evidence(project_root: Path, intent: str) -> list[AssignmentEvidence]:
    """Score requirement lines against an intent and keep positive matches."""
    intent_terms = _terms(intent)
    results: list[AssignmentEvidence] = []
    for spec_path in sorted((project_root / ".specs" / "features").glob("*/spec.md")):
        feature = spec_path.parent.name
        for ref, text in _requirement_lines(spec_path):
            overlap = len(intent_terms.intersection(_terms(text)))
            if overlap == 0:
                continue
            results.append(
                AssignmentEvidence(
                    feature=feature,
                    ref=ref,
                    source_path=spec_path.as_posix(),
                    excerpt=text,
                    score=overlap,
                )
            )
    return sorted(results, key=lambda item: (-item.score, item.feature, item.ref))


def _requirement_lines(spec_path: Path) -> list[tuple[str, str]]:
    """Extract AC/FR requirement text from a spec file."""
    lines: list[tuple[str, str]] = []
    for line in spec_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = _REF_LINE_RE.match(line.strip())
        if match is None:
            continue
        lines.append((match.group(1), match.group(2).strip()))
    return lines


def _terms(text: str) -> set[str]:
    """Normalize text into scoring terms."""
    return {term for term in re.split(r"[^a-z0-9]+", text.lower()) if len(term) > 2}


def _slugify(text: str) -> str:
    """Create a stable journey ID from free text."""
    slug = _NON_SLUG_RE.sub("-", text.strip().lower()).strip("-")
    return slug or "journey"


__all__ = [
    "AssignmentEvidence",
    "JourneyAssignmentCandidate",
    "infer_journey_assignment",
]
