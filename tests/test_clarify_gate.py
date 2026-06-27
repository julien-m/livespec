"""Tests for validator.clarify_gate — deterministic Clarify gate helpers (Feature A).

Protected invariants:
- A vague quality adjective (fast/scalable/secure/robust) is a clarification
  opportunity ONLY when its sentence carries no numeric criterion — once a metric
  is present the requirement is measurable and must NOT be flagged.
- The ranking is a pure function of Impact x Uncertainty with a total, stable
  tie-break order and a hard cap of 5, so the gate asks the same <=5 questions
  regardless of scan order.
"""

from __future__ import annotations

from pathlib import Path

from validator.clarify_gate import (
    VAGUE_ADJECTIVES,
    ClarifyOpportunity,
    rank_clarification_opportunities,
    scan_clarification_opportunities,
)


def _identity_key(opportunity: ClarifyOpportunity) -> tuple[str, str, int | None, str]:
    return (
        opportunity.category,
        str(opportunity.evidence_path),
        opportunity.evidence_line,
        opportunity.question,
    )


def _write_spec(tmp_path: Path, lines: list[str]) -> Path:
    spec = tmp_path / "spec.md"
    spec.write_text("\n".join(lines), encoding="utf-8")
    return spec


def test_vague_adjective_without_metric_is_flagged_but_metric_sentence_is_not(
    tmp_path: Path,
) -> None:
    spec = _write_spec(
        tmp_path,
        [
            "# Feature Spec",
            "- FR-001: The system must be fast.",
            "- FR-002: The system must be fast: p95 latency under 200 ms.",
        ],
    )

    opportunities = scan_clarification_opportunities(spec)
    flagged_lines = {o.evidence_line for o in opportunities}

    # FR-001 (line 2) has a vague adjective and no metric -> flagged.
    assert 2 in flagged_lines
    # FR-002 (line 3) quantifies "fast" in the same sentence -> not flagged.
    assert 3 not in flagged_lines


def test_every_seed_adjective_is_detected(tmp_path: Path) -> None:
    spec = _write_spec(
        tmp_path,
        ["# Spec"] + [f"- FR-00{i}: must be {adj}." for i, adj in enumerate(VAGUE_ADJECTIVES, 1)],
    )

    opportunities = scan_clarification_opportunities(spec)

    assert len(opportunities) == len(VAGUE_ADJECTIVES)


def test_digit_inside_identifier_is_not_treated_as_a_metric(tmp_path: Path) -> None:
    """A digit glued to letters (OAuth2, S3, v2) is an identifier, not a measurement.

    Invariant: such digits must NOT silence a vague-adjective ambiguity — only a
    standalone numeric criterion (e.g. `200 ms`) counts as quantification.
    """
    spec = _write_spec(
        tmp_path,
        [
            "# Spec",
            "- FR-001: The login must use a secure OAuth2 flow.",
            "- FR-002: The login must be secure within 200 ms.",
        ],
    )

    opportunities = scan_clarification_opportunities(spec)
    flagged_lines = {o.evidence_line for o in opportunities}

    # OAuth2's "2" is part of an identifier -> "secure" stays ambiguous -> flagged.
    assert 2 in flagged_lines
    # FR-002 has a real standalone metric (200 ms) -> not flagged.
    assert 3 not in flagged_lines


def test_ranking_prefers_higher_score_and_caps_at_five(tmp_path: Path) -> None:
    lines = ["# Spec"]
    # 3 requirement-level vague adjectives -> impact 3 x uncertainty 3 = score 9.
    lines += [f"- FR-00{i}: must be robust." for i in range(1, 4)]
    # 6 prose-level vague adjectives -> impact 2 x uncertainty 3 = score 6.
    lines += ["The interface should feel fast." for _ in range(6)]
    spec = _write_spec(tmp_path, lines)

    ranked = rank_clarification_opportunities(scan_clarification_opportunities(spec))

    assert len(ranked) == 5
    assert [o.score for o in ranked] == [9, 9, 9, 6, 6]


def test_ranking_is_deterministic_regardless_of_scan_order(tmp_path: Path) -> None:
    lines = ["# Spec"]
    lines += [f"- FR-00{i}: must be secure." for i in range(1, 4)]
    lines += ["The dashboard should be scalable." for _ in range(4)]
    spec = _write_spec(tmp_path, lines)
    scanned = scan_clarification_opportunities(spec)

    forward = rank_clarification_opportunities(scanned)
    reverse = rank_clarification_opportunities(list(reversed(scanned)))

    assert [_identity_key(o) for o in forward] == [_identity_key(o) for o in reverse]
