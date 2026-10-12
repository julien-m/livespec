# LiveSpec traceability anchors
# @spec(FR-006)

"""Unit tests for pitest XML parsing."""

# @spec FR-006: Unit tests for the pitest XML parser
# — .specs/features/022-driver-jvm/spec.md#fr-006

from __future__ import annotations

from validator.drivers.jvm_detector import parse_pitest_xml

_PITEST_XML = """<?xml version="1.0" encoding="UTF-8"?>
<mutations>
    <mutation detected="true" status="KILLED" numberOfTestsRun="3">
        <sourceFile>Foo.java</sourceFile>
    </mutation>
    <mutation detected="false" status="SURVIVED" numberOfTestsRun="2">
        <sourceFile>Foo.java</sourceFile>
    </mutation>
    <mutation detected="false" status="SURVIVED" numberOfTestsRun="2">
        <sourceFile>Bar.java</sourceFile>
    </mutation>
    <mutation detected="false" status="TIMED_OUT" numberOfTestsRun="1">
        <sourceFile>Bar.java</sourceFile>
    </mutation>
    <mutation detected="false" status="NO_COVERAGE" numberOfTestsRun="0">
        <sourceFile>Bar.java</sourceFile>
    </mutation>
</mutations>
"""


# ---------------------------------------------------------------------------
# parse_pitest_xml
# ---------------------------------------------------------------------------


def test_parse_pitest_xml_extracts_counts() -> None:
    """KILLED / SURVIVED / TIMED_OUT / NO_COVERAGE counts are extracted."""
    # @spec FR-004, AC-008, SC-004
    counts = parse_pitest_xml(_PITEST_XML)

    assert counts["killed"] == 1
    assert counts["survived"] == 2
    assert counts["timed_out"] == 1
    assert counts["no_coverage"] == 1
    # Other statuses are zero-filled.
    assert counts["memory_error"] == 0
    assert counts["run_error"] == 0


def test_parse_pitest_xml_zero_fills_missing_statuses() -> None:
    """Statuses not present in the XML default to zero."""
    # @spec FR-004
    payload = """<?xml version="1.0"?>
<mutations>
    <mutation status="KILLED"/>
</mutations>
"""

    counts = parse_pitest_xml(payload)

    assert counts == {
        "killed": 1,
        "survived": 0,
        "timed_out": 0,
        "no_coverage": 0,
        "memory_error": 0,
        "run_error": 0,
    }


def test_parse_pitest_xml_handles_lowercase_status() -> None:
    """Status strings are normalised case-insensitively."""
    # @spec SC-004 — handle KILLED and SURVIVED in any case
    payload = """<?xml version="1.0"?>
<mutations>
    <mutation status="killed"/>
    <mutation status="Survived"/>
    <mutation status="TIMED_OUT"/>
</mutations>
"""

    counts = parse_pitest_xml(payload)

    assert counts["killed"] == 1
    assert counts["survived"] == 1
    assert counts["timed_out"] == 1


def test_parse_pitest_xml_malformed_returns_zeros() -> None:
    """Garbage input that doesn't look like XML yields all-zero counts."""
    counts = parse_pitest_xml("not xml at all { just text }")

    assert counts == {
        "killed": 0,
        "survived": 0,
        "timed_out": 0,
        "no_coverage": 0,
        "memory_error": 0,
        "run_error": 0,
    }


def test_parse_pitest_xml_empty_returns_zeros() -> None:
    """Empty input yields all-zero counts."""
    counts = parse_pitest_xml("")

    assert all(v == 0 for v in counts.values())


def test_parse_pitest_xml_ignores_unknown_statuses() -> None:
    """Unknown status strings are silently ignored."""
    payload = """<?xml version="1.0"?>
<mutations>
    <mutation status="KILLED"/>
    <mutation status="TOTALLY_UNKNOWN"/>
    <mutation status="SURVIVED"/>
</mutations>
"""

    counts = parse_pitest_xml(payload)

    assert counts["killed"] == 1
    assert counts["survived"] == 1


def test_parse_pitest_xml_ignores_mutation_without_status_attribute() -> None:
    """Mutation elements lacking a ``status`` attribute are skipped."""
    payload = """<?xml version="1.0"?>
<mutations>
    <mutation status="KILLED"/>
    <mutation/>
</mutations>
"""

    counts = parse_pitest_xml(payload)

    assert counts["killed"] == 1
