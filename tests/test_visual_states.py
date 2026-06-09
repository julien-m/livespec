# LiveSpec traceability anchors
# @spec(AC-001)
# @spec(AC-013)
# @spec(AC-014)
# @spec(FR-008)

"""Tests for VisualState parsing in validator/taxonomy.py.

@spec FR-001, FR-002: Visual state taxonomy and parsing
— .specs/features/009-visual-state-baselines/spec.md#fr-001
"""

from __future__ import annotations

import subprocess
from collections.abc import Generator
from pathlib import Path

import pytest

from validator.taxonomy import (
    _TAXONOMY_CACHE,  # type: ignore[reportPrivateUsage]
    Trait,
    VisualState,
    check_duplicate_screenshots,
    load_taxonomy,
)

# Real taxonomy path — used for structure and detection tests
_TAXONOMY_PATH = Path(__file__).parent.parent / "system" / "testing" / "ui-behavioral-taxonomy.md"


@pytest.fixture(autouse=True)
def clear_taxonomy_cache() -> Generator[None, None, None]:
    """Ensure each test starts with a clean cache (test isolation)."""
    _TAXONOMY_CACHE.clear()  # type: ignore[attr-defined]
    yield
    _TAXONOMY_CACHE.clear()  # type: ignore[attr-defined]


class TestVisualStateParsing:
    """Tests for VisualState parsing from the real taxonomy document."""

    def test_visual_states_parsed_from_taxonomy(self) -> None:
        """Load the real taxonomy and assert traits with visual states have >= 2 states."""
        # Traits documented as having visual states (5 core + 6 from 005.2 expansion)
        traits_with_visual_states = {
            "is_submittable",
            "async_action",
            "has_overlay",
            "dismissible_layer",
            "has_validation",
            "is_navigable",
            "is_sortable",
            "shows_notification",
            "has_drag_drop",
            "has_date_picker",
        }
        taxonomy = load_taxonomy(_TAXONOMY_PATH)
        for trait in taxonomy.traits:
            if trait.name in traits_with_visual_states:
                assert len(trait.visual_states) >= 2, (
                    f"Trait '{trait.name}' has {len(trait.visual_states)} visual states, "
                    f"expected at least 2"
                )

    def test_visual_state_fields(self) -> None:
        """Assert VisualState has state_id: str, css_attributes: list[str], screenshot: str."""
        vs = VisualState(state_id="test", css_attributes=["a", "b"], screenshot="test.png")
        assert isinstance(vs.state_id, str)
        assert isinstance(vs.css_attributes, list)
        assert all(isinstance(a, str) for a in vs.css_attributes)
        assert isinstance(vs.screenshot, str)

    def test_is_submittable_has_disabled_enabled_loading(self) -> None:
        """Assert exactly 3 states: disabled, enabled, loading for is_submittable."""
        taxonomy = load_taxonomy(_TAXONOMY_PATH)
        trait = taxonomy.trait_by_name("is_submittable")
        assert trait is not None
        state_ids = [vs.state_id for vs in trait.visual_states]
        assert state_ids == ["disabled", "enabled", "loading"]

    def test_css_attributes_parsed_as_list(self) -> None:
        """Assert backtick-wrapped CSS values are separate list items."""
        taxonomy = load_taxonomy(_TAXONOMY_PATH)
        trait = taxonomy.trait_by_name("is_submittable")
        assert trait is not None
        disabled = next(vs for vs in trait.visual_states if vs.state_id == "disabled")
        assert "[disabled]" in disabled.css_attributes
        assert ".btn-disabled" in disabled.css_attributes
        assert 'aria-disabled="true"' in disabled.css_attributes

    def test_missing_visual_states_table_returns_empty_list(self) -> None:
        """A Trait without visual states in the doc should parse with empty list."""
        # Create a minimal trait manually — no visual states
        trait = Trait(name="test_trait", description="No visual states")
        assert trait.visual_states == []

    def test_duplicate_screenshot_detection(self) -> None:
        """Two VisualStates with same screenshot produce a warning."""
        trait = Trait(
            name="test_trait",
            description="test",
            visual_states=[
                VisualState(state_id="a", css_attributes=[], screenshot="same.png"),
                VisualState(state_id="b", css_attributes=[], screenshot="same.png"),
            ],
        )
        warnings = check_duplicate_screenshots(trait)
        assert len(warnings) == 1
        assert "same.png" in warnings[0]
        assert "'a'" in warnings[0]
        assert "'b'" in warnings[0]

    def test_all_five_traits_have_visual_states(self) -> None:
        """After reading the taxonomy, all 5 trait names are present with visual states."""
        taxonomy = load_taxonomy(_TAXONOMY_PATH)
        expected_traits = [
            "is_submittable",
            "async_action",
            "has_overlay",
            "dismissible_layer",
            "has_validation",
        ]
        trait_names = [t.name for t in taxonomy.traits]
        for name in expected_traits:
            assert name in trait_names, f"Trait '{name}' not found in taxonomy"
            trait = taxonomy.trait_by_name(name)
            assert trait is not None
            assert len(trait.visual_states) > 0, f"Trait '{name}' has no visual states"

    def test_visual_state_screenshot_not_empty(self) -> None:
        """All visual states have non-empty screenshot fields."""
        taxonomy = load_taxonomy(_TAXONOMY_PATH)
        for trait in taxonomy.traits:
            for vs in trait.visual_states:
                assert vs.screenshot, (
                    f"Empty screenshot for state '{vs.state_id}' in trait '{trait.name}'"
                )

    def test_visual_state_css_attributes_not_empty(self) -> None:
        """For states with known CSS (not 'none'), list is non-empty."""
        taxonomy = load_taxonomy(_TAXONOMY_PATH)
        for trait in taxonomy.traits:
            for vs in trait.visual_states:
                # The async_action 'idle' state has "(none)" CSS
                if vs.state_id == "idle" and trait.name == "async_action":
                    # This state explicitly has no CSS attributes
                    continue
                assert len(vs.css_attributes) > 0, (
                    f"Empty css_attributes for state '{vs.state_id}' in trait '{trait.name}'"
                )

    def test_taxonomy_hash_computable(self) -> None:
        """git hash-object on the taxonomy returns a non-empty string."""
        try:
            result = subprocess.run(
                ["git", "hash-object", str(_TAXONOMY_PATH)],
                capture_output=True,
                text=True,
                check=True,
            )
            assert result.stdout.strip(), "git hash-object returned empty string"
            assert len(result.stdout.strip()) == 40, "Expected 40-char SHA1 hash"
        except FileNotFoundError:
            pytest.skip("git not available")


