# LiveSpec traceability anchors
# @spec(FR-006)

"""Unit tests for Stryker mutation report parsing."""

# @spec FR-006: Unit tests for Stryker parser
# — .specs/features/018-driver-typescript-javascript/spec.md#fr-006

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from validator.drivers.stryker_parser import (
    compute_kill_rate,
    load_stryker_report,
    parse_stryker_report,
)


def test_compute_kill_rate_basic() -> None:
    """Kill rate reflects (killed + timeout) over total mutants."""
    # @spec AC-010 — .specs/features/018-driver-typescript-javascript/spec.md#ac-010
    assert compute_kill_rate(killed=8, survived=2, timeout=0) == 80.0


def test_compute_kill_rate_perfect() -> None:
    """All killed mutants yield a 100% rate."""
    assert compute_kill_rate(killed=10, survived=0, timeout=0) == 100.0


def test_compute_kill_rate_no_mutants() -> None:
    """Zero mutants returns 0.0 instead of dividing by zero."""
    assert compute_kill_rate(killed=0, survived=0, timeout=0) == 0.0


def test_compute_kill_rate_includes_timeout_as_killed() -> None:
    """Timeouts are credited as kills (Stryker convention)."""
    rate = compute_kill_rate(killed=5, survived=0, timeout=5)
    assert rate == 100.0


def test_parse_stryker_report_files_shape() -> None:
    """The standard ``files.<path>.mutants[]`` shape is aggregated correctly."""
    payload = {
        "files": {
            "src/foo.ts": {
                "mutants": [
                    {"status": "Killed"},
                    {"status": "Killed"},
                    {"status": "Survived"},
                ],
            },
            "src/bar.ts": {
                "mutants": [
                    {"status": "Timeout"},
                    {"status": "NoCoverage"},
                ],
            },
        },
    }
    result = parse_stryker_report(json.dumps(payload))

    assert result["killed"] == 2
    assert result["survived"] == 1
    assert result["timeout"] == 1
    assert result["no_coverage"] == 1
    # killed+timeout=3, survived=1, timeout=1 -> total 4 -> 75.0
    assert result["kill_rate"] == 75.0


def test_parse_stryker_report_metrics_shape() -> None:
    """Reports using only the ``metrics`` block are also supported."""
    payload = {
        "metrics": {
            "killed": 12,
            "survived": 3,
            "timeout": 0,
            "noCoverage": 1,
        },
    }
    result = parse_stryker_report(json.dumps(payload))

    assert result["killed"] == 12
    assert result["survived"] == 3
    assert result["timeout"] == 0
    assert result["no_coverage"] == 1
    assert result["kill_rate"] == 80.0


def test_parse_stryker_report_invalid_json() -> None:
    """Malformed JSON degrades to an empty result."""
    result = parse_stryker_report("not json {{{")

    assert result["killed"] == 0
    assert result["survived"] == 0
    assert result["kill_rate"] == 0.0


def test_parse_stryker_report_none_input() -> None:
    """``None`` input returns the empty result without raising."""
    result = parse_stryker_report(None)

    assert result["killed"] == 0
    assert result["kill_rate"] == 0.0


def test_parse_stryker_report_unrecognized_shape() -> None:
    """A JSON document with neither ``files`` nor ``metrics`` is empty."""
    result = parse_stryker_report(json.dumps({"other": "shape"}))

    assert result == {
        "killed": 0,
        "survived": 0,
        "timeout": 0,
        "no_coverage": 0,
        "kill_rate": 0.0,
    }


def test_load_stryker_report_missing_file() -> None:
    """A missing report file yields the empty result instead of raising."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = load_stryker_report(Path(tmpdir) / "does-not-exist.json")

    assert result["killed"] == 0
    assert result["kill_rate"] == 0.0


def test_load_stryker_report_reads_disk() -> None:
    """A real report file on disk is parsed end-to-end."""
    payload = {
        "metrics": {"killed": 4, "survived": 1, "timeout": 0, "noCoverage": 0},
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        report_path = Path(tmpdir) / "mutation.json"
        report_path.write_text(json.dumps(payload), encoding="utf-8")

        result = load_stryker_report(report_path)

    assert result["killed"] == 4
    assert result["survived"] == 1
    assert result["kill_rate"] == 80.0
