"""Unit tests for slug normalization and NNN allocation."""

from __future__ import annotations

from pathlib import Path

import pytest

from validator.brainstorm.slug import (
    SlugEmptyError,
    allocate_nnn,
    normalize_slug,
)


def test_normalize_basic() -> None:
    assert normalize_slug("Login Flow") == "login-flow"


def test_normalize_french_accents() -> None:
    assert normalize_slug("Création de compte") == "creation-de-compte"


def test_normalize_unicode_emoji() -> None:
    assert normalize_slug("Hello 🌍 World") == "hello-world"


def test_normalize_leading_trailing_dash() -> None:
    assert normalize_slug("--login!--") == "login"


def test_normalize_empty_after_fold_raises() -> None:
    with pytest.raises(SlugEmptyError):
        normalize_slug("!!!")


def test_normalize_empty_input_raises() -> None:
    with pytest.raises(SlugEmptyError):
        normalize_slug("")


def test_allocate_no_existing() -> None:
    assert allocate_nnn([], ["b", "a"], None) == {"a": "001", "b": "002"}


def test_allocate_with_index_order() -> None:
    assert allocate_nnn([], ["a", "b"], ["b", "a"]) == {"b": "001", "a": "002"}


def test_allocate_skip_collisions() -> None:
    """Existing 001-foo, 002-bar — new slugs get 003+."""
    existing = [Path("001-foo"), Path("002-bar")]
    result = allocate_nnn(existing, ["baz"], None)
    assert result == {"baz": "003"}


def test_allocate_skip_existing_slugs() -> None:
    """Slug already in existing → not re-allocated."""
    existing = [Path("001-login")]
    result = allocate_nnn(existing, ["login", "checkout"], None)
    assert "login" not in result
    assert result["checkout"] == "002"
