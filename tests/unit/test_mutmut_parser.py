# @spec FR-007: Unit tests for mutmut parser — .specs/features/017-driver-python/spec.md#fr-007
"""
Unit tests for mutmut result parsing and mutation score computation.
"""

import json

import pytest

from validator.drivers.mutmut_parser import (
    compute_mutation_score,
    parse_mutmut_results,
)


def test_compute_mutation_score_basic():
    """Test mutation score calculation."""
    # 80% killed (8 out of 10)
    score = compute_mutation_score(killed=8, survived=2)
    assert score == 80.0


def test_compute_mutation_score_perfect():
    """Test mutation score when all mutants are killed."""
    score = compute_mutation_score(killed=10, survived=0)
    assert score == 100.0


def test_compute_mutation_score_none_killed():
    """Test mutation score when no mutants are killed."""
    score = compute_mutation_score(killed=0, survived=10)
    assert score == 0.0


def test_compute_mutation_score_no_mutants():
    """Test mutation score when there are no mutants."""
    score = compute_mutation_score(killed=0, survived=0)
    assert score == 0.0


def test_parse_mutmut_results_from_json():
    """Test parsing mutmut results from JSON output."""
    json_output = json.dumps(
        {
            "killed": 15,
            "survived": 5,
            "timeout": 1,
        }
    )

    result = parse_mutmut_results(json_output)

    assert result["killed"] == 15
    assert result["survived"] == 5
    assert result["timeout"] == 1
    assert result["score"] == 75.0  # 15 / (15 + 5) * 100


def test_parse_mutmut_results_invalid_json():
    """Test graceful handling of invalid JSON."""
    result = parse_mutmut_results("invalid json {{{")

    assert result["killed"] == 0
    assert result["survived"] == 0
    assert result["score"] == 0.0


def test_parse_mutmut_results_empty_string():
    """Test graceful handling of empty JSON output."""
    result = parse_mutmut_results("")

    assert result["killed"] == 0
    assert result["score"] == 0.0
