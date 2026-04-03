"""Tests for validator.semantic.embeddings — cosine distance, section extraction, embedding stub."""

from __future__ import annotations

import pytest

from validator.semantic.embeddings import (
    compute_embedding,
    cosine_distance,
    extract_sections,
)


class TestCosineDistance:
    """Cosine distance computation with known vectors."""

    def test_identical_vectors(self) -> None:
        v = [1.0, 2.0, 3.0]
        assert cosine_distance(v, v) == pytest.approx(0.0, abs=1e-9)

    def test_orthogonal_vectors(self) -> None:
        u = [1.0, 0.0, 0.0]
        v = [0.0, 1.0, 0.0]
        assert cosine_distance(u, v) == pytest.approx(1.0, abs=1e-9)

    def test_opposite_vectors(self) -> None:
        u = [1.0, 0.0]
        v = [-1.0, 0.0]
        assert cosine_distance(u, v) == pytest.approx(2.0, abs=1e-9)

    def test_similar_vectors(self) -> None:
        u = [1.0, 1.0, 0.0]
        v = [1.0, 0.0, 0.0]
        dist = cosine_distance(u, v)
        # cos(45 degrees) = 0.707..., distance = 1 - 0.707 ~ 0.293
        assert 0.2 < dist < 0.4

    def test_dimension_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="dimension mismatch"):
            cosine_distance([1.0, 2.0], [1.0, 2.0, 3.0])

    def test_zero_vector_returns_one(self) -> None:
        assert cosine_distance([0.0, 0.0], [1.0, 2.0]) == pytest.approx(1.0)

    def test_high_dimensional(self) -> None:
        """Test with 1536-dim vectors (embedding dimension)."""
        u = [1.0] * 1536
        v = [1.0] * 1536
        assert cosine_distance(u, v) == pytest.approx(0.0, abs=1e-9)


class TestExtractSections:
    """Section extraction from spec markdown content."""

    def test_extracts_user_stories(self) -> None:
        content = """## User Stories

As a user, I want to log in so that I can access my account.

## Acceptance Criteria

AC-1: Login works.
"""
        sections = extract_sections(content)
        assert "user-stories" in sections
        assert "log in" in sections["user-stories"]

    def test_extracts_acceptance_criteria(self) -> None:
        content = """## Acceptance Criteria

AC-1: User can authenticate via email/password.
AC-2: User receives error on invalid credentials.

## Functional Requirements

FR-1: POST /login endpoint.
"""
        sections = extract_sections(content)
        assert "acceptance-criteria" in sections
        assert "AC-1" in sections["acceptance-criteria"]

    def test_extracts_functional_requirements(self) -> None:
        content = """## Functional Requirements

FR-1: Implement JWT-based authentication.
FR-2: Hash passwords with bcrypt.
"""
        sections = extract_sections(content)
        assert "functional-requirements" in sections
        assert "FR-1" in sections["functional-requirements"]

    def test_empty_content_returns_empty(self) -> None:
        sections = extract_sections("")
        assert sections == {}

    def test_no_matching_sections(self) -> None:
        content = """## Overview

This is a general overview.

## Notes

Some notes here.
"""
        sections = extract_sections(content)
        assert sections == {}

    def test_case_insensitive(self) -> None:
        content = """## user stories

As a user, I want to do something.

## Other
"""
        sections = extract_sections(content)
        assert "user-stories" in sections


class TestComputeEmbedding:
    """compute_embedding raises NotImplementedError (stub)."""

    def test_raises_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError, match="Embedding API not configured"):
            compute_embedding("hello world", "text-embedding-3-small")
