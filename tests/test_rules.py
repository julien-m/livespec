"""Tests for validator.rules — section presence and type-specific rules."""

from __future__ import annotations

import pytest

from validator.rules import validate_by_type, validate_sections
from validator.rules.changelog_entries import validate_changelog_entries
from validator.rules.roadmap_markers import validate_roadmap_markers
from validator.rules.sections import section_present


class TestSectionPresent:
    """section_present helper."""

    def test_matches_case_insensitive(self) -> None:
        assert section_present(["user scenarios"], ["User Scenarios"])

    def test_matches_partial(self) -> None:
        assert section_present(["My Acceptance Criteria Section"], ["Acceptance Criteria"])

    def test_no_match(self) -> None:
        assert not section_present(["Summary", "Risks"], ["Acceptance Criteria"])


class TestValidateSectionsSpec:
    """Section validation for spec type."""

    def test_all_sections_present(self) -> None:
        headings = [
            "User Scenarios",
            "Acceptance Criteria",
            "Functional Requirements",
            "Edge Cases",
        ]
        errors, warnings = validate_sections(headings, "spec")
        assert errors == []
        assert warnings == []

    def test_missing_section_returns_error(self) -> None:
        headings = ["User Scenarios", "Acceptance Criteria"]
        errors, warnings = validate_sections(headings, "spec")
        assert len(errors) == 2  # missing FR and Edge Cases
        assert any("fr" in e.lower() or "functional" in e.lower() for e in errors)
        assert any("edge" in e.lower() for e in errors)

    def test_empty_headings_returns_all_errors(self) -> None:
        errors, warnings = validate_sections([], "spec")
        assert len(errors) == 4


class TestValidateSectionsPlan:
    """Section validation for plan type."""

    def test_all_sections_present(self) -> None:
        headings = ["Summary", "Implementation Plan", "Testing Strategy", "Risks"]
        errors, warnings = validate_sections(headings, "plan")
        assert errors == []

    def test_missing_section(self) -> None:
        headings = ["Summary"]
        errors, _ = validate_sections(headings, "plan")
        assert len(errors) == 3


class TestValidateSectionsUnknownType:
    """Section validation for types without rules."""

    def test_unknown_type_returns_no_errors(self) -> None:
        errors, warnings = validate_sections(["Whatever"], "changelog")
        assert errors == []
        assert warnings == []


class TestValidateByTypeRoadmap:
    """Type-specific rules for roadmap."""

    def test_valid_markers(self) -> None:
        content = (
            "<!-- roadmap:mvp:start -->\n<!-- roadmap:mvp:end -->\n"
            "<!-- roadmap:postmvp:start -->\n<!-- roadmap:postmvp:end -->\n"
            "<!-- roadmap:future:start -->\n<!-- roadmap:future:end -->\n"
            "<!-- roadmap:deferred:start -->\n<!-- roadmap:deferred:end -->\n"
        )
        errors = validate_by_type(content, "roadmap", [])
        assert errors == []

    def test_missing_markers(self) -> None:
        content = "<!-- roadmap:mvp:start -->\n<!-- roadmap:mvp:end -->\n"
        errors = validate_by_type(content, "roadmap", [])
        assert len(errors) > 0
        assert any("postmvp" in e for e in errors)


class TestValidateByTypeChangelog:
    """Type-specific rules for changelog."""

    def test_valid_entries(self) -> None:
        content = "## 2026-04-02 — [Feature]: Added auth\n\nDetails.\n"
        errors = validate_by_type(content, "changelog", [])
        assert errors == []

    def test_no_entries(self) -> None:
        content = "# Changelog\n\nJust some text.\n"
        errors = validate_by_type(content, "changelog", [])
        assert len(errors) == 1
        assert "changelog entry" in errors[0].lower()


class TestValidateByTypePlan:
    """Type-specific rules for plan."""

    def test_has_mermaid(self) -> None:
        code_blocks = [{"lang": "mermaid", "code": "sequenceDiagram\n..."}]
        errors = validate_by_type("plan content", "plan", code_blocks)
        assert errors == []

    def test_no_mermaid(self) -> None:
        code_blocks = [{"lang": "python", "code": "print('hello')"}]
        errors = validate_by_type("plan content", "plan", code_blocks)
        assert len(errors) == 1
        assert "mermaid" in errors[0].lower()

    def test_empty_code_blocks(self) -> None:
        errors = validate_by_type("plan content", "plan", [])
        assert len(errors) == 1


class TestValidateByTypeImplementation:
    """Type-specific rules for implementation."""

    def test_has_spec_anchor(self) -> None:
        content = "Mapped to @spec(FR-001).\n"
        errors = validate_by_type(content, "implementation", [])
        assert errors == []

    def test_no_spec_anchor(self) -> None:
        content = "Just implementation notes.\n"
        errors = validate_by_type(content, "implementation", [])
        assert len(errors) == 1
        assert "@spec" in errors[0]


class TestValidateByTypeProgress:
    """Type-specific rules for progress."""

    def test_has_step_table(self) -> None:
        content = "| Step | Status |\n|------|--------|\n| 1 | Done |\n"
        errors = validate_by_type(content, "progress", [])
        assert errors == []

    def test_no_step_table(self) -> None:
        content = "# Progress\n\nNo table here.\n"
        errors = validate_by_type(content, "progress", [])
        assert len(errors) == 1
        assert "Step" in errors[0]


class TestValidateByTypeConstitution:
    """Type-specific rules for constitution."""

    def test_valid_content(self) -> None:
        content = "A" * 200  # >100 chars, no placeholders
        errors = validate_by_type(content, "constitution", [])
        assert errors == []

    def test_too_short(self) -> None:
        content = "Short."
        errors = validate_by_type(content, "constitution", [])
        assert any("too short" in e.lower() for e in errors)

    def test_has_tbd_placeholder(self) -> None:
        content = "A" * 200 + " [TBD] more text."
        errors = validate_by_type(content, "constitution", [])
        assert any("placeholder" in e.lower() for e in errors)

    def test_has_todo_placeholder(self) -> None:
        content = "A" * 200 + " [TODO] more text."
        errors = validate_by_type(content, "constitution", [])
        assert any("placeholder" in e.lower() for e in errors)

    def test_project_type_same_rules(self) -> None:
        """The 'project' type shares the same rules as constitution."""
        content = "Short [TBD]."
        errors = validate_by_type(content, "project", [])
        assert len(errors) == 2  # too short + placeholder
