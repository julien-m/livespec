"""Tests for validator.schemas — Pydantic frontmatter schemas."""

from __future__ import annotations

from datetime import date
from typing import get_args

import pytest
from pydantic import ValidationError

from validator.schemas import get_schema
from validator.schemas.implementation import ImplementationFrontmatter
from validator.schemas.plan import PlanFrontmatter
from validator.schemas.spec import SpecFrontmatter
from validator.schemas.stack import StackFrontmatter


class TestSpecFrontmatter:
    """SpecFrontmatter validation."""

    def test_valid_data(self) -> None:
        s = SpecFrontmatter(
            title="Auth Feature",
            status="Draft",
            priority="P1",
            created=date(2026, 1, 1),
            updated=date(2026, 1, 15),
        )
        assert s.title == "Auth Feature"
        assert s.status == "Draft"

    @pytest.mark.parametrize("status", ["WIP", "", "planned", "InProgress"])
    def test_invalid_status_rejects(self, status: str) -> None:
        with pytest.raises(ValidationError):
            SpecFrontmatter.model_validate(
                {
                    "title": "Test",
                    "status": status,
                    "priority": "P1",
                    "created": date(2026, 1, 1),
                    "updated": date(2026, 1, 15),
                }
            )

    def test_canonical_lifecycle_states_match_r2(self) -> None:
        """Every official producer state validates without widening to arbitrary strings."""
        from validator.coherence.rules.r2_status_files import _VALID_STATUSES

        schema_statuses = set(get_args(SpecFrontmatter.model_fields["status"].annotation))
        assert schema_statuses == _VALID_STATUSES
        for status in sorted(_VALID_STATUSES):
            spec = SpecFrontmatter.model_validate(
                {
                    "title": "Test",
                    "status": status,
                    "priority": "P1",
                    "created": date(2026, 1, 1),
                    "updated": date(2026, 1, 1),
                }
            )
            assert spec.status == status

    def test_empty_title_rejects(self) -> None:
        with pytest.raises(ValidationError):
            SpecFrontmatter(
                title="   ",
                status="Draft",
                priority="P1",
                created=date(2026, 1, 1),
                updated=date(2026, 1, 15),
            )

    def test_updated_before_created_rejects(self) -> None:
        with pytest.raises(ValidationError, match="updated must be >= created"):
            SpecFrontmatter(
                title="Test",
                status="Draft",
                priority="P1",
                created=date(2026, 3, 1),
                updated=date(2026, 1, 1),
            )

    def test_invalid_priority_rejects(self) -> None:
        with pytest.raises(ValidationError):
            SpecFrontmatter.model_validate(
                {
                    "title": "Test",
                    "status": "Draft",
                    "priority": "P0",
                    "created": date(2026, 1, 1),
                    "updated": date(2026, 1, 1),
                }
            )

    def test_extra_fields_ignored(self) -> None:
        s = SpecFrontmatter.model_validate(
            {
                "title": "Test",
                "status": "Draft",
                "priority": "P1",
                "created": date(2026, 1, 1),
                "updated": date(2026, 1, 1),
                "custom_field": "hello",
            }
        )
        assert not hasattr(s, "custom_field")


class TestPlanFrontmatter:
    """PlanFrontmatter validation."""

    def test_valid_data(self) -> None:
        p = PlanFrontmatter(
            title="Auth Plan",
            spec_ref="../spec.md",
            created=date(2026, 1, 1),
        )
        assert p.spec_ref == "../spec.md"

    def test_missing_spec_ref_rejects(self) -> None:
        with pytest.raises(ValidationError):
            PlanFrontmatter.model_validate({"title": "Test", "created": date(2026, 1, 1)})

    def test_missing_title_rejects(self) -> None:
        with pytest.raises(ValidationError):
            PlanFrontmatter.model_validate({"spec_ref": "../spec.md", "created": date(2026, 1, 1)})


class TestImplementationFrontmatter:
    """ImplementationFrontmatter validation."""

    def test_valid_data(self) -> None:
        impl = ImplementationFrontmatter(title="Auth Impl", feature="user-auth")
        assert impl.feature == "user-auth"

    def test_missing_feature_rejects(self) -> None:
        with pytest.raises(ValidationError):
            ImplementationFrontmatter.model_validate({"title": "Test"})

    def test_missing_title_rejects(self) -> None:
        with pytest.raises(ValidationError):
            ImplementationFrontmatter.model_validate({"feature": "user-auth"})


class TestStackFrontmatter:
    """StackFrontmatter validation."""

    def test_valid_data(self) -> None:
        s = StackFrontmatter(title="Default Stack", updated=date(2026, 1, 1))
        assert s.updated == date(2026, 1, 1)

    def test_missing_updated_rejects(self) -> None:
        with pytest.raises(ValidationError):
            StackFrontmatter.model_validate({"title": "Stack"})


class TestGetSchema:
    """get_schema registry lookup."""

    @pytest.mark.parametrize(
        "file_type,expected",
        [
            ("spec", SpecFrontmatter),
            ("plan", PlanFrontmatter),
            ("implementation", ImplementationFrontmatter),
            ("stack", StackFrontmatter),
        ],
    )
    def test_returns_correct_schema(self, file_type: str, expected: type) -> None:
        assert get_schema(file_type) is expected

    @pytest.mark.parametrize(
        "file_type",
        ["roadmap", "unknown"],
    )
    def test_returns_none_for_types_without_schema(self, file_type: str) -> None:
        assert get_schema(file_type) is None
