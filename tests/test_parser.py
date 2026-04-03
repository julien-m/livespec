"""Tests for validator.parser — Markdown parsing with frontmatter and AST."""

from __future__ import annotations

from pathlib import Path

from validator.parser import ParsedFile, parse_file


class TestParseFrontmatter:
    """Frontmatter extraction."""

    def test_extracts_metadata(self, valid_spec_path: Path) -> None:
        result = parse_file(valid_spec_path)
        assert result.metadata["title"] == "User Authentication"
        assert result.metadata["status"] == "Draft"
        assert result.metadata["priority"] == "P1"

    def test_no_frontmatter(self, tmp_path: Path) -> None:
        f = tmp_path / "bare.md"
        f.write_text("# Just a heading\n\nSome body text.\n")
        result = parse_file(f)
        assert result.metadata == {}
        assert "Just a heading" in result.content


class TestParseHeadings:
    """H2/H3 heading extraction."""

    def test_extracts_h2_headings(self, valid_spec_path: Path) -> None:
        result = parse_file(valid_spec_path)
        assert "User Scenarios" in result.headings
        assert "Acceptance Criteria" in result.headings
        assert "Functional Requirements" in result.headings
        assert "Edge Cases" in result.headings

    def test_extracts_h3_headings(self, tmp_path: Path) -> None:
        f = tmp_path / "h3.md"
        f.write_text("## Parent\n\n### Child\n\nText.\n")
        result = parse_file(f)
        assert "Parent" in result.headings
        assert "Child" in result.headings

    def test_ignores_h1(self, tmp_path: Path) -> None:
        f = tmp_path / "h1.md"
        f.write_text("# Title\n\n## Section\n\nBody.\n")
        result = parse_file(f)
        assert "Title" not in result.headings
        assert "Section" in result.headings


class TestParseCodeBlocks:
    """Fenced code block extraction."""

    def test_extracts_code_blocks(self, valid_plan_path: Path) -> None:
        result = parse_file(valid_plan_path)
        langs = [cb["lang"] for cb in result.code_blocks]
        assert "mermaid" in langs

    def test_extracts_language_info(self, tmp_path: Path) -> None:
        f = tmp_path / "code.md"
        f.write_text("## Code\n\n```python\nprint('hello')\n```\n\n```json\n{}\n```\n")
        result = parse_file(f)
        langs = [cb["lang"] for cb in result.code_blocks]
        assert "python" in langs
        assert "json" in langs

    def test_no_code_blocks(self, tmp_path: Path) -> None:
        f = tmp_path / "plain.md"
        f.write_text("## Heading\n\nJust text, no code.\n")
        result = parse_file(f)
        assert result.code_blocks == []


class TestParseEdgeCases:
    """Edge cases in parsing."""

    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.md"
        f.write_text("")
        result = parse_file(f)
        assert result.metadata == {}
        assert result.headings == []
        assert result.code_blocks == []

    def test_returns_parsed_file_dataclass(self, valid_spec_path: Path) -> None:
        result = parse_file(valid_spec_path)
        assert isinstance(result, ParsedFile)
        assert isinstance(result.metadata, dict)
        assert isinstance(result.content, str)
        assert isinstance(result.headings, list)
        assert isinstance(result.code_blocks, list)
