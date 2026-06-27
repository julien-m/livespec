"""Deterministic helpers for the Clarify gate (Feature A).

Pure stdlib. Scans a feature ``spec.md`` for clarification opportunities and ranks
them by Impact x Uncertainty into a stable, capped (<=5) question queue. The gate
surfaces three deterministic ambiguity categories:

- vague quality adjectives (``fast``/``scalable``/``secure``/``robust`` seed,
  extensible) used without a numeric criterion in the same sentence;
- explicit ``[NEEDS CLARIFICATION]`` placeholders;
- unconfirmed ``[ASSUMED]`` / ``TBD`` assumptions.

All scoring is closed-form so the same spec always yields the same ranked queue —
no model judgement is involved.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "VAGUE_ADJECTIVES",
    "ClarifyOpportunity",
    "rank_clarification_opportunities",
    "scan_clarification_opportunities",
]

# Extensible seed set of vague quality adjectives (brief: fast/scalable/secure/robust).
VAGUE_ADJECTIVES: tuple[str, ...] = ("fast", "scalable", "secure", "robust")

# Categories (spec-kit taxonomy mapped to LiveSpec).
_CATEGORY_VAGUE = "non-functional quality"
_CATEGORY_PLACEHOLDER = "placeholders"
_CATEGORY_ASSUMPTION = "constraints/tradeoffs"

_REQUIREMENT_RE = re.compile(r"\b(?:FR|AC|SC)-\d+\b")
# A real metric is a standalone numeric token (e.g. "200 ms", "99%"). A digit glued
# to letters is part of an identifier/proper noun (OAuth2, S3, v2, IPv6) and must NOT
# count as quantification, otherwise it would silence a genuine vague-adjective ambiguity.
_METRIC_RE = re.compile(r"(?<![A-Za-z])\d")
_CLARIFICATION_MARKER_RE = re.compile(r"\[NEEDS CLARIFICATION\]")
_ASSUMPTION_MARKER_RE = re.compile(r"\[ASSUMED\]|\bTBD\b")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class ClarifyOpportunity:
    """A single ranked clarification candidate grounded in spec evidence."""

    category: str
    question: str
    impact: int
    uncertainty: int
    evidence_path: Path
    evidence_line: int | None
    evidence_text: str

    @property
    def score(self) -> int:
        return self.impact * self.uncertainty


def _split_sentences(line: str) -> list[str]:
    return [segment for segment in _SENTENCE_SPLIT_RE.split(line) if segment.strip()]


def _has_metric(sentence: str) -> bool:
    """True when a real numeric criterion is present, ignoring requirement IDs.

    Requirement tokens such as ``FR-001`` carry digits that are identifiers, not
    measurements; they must not count as a metric or the gate would treat every
    requirement sentence as already quantified.
    """
    cleaned = _REQUIREMENT_RE.sub(" ", sentence)
    return bool(_METRIC_RE.search(cleaned))


def scan_clarification_opportunities(spec_path: Path) -> list[ClarifyOpportunity]:
    """Scan ``spec_path`` for deterministic clarification opportunities."""
    text = spec_path.read_text(encoding="utf-8")
    opportunities: list[ClarifyOpportunity] = []

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        is_requirement = bool(_REQUIREMENT_RE.search(line))

        if _CLARIFICATION_MARKER_RE.search(line):
            opportunities.append(
                ClarifyOpportunity(
                    category=_CATEGORY_PLACEHOLDER,
                    question=f"Resolve the [NEEDS CLARIFICATION] marker: {line}",
                    impact=3,
                    uncertainty=3,
                    evidence_path=spec_path,
                    evidence_line=line_number,
                    evidence_text=line,
                )
            )
        if _ASSUMPTION_MARKER_RE.search(line):
            opportunities.append(
                ClarifyOpportunity(
                    category=_CATEGORY_ASSUMPTION,
                    question=f"Confirm or replace the assumption: {line}",
                    impact=2,
                    uncertainty=2,
                    evidence_path=spec_path,
                    evidence_line=line_number,
                    evidence_text=line,
                )
            )

        for sentence in _split_sentences(line):
            if _has_metric(sentence):
                continue
            lowered = sentence.lower()
            for adjective in VAGUE_ADJECTIVES:
                if re.search(rf"\b{re.escape(adjective)}\b", lowered):
                    opportunities.append(
                        ClarifyOpportunity(
                            category=_CATEGORY_VAGUE,
                            question=(
                                f"Quantify '{adjective}' with a measurable criterion: {sentence}"
                            ),
                            impact=3 if is_requirement else 2,
                            uncertainty=3,
                            evidence_path=spec_path,
                            evidence_line=line_number,
                            evidence_text=sentence,
                        )
                    )

    return opportunities


def rank_clarification_opportunities(
    opportunities: list[ClarifyOpportunity], *, limit: int = 5
) -> list[ClarifyOpportunity]:
    """Return the top ``limit`` opportunities by a stable Impact x Uncertainty order.

    Tie-break order: ``(-score, category, evidence_path, evidence_line, question)``.
    """
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
    return ordered[:limit]
