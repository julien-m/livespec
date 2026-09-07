"""Deterministic bilingual ambiguity candidates and lossless presentation ranking."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "VAGUE_ADJECTIVES",
    "ClarifyOpportunity",
    "rank_clarification_opportunities",
    "scan_clarification_opportunities",
]

# @spec(FR-002): vague adjective without measurable criterion (069-clarify-gate)
# Explicit common French forms share quality rules; preserve the original seed order.
_QUALITY_GROUP: dict[str, str] = {
    "fast": "speed",
    "scalable": "scale",
    "secure": "security",
    "robust": "reliability",
    "rapide": "speed",
    "évolutif": "scale",
    "sécurisé": "security",
    "securise": "security",
    "robuste": "reliability",
    "rapides": "speed",
    "évolutive": "scale",
    "évolutifs": "scale",
    "évolutives": "scale",
    "sécurisée": "security",
    "sécurisés": "security",
    "sécurisées": "security",
    "securisee": "security",
    "securises": "security",
    "securisees": "security",
    "robustes": "reliability",
}
VAGUE_ADJECTIVES: tuple[str, ...] = tuple(_QUALITY_GROUP)

# Categories (spec-kit taxonomy mapped to LiveSpec).
_CATEGORY_VAGUE = "non-functional quality"
_CATEGORY_PLACEHOLDER = "placeholders"
_CATEGORY_ASSUMPTION = "constraints/tradeoffs"

# @spec(FR-003): requirement-ID / identifier digits are not a metric (069-clarify-gate)
_REQUIREMENT_RE = re.compile(r"\b(?:FR|AC|SC)-\d+\b")
# A real metric is a standalone numeric token (e.g. "200 ms", "99%"). A digit glued
# to letters is part of an identifier/proper noun (OAuth2, S3, v2, IPv6) and must NOT
# count as quantification, otherwise it would silence a genuine vague-adjective ambiguity.
# Units are associated with the quality claim, never with arbitrary population counts.
_CAPACITY_NUMBER = r"\d+(?:[, \u00a0\u202f]\d{3})*"
_QUALITY_METRICS = {
    "speed": r"\b\d+(?:[.,]\d+)?\s*(?:ms|milliseconds?|millisecondes?|seconds?|secondes?|s)\b",
    "scale": (
        rf"\b{_CAPACITY_NUMBER}\s*"
        r"(?:(?:concurrent|simultaneous|simultanés?|simultanes?)\s+)?"
        r"(?:users?|utilisateurs?|requests?|requêtes?|jobs?|workers?)\b"
    ),
    "security": (
        r"\b(?:AES[- ]?256|TLS\s*1\.[23]|OWASP\s+ASVS\s+(?:level|niveau)\s*[123])\b"
        r"|\b\d+\s+(?:(?:critical\s+)?vulnerabilit(?:y|ies)"
        r"|vuln[ée]rabilit[ée]s?(?:\s+critiques?)?)\b"
    ),
    "reliability": (
        r"\b\d+(?:[.,]\d+)?\s*%\s*(?:availability|uptime|disponibilité|disponibilite)\b"
        r"|\b(?:error\s+rate|taux\s+(?:d['\u2019])?erreurs?)\b\s*"
        r"(?:below|less\s+than|inf[ée]rieur\s+[àa]|<=?)?\s*\d+(?:[.,]\d+)?\s*%"
    ),
}
# @spec(FR-004): detect placeholder + assumption markers (069-clarify-gate)
_CLARIFICATION_MARKER_RE = re.compile(r"\[NEEDS CLARIFICATION\]")
_ASSUMPTION_MARKER_RE = re.compile(r"\[ASSUMED\]|\bTBD\b")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
# Coordinated claims are separate; commas within numbers are not clause boundaries.
_CLAUSE_SPLIT_RE = re.compile(r";|(?<!\d),|,(?!\d)|\b(?:and|or|but|et|ou|mais)\b", re.IGNORECASE)


@dataclass(frozen=True)
class ClarifyOpportunity:
    """Immutable clarification data; the scanner or review consumer supplies its evidence.

    Attributes:
        category: Ambiguity category used for grouping and stable ranking.
        question: Decision or measurable criterion requested from the user.
        impact: Impact weight used by the ranking function.
        uncertainty: Uncertainty weight used by the ranking function.
        evidence_path: Source path retained by reference; this value performs no file I/O.
        evidence_line: One-based source line, or None when unavailable.
        evidence_text: Cited source excerpt identifying the ambiguity.
        requirement_id: Feature-qualified requirement ID, or empty for unscoped prose.
        decision_key: Decision identity within the requirement, supplied by its detector.
        critical: Whether an unresolved item prevents readiness in the inventory consumer.
        source_hash: Source fingerprint supplied by the scanner or review consumer.
        resolution: Accepted answer supplied by the decision or review consumer; empty if pending.
        resolution_provenance: Supporting citations supplied with an accepted resolution.
        score: Computed impact times uncertainty for presentation ranking.

    The value itself neither validates evidence nor records decisions; consumers own those checks.
    """

    category: str
    question: str
    impact: int
    uncertainty: int
    evidence_path: Path
    evidence_line: int | None
    evidence_text: str
    requirement_id: str = ""
    decision_key: str = ""
    critical: bool = False
    source_hash: str = ""
    resolution: str = ""
    resolution_provenance: tuple[str, ...] = ()

    @property
    def score(self) -> int:
        # @spec(FR-005): rank by Impact x Uncertainty (069-clarify-gate)
        return self.impact * self.uncertainty


def _split_sentences(line: str) -> list[str]:
    return [segment for segment in _SENTENCE_SPLIT_RE.split(line) if segment.strip()]


def _has_metric(clause: str, adjective: str) -> bool:
    """Require a criterion for this quality within the same grammatical clause."""
    pattern = _QUALITY_METRICS[_QUALITY_GROUP[adjective]]
    return bool(re.search(pattern, _REQUIREMENT_RE.sub(" ", clause), re.IGNORECASE))


def _line_opportunities(
    line: str,
    spec_path: Path,
    number: int,
    requirement_id: str,
    source_hash: str,
) -> list[ClarifyOpportunity]:
    """Combine ordered detectors before attaching the shared source identity."""
    candidates = _marker_candidates(
        line,
        _CLARIFICATION_MARKER_RE,
        _CATEGORY_PLACEHOLDER,
        "Resolve the [NEEDS CLARIFICATION] marker",
        3,
    )
    candidates.extend(
        _marker_candidates(
            line,
            _ASSUMPTION_MARKER_RE,
            _CATEGORY_ASSUMPTION,
            "Confirm or replace the assumption",
            2,
        )
    )
    candidates.extend(_quality_candidates(line, requirement_id))
    return _candidate_opportunities(candidates, spec_path, number, requirement_id, source_hash)


def _marker_candidates(
    line: str,
    pattern: re.Pattern[str],
    category: str,
    question: str,
    score: int,
) -> list[tuple[str, str, int, int, str, str]]:
    """Preserve each marker's question, equal scores and exact decision key."""
    if not pattern.search(line):
        return []
    return [(category, f"{question}: {line}", score, score, line, f"{category}:{line}")]