class TestAsyncActionStates:
    """Verify async_action trait has expected 4 visual states."""

    def test_async_action_has_four_states(self) -> None:
        taxonomy = load_taxonomy(_TAXONOMY_PATH)
        trait = taxonomy.trait_by_name("async_action")
        assert trait is not None
        state_ids = [vs.state_id for vs in trait.visual_states]
        assert state_ids == ["idle", "loading", "error", "success"]


class TestHasOverlayStates:
    """Verify has_overlay trait has expected 3 visual states."""

    def test_has_overlay_has_three_states(self) -> None:
        taxonomy = load_taxonomy(_TAXONOMY_PATH)
        trait = taxonomy.trait_by_name("has_overlay")
        assert trait is not None
        state_ids = [vs.state_id for vs in trait.visual_states]
        assert state_ids == ["closed", "open", "focused"]


class TestDismissibleLayerStates:
    """Verify dismissible_layer trait has expected 3 visual states."""

    def test_dismissible_layer_has_three_states(self) -> None:
        taxonomy = load_taxonomy(_TAXONOMY_PATH)
        trait = taxonomy.trait_by_name("dismissible_layer")
        assert trait is not None
        state_ids = [vs.state_id for vs in trait.visual_states]
        assert state_ids == ["open", "closing", "closed"]


class TestHasValidationStates:
    """Verify has_validation trait has expected 3 visual states."""

    def test_has_validation_has_three_states(self) -> None:
        taxonomy = load_taxonomy(_TAXONOMY_PATH)
        trait = taxonomy.trait_by_name("has_validation")
        assert trait is not None
        state_ids = [vs.state_id for vs in trait.visual_states]
        assert state_ids == ["valid", "invalid", "empty"]
