# LiveSpec traceability anchors
# @spec(FR-005)

"""Unit tests for the cargo-mutants JSON parser."""

# @spec FR-005: Unit tests for the cargo-mutants JSON parser
# — .specs/features/021-driver-rust/spec.md#fr-005

from __future__ import annotations

import json

from validator.drivers.rust_detector import parse_cargo_mutants_json

# ---------------------------------------------------------------------------
# parse_cargo_mutants_json
# ---------------------------------------------------------------------------


def test_parse_cargo_mutants_json_extracts_summary_object() -> None:
    """A single-object summary yields the expected counts."""
    # @spec FR-003, AC-008
    payload = json.dumps({"caught": 12, "missed": 3, "timeout": 1, "unviable": 0})

    counts = parse_cargo_mutants_json(payload)

    assert counts == {"caught": 12, "missed": 3, "timeout": 1, "unviable": 0}


def test_parse_cargo_mutants_json_supports_nested_outcomes() -> None:
    """Nested ``outcomes`` / ``summary`` shapes are also recognised."""
    payload = json.dumps(
        {
            "version": "24.4.0",
            "outcomes": {"caught": 5, "missed": 2, "timeout": 0, "unviable": 1},
        }
    )

    counts = parse_cargo_mutants_json(payload)

    assert counts == {"caught": 5, "missed": 2, "timeout": 0, "unviable": 1}


def test_parse_cargo_mutants_json_aggregates_per_mutant_lines() -> None:
    """Line-delimited per-mutant events are aggregated by ``outcome``."""
    payload = "\n".join(
        [
            json.dumps({"mutant": "m1", "outcome": "caught"}),
            json.dumps({"mutant": "m2", "outcome": "caught"}),
            json.dumps({"mutant": "m3", "outcome": "missed"}),
            json.dumps({"mutant": "m4", "outcome": "timeout"}),
            json.dumps({"mutant": "m5", "outcome": "unviable"}),
        ]
    )

    counts = parse_cargo_mutants_json(payload)

    assert counts == {"caught": 2, "missed": 1, "timeout": 1, "unviable": 1}


def test_parse_cargo_mutants_json_zero_fills_missing_keys() -> None:
    """Absent outcome keys default to zero."""
    payload = json.dumps({"caught": 10})

    counts = parse_cargo_mutants_json(payload)

    assert counts == {"caught": 10, "missed": 0, "timeout": 0, "unviable": 0}


def test_parse_cargo_mutants_json_malformed_returns_zeros() -> None:
    """Garbage input yields all-zero counts (no raise)."""
    counts = parse_cargo_mutants_json("not json at all { [ ")

    assert counts == {"caught": 0, "missed": 0, "timeout": 0, "unviable": 0}


def test_parse_cargo_mutants_json_empty_returns_zeros() -> None:
    """Empty stdout yields all-zero counts."""
    counts = parse_cargo_mutants_json("")

    assert counts == {"caught": 0, "missed": 0, "timeout": 0, "unviable": 0}


def test_parse_cargo_mutants_json_ignores_unknown_outcome_strings() -> None:
    """Unknown outcome labels are silently ignored."""
    payload = "\n".join(
        [
            json.dumps({"outcome": "caught"}),
            json.dumps({"outcome": "totally-unknown"}),
            json.dumps({"outcome": "missed"}),
        ]
    )

    counts = parse_cargo_mutants_json(payload)

    assert counts == {"caught": 1, "missed": 1, "timeout": 0, "unviable": 0}
