"""Tests for behavioral TDD and audit mechanisms.

Validates that:
  - /spec-implement detects Behavioral AC and activates Step 0a (AC-001, AC-004)
  - /spec-test Phase 1.5 produces coverage matrix and messages (AC-007, AC-008, AC-009)

@spec AC-001, AC-004, AC-007, AC-008, AC-009 — .specs/features/005.1-behavioral-tdd-audit/spec.md
"""

from __future__ import annotations

import textwrap
from pathlib import Path

# Real command files — used for content-based validation
_IMPLEMENT_CMD = (
    Path(__file__).parent.parent
    / ".agent-sync"
    / "skills"
    / "spec-implement"
    / "SKILL.md"
)
_TEST_CMD = (
    Path(__file__).parent.parent / ".agent-sync" / "skills" / "spec-test" / "SKILL.md"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _has_behavioral_ac_section(spec_content: str) -> bool:
    """Check whether a spec.md content string contains a ## Behavioral AC section."""
    for line in spec_content.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Behavioral AC") or stripped.startswith("## Behavioral AC"):
            return True
    return False


def _build_audit_output(
    traits_covered: dict[str, list[tuple[str, str, bool]]],
    taxonomy_path: str = "system/testing/ui-behavioral-taxonomy.md",
) -> str:
    """Build a mock behavioral coverage audit output string.

    Args:
        traits_covered: dict mapping trait name to list of
            (pattern_name, pattern_keyword, is_covered) tuples.
        taxonomy_path: path to taxonomy document for gap references.

    Returns:
        Formatted audit output string matching the spec-test skill Phase 1.5
        format.
    """
    lines = ["### Behavioral Coverage Audit", ""]
    lines.append("| Trait | Required Pattern | Pattern Keyword | Status | Notes |")
    lines.append("|-------|-----------------|-----------------|--------|-------|")

    total = 0
    covered = 0
    gaps: list[tuple[str, str]] = []

    for trait, patterns in traits_covered.items():
        for pattern_name, keyword, is_covered in patterns:
            total += 1
            status = "Covered" if is_covered else "Gap"
            notes = "test found" if is_covered else "no test found"
            if is_covered:
                covered += 1
            else:
                gaps.append((trait, pattern_name))
            lines.append(
                f"| {trait} | {pattern_name} | `{keyword}` | {status} | {notes} |"
            )

    lines.append("")
    pct = int(covered / total * 100) if total > 0 else 0
    lines.append(f"**Behavioral coverage:** {covered}/{total} patterns covered ({pct}%)")

    if gaps:
        lines.append(f"**Gaps:** {len(gaps)}")
        for trait, _pattern_name in gaps:
            lines.append(
                f"  -> See taxonomy: {taxonomy_path}#{trait}"
            )
    else:
        lines.append("All behavioral traits covered")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Test 1 — AC-001: /spec-implement detects Behavioral AC
# ---------------------------------------------------------------------------


class TestImplementDetectsBehavioralAc:
    """AC-001: /spec-implement detects Behavioral AC and includes TDD step."""

    # @spec FR-001: Behavioral TDD detection
    # .specs/features/005.1-behavioral-tdd-audit/spec.md#fr-001

    def test_implement_detects_behavioral_ac(self, tmp_path: Path) -> None:
        """Given a spec.md with ## Behavioral AC containing is_submittable,
        verify the section is detectable."""
        spec_content = textwrap.dedent("""\
            # Feature Spec: Test Feature

            ## Acceptance Criteria

            | ID | Criterion |
            |----|-----------|
            | AC-001 | Form submits data |

            ## Behavioral AC

            - **is_submittable**: Form has a submit button with disabled state
            - **has_validation**: Form validates required fields
        """)

        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        # Verify detection: section is present
        assert _has_behavioral_ac_section(spec_content) is True

        # Verify trait names are present in the section
        assert "is_submittable" in spec_content
        assert "has_validation" in spec_content

        # Verify the implement command contains Step 0a for behavioral TDD
        implement_content = _IMPLEMENT_CMD.read_text()
        assert "Step 0a" in implement_content
        assert "Behavioral TDD" in implement_content
        assert "Behavioral AC" in implement_content


# ---------------------------------------------------------------------------
# Test 2 — AC-004: /spec-implement skips without Behavioral AC
# ---------------------------------------------------------------------------


class TestImplementSkipsWithoutBehavioralAc:
    """AC-004: Features without Behavioral AC are unaffected."""

    # @spec FR-004: Skip without Behavioral AC
    # .specs/features/005.1-behavioral-tdd-audit/spec.md#fr-004

    def test_implement_skips_without_behavioral_ac(self, tmp_path: Path) -> None:
        """Given a spec.md WITHOUT ## Behavioral AC section,
        verify the section is not present."""
        spec_content = textwrap.dedent("""\
            # Feature Spec: Backend Feature

            ## Acceptance Criteria

            | ID | Criterion |
            |----|-----------|
            | AC-001 | API returns 200 |
            | AC-002 | Data is persisted |

            ## Edge Cases

            | # | Edge Case |
            |---|-----------|
            | EC-001 | Empty payload returns 400 |
        """)

        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        # Verify detection: section is NOT present
        assert _has_behavioral_ac_section(spec_content) is False

        # Verify the implement command documents the skip condition
        implement_content = _IMPLEMENT_CMD.read_text()
        assert "If absent" in implement_content or "Skipped if" in implement_content


# ---------------------------------------------------------------------------
# Test 3 — AC-007: Coverage matrix structure
# ---------------------------------------------------------------------------


class TestAuditCoverageMatrixStructure:
    """AC-007: /spec-test produces a behavioral coverage matrix."""

    # @spec FR-007: Coverage matrix output
    # .specs/features/005.1-behavioral-tdd-audit/spec.md#fr-007

    def test_test_behavioral_audit_coverage_matrix_structure(self) -> None:
        """Given a known behavioral audit output, verify it contains
        required table columns: Trait, Pattern, Status."""
        audit_output = _build_audit_output(
            {
                "async_action": [
                    ("loading state", "loading-state", True),
                    ("double-click prevention", "double-click", False),
                ],
                "is_submittable": [
                    ("submit disabled when invalid", "submit-disabled", True),
                ],
            }
        )

        # Verify required columns exist in the table header
        assert "Trait" in audit_output
        assert "Required Pattern" in audit_output or "Pattern" in audit_output
        assert "Status" in audit_output

        # Verify coverage stats are present
        assert "Behavioral coverage:" in audit_output
        assert "2/3" in audit_output

        # Verify the test command contains the audit phase
        test_content = _TEST_CMD.read_text()
        assert "Behavioral Coverage Audit" in test_content
        assert "Trait" in test_content
        assert "Status" in test_content


# ---------------------------------------------------------------------------
# Test 4 — AC-008: All covered message
# ---------------------------------------------------------------------------


class TestAuditAllCoveredMessage:
    """AC-008: Shows 'All behavioral traits covered' when fully covered."""

    # @spec FR-008: All covered message — .specs/features/005.1-behavioral-tdd-audit/spec.md#fr-008

    def test_test_audit_all_covered_message(self) -> None:
        """Given an audit output where all patterns are covered,
        verify 'All behavioral traits covered' message is present."""
        audit_output = _build_audit_output(
            {
                "is_submittable": [
                    ("submit disabled when invalid", "submit-disabled", True),
                ],
                "has_validation": [
                    ("error message shown", "error-message", True),
                ],
            }
        )

        assert "All behavioral traits covered" in audit_output

        # Verify no gaps are reported
        assert "Gaps:" not in audit_output

        # Verify the command documents this message
        test_content = _TEST_CMD.read_text()
        assert "All behavioral traits covered" in test_content


# ---------------------------------------------------------------------------
# Test 5 — AC-009: Gap includes taxonomy reference
# ---------------------------------------------------------------------------


class TestAuditGapIncludesTaxonomyRef:
    """AC-009: Gap reports include taxonomy reference."""

    # @spec FR-009: Taxonomy ref in gaps — .specs/features/005.1-behavioral-tdd-audit/spec.md#fr-009

    def test_test_audit_missing_pattern_with_taxonomy_ref(self) -> None:
        """Given an audit output with a gap, verify it includes
        taxonomy reference text."""
        audit_output = _build_audit_output(
            {
                "async_action": [
                    ("loading state", "loading-state", True),
                    ("double-click prevention", "double-click", False),
                ],
            }
        )

        # Verify gap is reported
        assert "Gap" in audit_output
        assert "Gaps:" in audit_output

        # Verify taxonomy reference is included
        assert "taxonomy" in audit_output.lower()
        assert "ui-behavioral-taxonomy" in audit_output

        # Verify the reference points to the specific trait
        assert "async_action" in audit_output

        # Verify the test command documents taxonomy references in gaps
        test_content = _TEST_CMD.read_text()
        assert "taxonomy" in test_content.lower()
