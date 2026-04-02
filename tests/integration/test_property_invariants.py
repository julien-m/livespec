"""Level 3A — Property invariants on static fixtures (no LLM calls)."""

from __future__ import annotations

import re

import pytest
from pathlib import Path
from tests.integration.helpers.validators import (
    validate_frontmatter,
    validate_spec_sections,
    validate_gherkin_blocks,
    validate_mermaid_blocks,
    validate_ac_fr_links,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.mark.level_3a
class TestSpecMdInvariants:
    """Structural invariants on spec.md (post-specify fixture)."""

    @pytest.fixture
    def spec_md(self) -> str:
        path = FIXTURES_DIR / "post-specify/.specs/features/001-user-auth/spec.md"
        return path.read_text()

    def test_frontmatter_yaml_valid(self, spec_md: str):
        """Output MUST contain valid YAML frontmatter."""
        result = validate_frontmatter(spec_md)
        assert result.valid, f"Invalid frontmatter: {result.errors}"

    def test_required_sections_present(self, spec_md: str):
        """Output MUST contain required sections from spec-system.md."""
        required = [
            "Feature Name",
            "Branch",
            "Date",
            "Status",
            "User Scenarios",
            "Acceptance Criteria",
            "Functional Requirements",
            "Key Entities",
            "Edge Cases",
            "Success Criteria",
        ]
        result = validate_spec_sections(spec_md, required_sections=required)
        assert result.valid, f"Missing sections: {result.missing}"

    def test_gherkin_present_and_syntactically_valid(self, spec_md: str):
        """Each story MUST have at least 1 Gherkin block."""
        result = validate_gherkin_blocks(spec_md, min_per_story=1)
        assert result.valid, f"Invalid Gherkin: {result.errors}"

    def test_mermaid_flowchart_present_per_story(self, spec_md: str):
        """Each story MUST have a Mermaid flowchart."""
        result = validate_mermaid_blocks(spec_md, expected_type="flowchart")
        assert result.count >= result.story_count, (
            f"Insufficient Mermaid: {result.count} flowcharts for "
            f"{result.story_count} stories"
        )

    def test_no_unresolved_decision_needed(self, spec_md: str):
        """Output MUST NOT contain unresolved [DECISION NEEDED] markers."""
        unresolved = re.findall(r"\[DECISION NEEDED\]", spec_md, re.IGNORECASE)
        assert len(unresolved) == 0, (
            f"{len(unresolved)} unresolved [DECISION NEEDED] marker(s)"
        )

    def test_fr_maps_to_ac(self, spec_md: str):
        """Each FR MUST reference at least one AC."""
        result = validate_ac_fr_links(spec_md)
        assert result.valid, f"FR without AC: {result.orphan_frs}"

    def test_ac_numbered_sequentially(self, spec_md: str):
        """AC definitions must be numbered sequentially."""
        # Only check AC definitions (### AC-NNN headings or | AC-NNN | in AC table)
        ac_definitions = re.findall(r"###\s+AC-(\d{3})", spec_md)
        if not ac_definitions:
            # Fallback: unique AC references in order of first appearance
            seen = []
            for m in re.finditer(r"AC-(\d{3})", spec_md):
                num = m.group(1)
                if num not in seen:
                    seen.append(num)
            ac_definitions = seen
        expected = [f"{i + 1:03d}" for i in range(len(ac_definitions))]
        assert ac_definitions == expected, (
            f"Non-sequential AC numbering: {ac_definitions}"
        )

    def test_no_excessive_needs_clarification(self, spec_md: str):
        """Max 3 [NEEDS CLARIFICATION] markers allowed."""
        markers = re.findall(r"\[NEEDS CLARIFICATION\]", spec_md, re.IGNORECASE)
        assert len(markers) <= 3, (
            f"{len(markers)} [NEEDS CLARIFICATION] markers (max: 3)"
        )


@pytest.mark.level_3a
class TestSpecAnchorFormat:
    """@spec anchors MUST follow the format defined in spec-system.md."""

    @pytest.fixture
    def source_files(self) -> list[Path]:
        return list((FIXTURES_DIR / "post-specify/src").glob("**/*.ts"))

    def test_anchor_format_valid(self, source_files: list[Path]):
        """Expected format: @spec FR-NNN: description -- path#fragment"""
        anchor_pattern = re.compile(
            r"@spec\s+FR-\d{3}(?::\s+[^\u2014]{1,50}\s+\u2014\s+[^\s]+#fr-\d{3})?"
        )
        for path in source_files:
            content = path.read_text()
            raw_anchors = re.findall(r"@spec\s+FR-\d{3}.*", content)
            for anchor in raw_anchors:
                assert anchor_pattern.match(anchor), (
                    f"Malformed anchor in {path.name}: {anchor!r}"
                )


@pytest.mark.level_3a
class TestRoadmapStructure:
    """Roadmap MUST be organized in tiers with HTML markers."""

    @pytest.fixture
    def roadmap_md(self) -> str:
        path = FIXTURES_DIR / "post-specify/.specs/roadmap.md"
        return path.read_text()

    def test_html_markers_present(self, roadmap_md: str):
        """HTML section markers must be present."""
        required_markers = [
            "<!-- roadmap:mvp:start -->",
            "<!-- roadmap:mvp:end -->",
            "<!-- roadmap:postmvp:start -->",
            "<!-- roadmap:postmvp:end -->",
            "<!-- roadmap:future:start -->",
            "<!-- roadmap:future:end -->",
        ]
        for marker in required_markers:
            assert marker in roadmap_md, f"Missing marker: {marker}"

    def test_items_format_correct(self, roadmap_md: str):
        """Items must follow format: - [ ] **Name** -- description ..."""
        item_pattern = re.compile(
            r"^- \[[ x]\] \*\*.+\*\* \u2014 .+",
            re.MULTILINE,
        )
        items = item_pattern.findall(roadmap_md)
        assert len(items) >= 1, "No roadmap item found in expected format"


@pytest.mark.level_3a
class TestReadmeMarkers:
    """README.md must contain updatable section markers."""

    @pytest.fixture
    def readme_md(self) -> str:
        path = FIXTURES_DIR / "post-specify/.specs/README.md"
        return path.read_text()

    def test_features_markers_present(self, readme_md: str):
        assert "<!-- readme:features:start -->" in readme_md
        assert "<!-- readme:features:end -->" in readme_md

    def test_decisions_markers_present(self, readme_md: str):
        assert "<!-- readme:decisions:start -->" in readme_md
        assert "<!-- readme:decisions:end -->" in readme_md

    def test_activity_markers_present(self, readme_md: str):
        assert "<!-- readme:activity:start -->" in readme_md
        assert "<!-- readme:activity:end -->" in readme_md
