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

# Traceability — behaviors protected by this suite (069-clarify-gate):
# @spec(FR-002) @spec(FR-003) @spec(FR-004) @spec(FR-005) @spec(FR-006) @spec(FR-007)


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


def test_placeholder_and_assumption_markers_are_detected(tmp_path: Path) -> None:
    """FR-004: [NEEDS CLARIFICATION] -> placeholders; [ASSUMED]/TBD -> constraints/tradeoffs."""
    spec = _write_spec(
        tmp_path,
        [
            "# Spec",
            "- The retention window is [NEEDS CLARIFICATION].",
            "- The export format is [ASSUMED] to be CSV.",
            "- The rate limit is TBD.",
        ],
    )

    opportunities = scan_clarification_opportunities(spec)
    by_category = {o.category for o in opportunities}

    # The placeholder marker yields a placeholders opportunity.
    assert "placeholders" in by_category
    # Both [ASSUMED] and TBD yield constraints/tradeoffs opportunities.
    assumption_lines = {
        o.evidence_line for o in opportunities if o.category == "constraints/tradeoffs"
    }
    assert assumption_lines == {3, 4}


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
    # FR-002's latency metric does not resolve its security ambiguity.
    assert 3 in flagged_lines


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


# @spec FR-006: Bilingual claim metrics
# — .specs/features/078-requirement-evidence-integrity/spec.md#fr-006


def test_unrelated_population_does_not_resolve_security(tmp_path: Path) -> None:
    spec = _write_spec(
        tmp_path, ["FR-001: secure for 10 users.", "FR-002: sécurisé pour 10 utilisateurs."]
    )
    assert len(scan_clarification_opportunities(spec)) == 2


def test_metric_belongs_to_quality_not_neighbouring_claim(tmp_path: Path) -> None:
    spec = _write_spec(
        tmp_path,
        ["FR-001: fast under 200 ms and secure.", "FR-002: rapide sous 200 ms et robuste."],
    )
    items = scan_clarification_opportunities(spec)
    assert len(items) == 2
    assert all("secure" in item.question or "robuste" in item.question for item in items)


def test_six_critical_questions_survive_presentation_limit(tmp_path: Path) -> None:
    spec = _write_spec(
        tmp_path, [f"FR-{i:03d}: [NEEDS CLARIFICATION] permission {i}" for i in range(1, 7)]
    )
    items = scan_clarification_opportunities(spec)
    assert len(rank_clarification_opportunities(items, limit=None)) == 6
    assert len(rank_clarification_opportunities(items, limit=20)) == 5
    assert all(item.critical and item.source_hash and item.requirement_id for item in items)


def test_requirement_heading_qualifies_body_ambiguity(tmp_path: Path) -> None:
    spec = _write_spec(tmp_path, ["### FR-001", "**Requirement:** The API must be secure."])
    item = scan_clarification_opportunities(spec)[0]
    assert item.requirement_id == f"{tmp_path.name}:FR-001"
    assert item.critical
