"""Integration tests for Feature 007 — Structured Signal Extraction.

These tests validate the Phase 2 contract of the 3-phase pipeline:
given a fixed signal list (as would be extracted by Phase 1 LLM call),
detect_traits() returns the correct deterministic trait set.

@spec FR-005, FR-006 — .specs/features/007-structured-signal-extraction/spec.md
"""

from __future__ import annotations

from pathlib import Path

import pytest

from validator.taxonomy import (
    _TAXONOMY_CACHE,  # type: ignore[reportPrivateUsage]
    detect_traits,
)

_TAXONOMY_PATH = (
    Path(__file__).parent.parent / "system" / "testing" / "ui-behavioral-taxonomy.md"
)


@pytest.fixture(autouse=True)
def clear_cache() -> None:  # type: ignore[misc]
    """Ensure each test starts with a clean taxonomy cache."""
    _TAXONOMY_CACHE.clear()  # type: ignore[attr-defined]
    yield  # type: ignore[misc]
    _TAXONOMY_CACHE.clear()  # type: ignore[attr-defined]


def test_form_submit_signals_detect_is_submittable() -> None:
    """AC-005: signals ["form", "submit button"] -> is_submittable trait."""
    result = detect_traits(["form", "submit button"], path=_TAXONOMY_PATH)
    assert "is_submittable" in result


def test_modal_close_signals_detect_overlay_and_dismissible() -> None:
    """AC-006: signals ["modal", "close button"] -> has_overlay + dismissible_layer."""
    result = detect_traits(["modal", "close button"], path=_TAXONOMY_PATH)
    assert "has_overlay" in result
    assert "dismissible_layer" in result


def test_empty_signals_produce_no_traits() -> None:
    """AC-007: empty signal list -> empty trait set (Phase 1 returns [] for non-UI)."""
    result = detect_traits([], path=_TAXONOMY_PATH)
    assert result == set()


def test_ambiguous_save_signal_alone_produces_no_traits() -> None:
    """AC-008: ambiguous signal ["save"] alone -> empty set (EC-001 preserved)."""
    result = detect_traits(["save"], path=_TAXONOMY_PATH)
    assert result == set()


def test_duplicate_signals_normalized_double() -> None:
    """AC-010: detect_traits(["form", "form"]) == detect_traits(["form"]) — EC-003."""
    result_dup = detect_traits(["form", "form"], path=_TAXONOMY_PATH)
    result_single = detect_traits(["form"], path=_TAXONOMY_PATH)
    assert result_dup == result_single


def test_duplicate_signals_normalized_triple() -> None:
    """AC-010: detect_traits(["form","form","form"]) == detect_traits(["form"]).

    Rules out frequency-dependent behavior in detect_traits().
    """
    result_triple = detect_traits(["form", "form", "form"], path=_TAXONOMY_PATH)
    result_single = detect_traits(["form"], path=_TAXONOMY_PATH)
    assert result_triple == result_single
