"""Tests for validator.identity (Chantier 4 / Feature 013, FR-001/002/009)."""

from __future__ import annotations

from pathlib import Path

import pytest

from validator.identity import (
    PLACEHOLDER_LITERAL,
    SLUG_REGEX,
    FeatureSlug,
    IdentityResolutionError,
    assert_resolved,
    parse_slug,
    resolve_feature_slug,
)


class TestParseSlug:
    """parse_slug accepts canonical NNN-name slugs and rejects everything else."""

    def test_accepts_canonical_slug(self) -> None:
        slug = parse_slug("013-state-model-identity-resolution")
        assert isinstance(slug, FeatureSlug)
        assert slug.nnn == "013"
        assert slug.name == "state-model-identity-resolution"
        assert slug.full == "013-state-model-identity-resolution"

    def test_accepts_minimal_slug(self) -> None:
        slug = parse_slug("001-foo")
        assert slug.nnn == "001"
        assert slug.name == "foo"

    def test_rejects_placeholder_literal(self) -> None:
        with pytest.raises(IdentityResolutionError, match="literal placeholder"):
            parse_slug(PLACEHOLDER_LITERAL)

    def test_rejects_empty(self) -> None:
        with pytest.raises(IdentityResolutionError, match="canonical regex"):
            parse_slug("")

    @pytest.mark.parametrize(
        "bad_slug",
        [
            "13-foo",  # NNN not zero-padded
            "0013-foo",  # too many digits
            "013_foo",  # underscore not hyphen
            "013-Foo",  # uppercase
            "013-foo-",  # trailing hyphen
            "-013-foo",  # leading hyphen
            "abc-foo",  # non-digit prefix
            "013",  # missing name
        ],
    )
    def test_rejects_malformed(self, bad_slug: str) -> None:
        with pytest.raises(IdentityResolutionError):
            parse_slug(bad_slug)


class TestResolveFeatureSlug:
    """resolve_feature_slug handles both pre-resolved slugs and free-text descriptions."""

    def test_passthrough_for_valid_slug(self) -> None:
        slug = resolve_feature_slug("013-state-model-identity-resolution")
        assert slug.full == "013-state-model-identity-resolution"

    def test_allocates_first_nnn_in_empty_specs(self, tmp_path: Path) -> None:
        specs = tmp_path / ".specs"
        specs.mkdir()
        slug = resolve_feature_slug("Add user search", specs_root=specs)
        assert slug.nnn == "001"
        assert slug.name == "add-user-search"
        assert slug.full == "001-add-user-search"

    def test_increments_nnn_past_existing_features(self, tmp_path: Path) -> None:
        specs = tmp_path / ".specs"
        (specs / "features").mkdir(parents=True)
        for n in ("001-foo", "002-bar", "005-baz"):
            (specs / "features" / n).mkdir()
        slug = resolve_feature_slug("Real-time notifications", specs_root=specs)
        assert slug.nnn == "006"
        assert slug.name == "real-time-notifications"

    def test_strips_special_chars_from_description(self, tmp_path: Path) -> None:
        specs = tmp_path / ".specs"
        specs.mkdir()
        slug = resolve_feature_slug("CSV / PDF export!", specs_root=specs)
        assert slug.name == "csv-pdf-export"

    def test_truncates_long_description(self, tmp_path: Path) -> None:
        specs = tmp_path / ".specs"
        specs.mkdir()
        long_desc = "a" * 200
        slug = resolve_feature_slug(long_desc, specs_root=specs)
        assert len(slug.name) <= 60

    def test_rejects_placeholder_literal(self) -> None:
        with pytest.raises(IdentityResolutionError, match="literal placeholder"):
            resolve_feature_slug(PLACEHOLDER_LITERAL)

    def test_rejects_empty_input(self) -> None:
        with pytest.raises(IdentityResolutionError, match="non-empty"):
            resolve_feature_slug("")

    def test_rejects_whitespace_only(self) -> None:
        with pytest.raises(IdentityResolutionError, match="non-empty"):
            resolve_feature_slug("   ")

    def test_rejects_description_that_slugifies_to_empty(self, tmp_path: Path) -> None:
        specs = tmp_path / ".specs"
        specs.mkdir()
        with pytest.raises(IdentityResolutionError, match="empty slug"):
            resolve_feature_slug("!!!", specs_root=specs)


class TestAssertResolved:
    """assert_resolved is a guard that raises IdentityResolutionError on bad input."""

    def test_passes_for_valid_slug(self) -> None:
        assert_resolved("013-foo")  # no exception

    def test_raises_on_placeholder(self) -> None:
        with pytest.raises(IdentityResolutionError):
            assert_resolved(PLACEHOLDER_LITERAL)

    def test_raises_on_empty(self) -> None:
        with pytest.raises(IdentityResolutionError):
            assert_resolved("")


class TestSlugRegex:
    """The canonical regex is documented in system/identity.md and used by validators."""

    def test_regex_pattern_matches_documentation(self) -> None:
        # If this test breaks, system/identity.md must be updated to match.
        assert SLUG_REGEX.pattern == r"^\d{3}(\.\d+)?-[a-z0-9]+(-[a-z0-9]+)*$"

    def test_regex_accepts_subfeatures(self) -> None:
        # Sub-features (NNN.M-name) are a real LiveSpec convention — see
        # .specs/features/005.1-behavioral-tdd-audit/ for example.
        assert SLUG_REGEX.match("005.1-behavioral-tdd-audit") is not None
        assert SLUG_REGEX.match("005.2-taxonomy-complete-expansion") is not None
        # But malformed sub-numbers are still rejected
        assert SLUG_REGEX.match("005.-foo") is None
        assert SLUG_REGEX.match("005.a-foo") is None

    def test_regex_rejects_placeholder(self) -> None:
        # The placeholder uses alphabetic 'NNN', not digits, so the regex naturally rejects it.
        assert SLUG_REGEX.match(PLACEHOLDER_LITERAL) is None

    def test_spec_check_contract_uses_subfeature_regex(self) -> None:
        """Spec-check and activation docs use the canonical sub-feature regex."""
        repo_root = Path(__file__).resolve().parents[1]
        spec_check = repo_root / ".agent-sync" / "skills" / "spec-check" / "SKILL.md"
        activation_contract = repo_root / "system" / "activation-contract.md"

        assert SLUG_REGEX.pattern in spec_check.read_text(encoding="utf-8")
        assert "005.1-behavioral-tdd-audit" in spec_check.read_text(encoding="utf-8")
        assert SLUG_REGEX.pattern in activation_contract.read_text(encoding="utf-8")
