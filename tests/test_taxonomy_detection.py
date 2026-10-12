# LiveSpec traceability anchors
# @spec(AC-001)
# @spec(AC-002)
# @spec(AC-003)
# @spec(AC-004)
# @spec(AC-005)
# @spec(AC-006)
# @spec(AC-007)
# @spec(AC-008)
# @spec(AC-009)
# @spec(AC-010)
# @spec(AC-011)
# @spec(AC-012)
# @spec(AC-013)
# @spec(FR-001)
# @spec(FR-002)
# @spec(FR-003)
# @spec(FR-004)
# @spec(FR-005)
# @spec(FR-006)
# @spec(FR-007)
# @spec(FR-008)
# @spec(FR-011)

"""Tests for validator.taxonomy — detect_traits, load_taxonomy.

Coverage mapping per FR-008:
  - detection.feature    : 8 scenarios  - tests 1-8
  - ec-005-asymmetry     : fail-fast load errors (deduplicate_tests and the
    tautological graceful-degradation test were removed on 2026-10-12)

@spec FR-008 - .specs/features/006-taxonomy-testing-infra/spec.md#fr-008
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest

from validator.exceptions import TaxonomyLoadError
from validator.taxonomy import (
    _TAXONOMY_CACHE,  # type: ignore[reportPrivateUsage]
    Taxonomy,
    Trait,
    detect_traits,
    load_taxonomy,
)

# Real taxonomy path — used for structure and detection tests
_TAXONOMY_PATH = Path(__file__).parent.parent / "system" / "testing" / "ui-behavioral-taxonomy.md"


@pytest.fixture(autouse=True)
def clear_taxonomy_cache() -> Generator[None, None, None]:  # type: ignore[no-untyped-def]
    """Ensure each test starts with a clean cache (test isolation)."""
    _TAXONOMY_CACHE.clear()  # type: ignore[attr-defined]
    yield
    _TAXONOMY_CACHE.clear()  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# detection.feature — 8 tests
# ---------------------------------------------------------------------------


class TestLoadTaxonomyStructure:
    """detection.feature: load_taxonomy — parse and return taxonomy structure."""

    def test_load_taxonomy_returns_correct_counts(self) -> None:
        """Taxonomy loads with 22 traits and 6 transversal patterns. (AC-002, AC-004)"""
        taxonomy = load_taxonomy(_TAXONOMY_PATH)
        assert isinstance(taxonomy, Taxonomy)
        assert len(taxonomy.traits) == 22, (
            f"Expected 22 traits, got {len(taxonomy.traits)}: {[t.name for t in taxonomy.traits]}"
        )
        assert len(taxonomy.transversal_patterns) == 6, (
            f"Expected 6 transversal patterns, "
            f"got {len(taxonomy.transversal_patterns)}: "
            f"{[p.name for p in taxonomy.transversal_patterns]}"
        )

    def test_is_submittable_trait_has_required_fields(self) -> None:
        """is_submittable trait has name, description, signals, gherkin, patterns."""
        taxonomy = load_taxonomy(_TAXONOMY_PATH)
        trait = taxonomy.trait_by_name("is_submittable")
        assert trait is not None, "is_submittable trait not found"
        assert isinstance(trait, Trait)
        assert trait.name == "is_submittable"
        assert trait.description
        assert len(trait.detection_signals) > 0
        assert trait.gherkin_template
        assert len(trait.test_patterns) > 0


class TestDetectTraitsPositive:
    """detection.feature: true positives — traits correctly detected."""

    def test_form_signal_detects_is_submittable(self) -> None:
        """Unambiguous signal 'form' alone triggers is_submittable. (AC-004)"""
        result = detect_traits(["form"], path=_TAXONOMY_PATH)
        assert "is_submittable" in result

    def test_multiple_signals_detect_multiple_traits(self) -> None:
        """'form' + 'validation' detects is_submittable and has_validation."""
        result = detect_traits(["form", "validation"], path=_TAXONOMY_PATH)
        assert "is_submittable" in result
        assert "has_validation" in result

    def test_modal_detects_overlay_and_dismissible_via_co_occurrence(self) -> None:
        """'modal' + 'close button' detects has_overlay and dismissible_layer. (AC-007)

        Validates FR-004: co-occurrence rule auto-checks dismissible_layer
        when has_overlay is matched.
        """
        result = detect_traits(["modal", "close button"], path=_TAXONOMY_PATH)
        assert "has_overlay" in result
        assert "dismissible_layer" in result


class TestDetectTraitsNegative:
    """detection.feature: true negatives — EC-001 compliance."""

    def test_backend_context_no_injection(self) -> None:
        """Backend signals (no UI) do not inject any trait. (EC-001)"""
        result = detect_traits(
            ["submit", "analytics server", "backend"],
            path=_TAXONOMY_PATH,
        )
        assert result == set()

    def test_save_alone_no_injection(self) -> None:
        """Ambiguous signal 'save' alone returns empty set. (AC-005, EC-001)"""
        result = detect_traits(["save"], path=_TAXONOMY_PATH)
        assert result == set()

    def test_ambiguous_signal_with_ui_context_injects(self) -> None:
        """Ambiguous 'save' + UI context injects is_submittable. (AC-006)

        'preferences dialog' provides the second UI signal needed for 'save'.
        """
        result = detect_traits(["save", "preferences dialog"], path=_TAXONOMY_PATH)
        assert "is_submittable" in result


# ---------------------------------------------------------------------------
# @spec FR-011: 17 new detection tests
# .specs/features/005.2-taxonomy-complete-expansion/spec.md#fr-011
# ---------------------------------------------------------------------------


class TestNavigationTraits:
    """detection.feature: Navigation & Layout trait detection (FR-003)."""

    def test_detect_is_navigable_from_tabs(self) -> None:
        """Unambiguous signal 'tabs' detects is_navigable. (AC-005)"""
        result = detect_traits(["tabs"], path=_TAXONOMY_PATH)
        assert "is_navigable" in result

    def test_detect_is_navigable_from_pagination(self) -> None:
        """Unambiguous signal 'pagination' detects is_navigable. (AC-005)"""
        result = detect_traits(["pagination"], path=_TAXONOMY_PATH)
        assert "is_navigable" in result

    def test_detect_has_dropdown(self) -> None:
        """Unambiguous signal 'dropdown' detects has_dropdown."""
        result = detect_traits(["dropdown"], path=_TAXONOMY_PATH)
        assert "has_dropdown" in result

    def test_detect_is_collapsible(self) -> None:
        """Unambiguous signal 'accordion' detects is_collapsible."""
        result = detect_traits(["accordion"], path=_TAXONOMY_PATH)
        assert "is_collapsible" in result

    def test_detect_has_pagination(self) -> None:
        """Unambiguous signal 'load more' detects has_pagination."""
        result = detect_traits(["load more"], path=_TAXONOMY_PATH)
        assert "has_pagination" in result


class TestDataDisplayTraits:
    """detection.feature: Data Display trait detection (FR-004)."""

    def test_detect_is_sortable(self) -> None:
        """Unambiguous signal 'sortable' detects is_sortable. (AC-006)"""
        result = detect_traits(["sortable"], path=_TAXONOMY_PATH)
        assert "is_sortable" in result

    def test_detect_is_filterable(self) -> None:
        """Unambiguous signal 'faceted search' detects is_filterable."""
        result = detect_traits(["faceted search"], path=_TAXONOMY_PATH)
        assert "is_filterable" in result

    def test_detect_has_selection(self) -> None:
        """Unambiguous signal 'multi-select' detects has_selection."""
        result = detect_traits(["multi-select"], path=_TAXONOMY_PATH)
        assert "has_selection" in result


class TestUserFeedbackTraits:
    """detection.feature: User Feedback trait detection (FR-005)."""

    def test_detect_shows_notification(self) -> None:
        """Unambiguous signal 'toast' detects shows_notification. (AC-007)"""
        result = detect_traits(["toast"], path=_TAXONOMY_PATH)
        assert "shows_notification" in result

    def test_detect_has_confirmation(self) -> None:
        """Unambiguous signal 'confirmation' detects has_confirmation."""
        result = detect_traits(["confirmation"], path=_TAXONOMY_PATH)
        assert "has_confirmation" in result

    def test_detect_has_progress_indicator(self) -> None:
        """Unambiguous signal 'progress bar' detects has_progress_indicator."""
        result = detect_traits(["progress bar"], path=_TAXONOMY_PATH)
        assert "has_progress_indicator" in result

    def test_detect_has_tooltip(self) -> None:
        """Unambiguous signal 'tooltip' detects has_tooltip."""
        result = detect_traits(["tooltip"], path=_TAXONOMY_PATH)
        assert "has_tooltip" in result


class TestAdvancedInteractionTraits:
    """detection.feature: Advanced Interaction trait detection (FR-006)."""

    def test_detect_has_drag_drop(self) -> None:
        """Unambiguous signal 'drag-drop' detects has_drag_drop. (AC-008)"""
        result = detect_traits(["drag-drop"], path=_TAXONOMY_PATH)
        assert "has_drag_drop" in result

    def test_detect_has_dirty_state(self) -> None:
        """Unambiguous signal 'unsaved changes' detects has_dirty_state."""
        result = detect_traits(["unsaved changes"], path=_TAXONOMY_PATH)
        assert "has_dirty_state" in result

    def test_detect_is_optimistic(self) -> None:
        """Unambiguous signal 'optimistic update' detects is_optimistic."""
        result = detect_traits(["optimistic update"], path=_TAXONOMY_PATH)
        assert "is_optimistic" in result

    def test_detect_is_keyboard_navigable(self) -> None:
        """Unambiguous signal 'keyboard navigation' detects is_keyboard_navigable."""
        result = detect_traits(["keyboard navigation"], path=_TAXONOMY_PATH)
        assert "is_keyboard_navigable" in result


class TestSpecializedComponentTraits:
    """detection.feature: Specialized Component trait detection (FR-007)."""

    def test_detect_has_date_picker(self) -> None:
        """Unambiguous signal 'date picker' detects has_date_picker. (AC-009)"""
        result = detect_traits(["date picker"], path=_TAXONOMY_PATH)
        assert "has_date_picker" in result

    def test_detect_has_rich_text(self) -> None:
        """Unambiguous signal 'rich text' detects has_rich_text. (AC-010)"""
        result = detect_traits(["rich text"], path=_TAXONOMY_PATH)
        assert "has_rich_text" in result


# ---------------------------------------------------------------------------
# ec-005-asymmetry.feature — 2 tests (fail-fast side)
# ---------------------------------------------------------------------------


class TestEc005Asymmetry:
    """ec-005-asymmetry.feature: the parser fails fast; consumers own degradation."""

    def test_detect_traits_raises_taxonomy_load_error_on_missing_file(self, tmp_path: Path) -> None:
        """detect_traits raises TaxonomyLoadError when taxonomy file missing. (AC-008)"""
        missing = tmp_path / "nonexistent-taxonomy.md"
        with pytest.raises(TaxonomyLoadError):
            detect_traits(["form"], path=missing)

    def test_load_taxonomy_raises_with_path_in_message(self, tmp_path: Path) -> None:
        """load_taxonomy raises TaxonomyLoadError with file path in message. (AC-003)"""
        missing = tmp_path / "nonexistent-taxonomy.md"
        with pytest.raises(TaxonomyLoadError) as exc_info:
            load_taxonomy(missing)
        assert str(missing) in str(exc_info.value)
