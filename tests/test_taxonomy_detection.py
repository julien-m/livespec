"""Tests for validator.taxonomy — detect_traits, deduplicate_tests, load_taxonomy.

Coverage mapping per FR-008:
  - detection.feature    : 8 scenarios  - tests 1-8
  - deduplication.feature: 4 scenarios  - tests 9-12
  - ec-005-asymmetry     : 3 scenarios  - tests 13-15

@spec FR-008 - .specs/features/006-taxonomy-testing-infra/spec.md#fr-008
"""

from __future__ import annotations

import warnings
from collections.abc import Generator
from pathlib import Path

import pytest

from validator.exceptions import TaxonomyLoadError
from validator.taxonomy import (
    _TAXONOMY_CACHE,  # type: ignore[reportPrivateUsage]
    MergedTest,
    Taxonomy,
    Trait,
    deduplicate_tests,
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
        """Taxonomy loads with 5 traits and 3 transversal patterns. (AC-002)"""
        taxonomy = load_taxonomy(_TAXONOMY_PATH)
        assert isinstance(taxonomy, Taxonomy)
        assert len(taxonomy.traits) == 5, (
            f"Expected 5 traits, got {len(taxonomy.traits)}: "
            f"{[t.name for t in taxonomy.traits]}"
        )
        assert len(taxonomy.transversal_patterns) == 3, (
            f"Expected 3 transversal patterns, "
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
# deduplication.feature — 4 tests
# ---------------------------------------------------------------------------


class TestDeduplicateTests:
    """deduplication.feature: EC-002 overlap resolution and EC-004 deduplication."""

    def test_overlap_merges_to_single_test(self) -> None:
        """Overlapping AC and Behavioral AC merge into one MergedTest. (AC-009)"""
        result = deduplicate_tests(
            ac_list=["AC-003: formulaire bloque submit sans champs requis"],
            behavioral_ac_list=["is_submittable: submit avec champs vides doit être bloqué"],
        )
        assert len(result) == 1
        merged = result[0]
        assert isinstance(merged, MergedTest)
        assert "AC-003" in merged.ref
        assert "Behavioral-is_submittable" in merged.ref
        assert merged.ac_id == "AC-003"
        assert merged.behavioral_trait == "is_submittable"

    def test_no_overlap_produces_two_tests(self) -> None:
        """Non-overlapping AC and Behavioral AC produce separate MergedTests. (AC-010)"""
        result = deduplicate_tests(
            ac_list=["AC-001: le bouton est vert"],
            behavioral_ac_list=["is_submittable: submit avec données valides persiste"],
        )
        assert len(result) == 2
        refs = {r.ref for r in result}
        assert any("AC-001" in r for r in refs)
        assert any("Behavioral-is_submittable" in r for r in refs)

    def test_multiple_overlapping_pairs_merge_independently(self) -> None:
        """Multiple AC pairs each merge with their matching behavioral AC."""
        result = deduplicate_tests(
            ac_list=[
                "AC-001: le bouton affiche un spinner pendant le chargement",
                "AC-002: le formulaire bloque la soumission si les champs sont vides",
            ],
            behavioral_ac_list=[
                "async_action: loading state pendant l'opération asynchrone",
                "is_submittable: submit avec champs vides doit être bloqué",
            ],
        )
        assert len(result) == 2
        refs = {r.ref for r in result}
        assert any("AC-001" in r and "Behavioral-async_action" in r for r in refs)
        assert any("AC-002" in r and "Behavioral-is_submittable" in r for r in refs)

    def test_ec004_trait_deduplication(self) -> None:
        """EC-004: duplicate trait entries in behavioral_ac_list injected once. (AC-011)"""
        result = deduplicate_tests(
            ac_list=[],
            behavioral_ac_list=[
                "is_submittable: formulaire dans le modal",
                "is_submittable: submit via le bouton principal",
            ],
        )
        # is_submittable appears twice in input but must produce only 1 MergedTest
        submittable_refs = [r for r in result if r.behavioral_trait == "is_submittable"]
        assert len(submittable_refs) == 1, (
            f"Expected 1 is_submittable MergedTest, got {len(submittable_refs)}"
        )


# ---------------------------------------------------------------------------
# ec-005-asymmetry.feature — 3 tests
# ---------------------------------------------------------------------------


class TestEc005Asymmetry:
    """ec-005-asymmetry.feature: fail-fast vs degrade gracefully."""

    def test_detect_traits_raises_taxonomy_load_error_on_missing_file(
        self, tmp_path: Path
    ) -> None:
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

    def test_graceful_degradation_pattern(self, tmp_path: Path) -> None:
        """Callers can catch TaxonomyLoadError and degrade gracefully.

        Validates the /spec.implement and /spec.test degradation contract:
        catch TaxonomyLoadError → log WARNING → return empty result.
        """
        missing = tmp_path / "nonexistent-taxonomy.md"
        detected: set[str] = set()
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            try:
                detected = detect_traits(["form", "modal"], path=missing)
            except TaxonomyLoadError:
                warnings.warn(
                    "Behavioral taxonomy not found — behavioral TDD step will be skipped.",
                    stacklevel=1,
                )
                detected = set()

        assert detected == set(), "Graceful degradation must return empty set"
