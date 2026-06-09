# LiveSpec traceability anchors
# @spec(FR-007)

"""Unit tests for mutmut result parsing and mutation score computation."""

# @spec FR-007: Unit tests for mutmut parser — .specs/features/017-driver-python/spec.md#fr-007

from __future__ import annotations

import json

from validator.drivers.mutmut_parser import compute_mutation_score, parse_mutmut_results


def test_compute_mutation_score_basic() -> None:
    """Mutation score should reflect the killed-to-total ratio."""
    score = compute_mutation_score(killed=8, survived=2)
    assert score == 80.0


def test_compute_mutation_score_perfect() -> None:
    """All killed mutants should yield a perfect score."""
    score = compute_mutation_score(killed=10, survived=0)
    assert score == 100.0


def test_compute_mutation_score_none_killed() -> None:
    """Zero killed mutants should yield zero score."""
    score = compute_mutation_score(killed=0, survived=10)
    assert score == 0.0


def test_compute_mutation_score_no_mutants() -> None:
    """An empty mutant set should not divide by zero."""
    score = compute_mutation_score(killed=0, survived=0)
    assert score == 0.0


def test_parse_mutmut_results_from_json() -> None:
    """JSON output should be converted into the structured result payload."""
    json_output = json.dumps({"killed": 15, "survived": 5, "timeout": 1})

    result = parse_mutmut_results(json_output)

    assert result["killed"] == 15
    assert result["survived"] == 5
    assert result["timeout"] == 1
    assert result["score"] == 75.0


def test_parse_mutmut_results_invalid_json() -> None:
    """Invalid JSON should degrade to an empty parse result."""
    result = parse_mutmut_results("invalid json {{{")

    assert result["killed"] == 0
    assert result["survived"] == 0
    assert result["score"] == 0.0


def test_parse_mutmut_results_empty_string() -> None:
    """Empty input should degrade to an empty parse result."""
    result = parse_mutmut_results("")

    assert result["killed"] == 0
    assert result["score"] == 0.0