def _quality_candidates(
    line: str,
    requirement_id: str,
) -> list[tuple[str, str, int, int, str, str]]:
    """Check each clause independently so a measured claim cannot mask its vague neighbour."""
    candidates: list[tuple[str, str, int, int, str, str]] = []
    for sentence in _split_sentences(line):
        for clause in _CLAUSE_SPLIT_RE.split(sentence):
            for adjective in VAGUE_ADJECTIVES:
                if re.search(
                    rf"\b{re.escape(adjective)}\b", clause, re.IGNORECASE
                ) and not _has_metric(clause, adjective):
                    identity = " ".join(clause.casefold().split())
                    candidates.append(
                        (
                            _CATEGORY_VAGUE,
                            f"Quantify '{adjective}' with a measurable criterion: {clause}",
                            3 if requirement_id else 2,
                            3,
                            clause,
                            f"quality:{_QUALITY_GROUP[adjective]}:{identity}",
                        )
                    )
    return candidates


def _candidate_opportunities(
    candidates: list[tuple[str, str, int, int, str, str]],
    spec_path: Path,
    number: int,
    requirement_id: str,
    source_hash: str,
) -> list[ClarifyOpportunity]:
    """Attach exact source identity to deterministic question candidates."""
    return [
        ClarifyOpportunity(
            category=category,
            question=question,
            impact=impact,
            uncertainty=uncertainty,
            evidence_path=spec_path,
            evidence_line=number,
            evidence_text=evidence,
            requirement_id=f"{spec_path.parent.name}:{requirement_id}" if requirement_id else "",
            decision_key=decision,
            critical=category == _CATEGORY_PLACEHOLDER
            or (category == _CATEGORY_VAGUE and bool(requirement_id)),
            source_hash=source_hash,
        )
        for category, question, impact, uncertainty, evidence, decision in candidates
    ]


def scan_clarification_opportunities(spec_path: Path) -> list[ClarifyOpportunity]:
    """Scan source declarations, retaining heading identity and every candidate.

    Args:
        spec_path: UTF-8 specification to scan, excluding its Clarifications ledger.

    Returns:
        All detected opportunities in source order, bound to source lines and content hash.

    Raises:
        OSError: The specification cannot be read, including a missing path.
        UnicodeError: The specification cannot be decoded as UTF-8.

    Side effects:
        Reads the specification once; does not write files or resolve decisions.
    """
    text = spec_path.read_text(encoding="utf-8")
    source_hash = hashlib.sha256(text.encode()).hexdigest()
    opportunities: list[ClarifyOpportunity] = []
    in_decisions = False
    heading_requirement = ""
    for number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if line.startswith("## "):
            in_decisions = line == "## Clarifications"
        if line.startswith("#"):
            match = re.fullmatch(r"#{1,6}\s+((?:FR|AC|SC)-\d+)", line)
            heading_requirement = match.group(1) if match else ""
        if in_decisions or not line:
            continue  # The accepted ledger is context, not a new ambiguity declaration.
        match = _REQUIREMENT_RE.search(line)
        requirement = heading_requirement or (match.group() if match else "")
        opportunities.extend(_line_opportunities(line, spec_path, number, requirement, source_hash))
    return opportunities


def rank_clarification_opportunities(
    opportunities: list[ClarifyOpportunity], *, limit: int | None = 5
) -> list[ClarifyOpportunity]:
    """Rank by descending Impact x Uncertainty without mutating the input.

    Args:
        opportunities: Complete candidate list to order for presentation.
        limit: None returns the full inventory; numeric limits are clamped to 0..5.

    Returns:
        A new list ordered by descending score, then category, path, line and question.
        Missing lines sort as -1; equal keys retain input order.

    Side effects:
        None; performs no filesystem access and leaves the candidate list unchanged.
    """
    # @spec(FR-006): deterministic, reproducible ranking (069-clarify-gate)
    # @spec(FR-007): cap the ranked queue at 5 (069-clarify-gate)
    ordered = sorted(
        opportunities,
        key=lambda opportunity: (
            -opportunity.score,
            opportunity.category,
            str(opportunity.evidence_path),
            opportunity.evidence_line if opportunity.evidence_line is not None else -1,
            opportunity.question,
        ),
    )
    return ordered if limit is None else ordered[: max(0, min(limit, 5))]
