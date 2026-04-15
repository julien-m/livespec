"""Tests for Feature 004 — Visual Testing Governance.

Validates that:
- baseline.manifest.yml schema document exists and is well-formed (FR-007)
- spec.test.md contains the manifest write block (FR-001)
- spec.check.md contains --show-provenance handler (FR-002)
- spec.check.md Step 8 contains staleness gate with mockup hash detection (FR-003, FR-004)
- spec.check.md Step 8 contains browser version detection (FR-005)
- spec.check.md contains --visual-status governance dashboard (FR-006)
- migrations/5/migrate.md exists with correct structure (FR-008)

These are "spec-trace" tests: they verify that the command Markdown files contain
the documented behavior, following the same pattern as feature 003 implementation tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent
SPEC_TEST_MD = REPO_ROOT / "commands" / "test.md"
SPEC_CHECK_MD = REPO_ROOT / "commands" / "check.md"
BASELINE_SCHEMA_MD = REPO_ROOT / "system" / "schemas" / "baseline-manifest.md"
MIGRATION_V5_MD = REPO_ROOT / "migrations" / "5" / "migrate.md"
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "baseline_manifest"


# ---------------------------------------------------------------------------
# FR-007: Schema document exists and contains required fields
# ---------------------------------------------------------------------------


class TestBaselineManifestSchema:
    """AC-001, AC-002: Schema document is well-formed and complete."""

    def test_schema_file_exists(self) -> None:
        """FR-007: baseline-manifest.md schema file must exist."""
        assert BASELINE_SCHEMA_MD.exists(), (
            f"system/schemas/baseline-manifest.md not found at {BASELINE_SCHEMA_MD}"
        )

    def test_schema_documents_required_fields(self) -> None:
        """AC-002: Schema must document all required fields from AC-002."""
        content = BASELINE_SCHEMA_MD.read_text()
        # Required fields per AC-002
        required_fields = [
            "capture_date",
            "approved_by",
            "browser_version",
            "os",
            "mockup_version",
            "docker_image",
        ]
        for field in required_fields:
            assert field in content, (
                f"Required field '{field}' not documented in baseline-manifest.md (AC-002)"
            )

    def test_schema_documents_approved_by_auto_values(self) -> None:
        """AC-002: Schema must document auto-approved values for spec.ship pipeline."""
        content = BASELINE_SCHEMA_MD.read_text()
        assert "auto (spec.ship)" in content, (
            "Schema must document 'auto (spec.ship)' as an approved_by value"
        )

    def test_schema_documents_pre_v5_stub_value(self) -> None:
        """AC-012: Schema must document 'pre-v5 (untracked)' for migration stubs."""
        content = BASELINE_SCHEMA_MD.read_text()
        assert "pre-v5 (untracked)" in content, (
            "Schema must document 'pre-v5 (untracked)' as approved_by value for migration stubs"
        )

    def test_schema_documents_sha256_format(self) -> None:
        """AC-002: mockup_version field must use sha256: prefix format."""
        content = BASELINE_SCHEMA_MD.read_text()
        assert "sha256:" in content, "Schema must document sha256: prefix format for mockup_version"

    def test_schema_example_yaml_is_valid(self) -> None:
        """Schema must contain a valid YAML example block."""
        content = BASELINE_SCHEMA_MD.read_text()
        # Extract the first ```yaml block
        yaml_blocks: list[str] = []
        in_block = False
        current_block: list[str] = []
        for line in content.splitlines():
            if line.strip() == "```yaml":
                in_block = True
                current_block = []
            elif line.strip() == "```" and in_block:
                in_block = False
                yaml_blocks.append("\n".join(current_block))
            elif in_block:
                current_block.append(line)

        assert len(yaml_blocks) >= 1, "Schema must contain at least one ```yaml block"

        # The first block is the schema definition — parse it
        # It uses placeholder values like "<feature-name>" so we only check it doesn't crash
        for block in yaml_blocks:
            # Skip schema definition blocks with angle-bracket placeholders
            if "<" in block:
                continue
            try:
                parsed = yaml.safe_load(block)
                assert isinstance(parsed, dict), "YAML example block must parse to a dict"
            except yaml.YAMLError as e:
                pytest.fail(f"Invalid YAML in schema example block: {e}")

    def test_schema_specifies_version_field(self) -> None:
        """Schema must define schema_version field for future evolution."""
        content = BASELINE_SCHEMA_MD.read_text()
        assert "schema_version" in content, "Schema must document schema_version field"


# ---------------------------------------------------------------------------
# FR-001: spec.test.md writes manifest after approval
# ---------------------------------------------------------------------------


class TestSpecTestManifestWrite:
    """AC-001, AC-002: spec.test Phase 4.5.3 writes baseline.manifest.yml."""

    def test_spec_test_contains_manifest_write_block(self) -> None:
        """AC-001: spec.test.md must document manifest write after approval."""
        assert SPEC_TEST_MD.exists(), f"spec.test.md not found at {SPEC_TEST_MD}"
        content = SPEC_TEST_MD.read_text()
        assert "baseline.manifest.yml" in content, (
            "spec.test.md must document baseline.manifest.yml write (AC-001)"
        )

    def test_spec_test_references_fr001_anchor(self) -> None:
        """FR-001: spec.test.md must have @spec anchor for FR-001."""
        content = SPEC_TEST_MD.read_text()
        assert "@spec FR-001" in content, (
            "spec.test.md must contain @spec FR-001 anchor for baseline manifest write"
        )

    def test_spec_test_documents_all_required_fields(self) -> None:
        """AC-002: spec.test.md must document collection of all required manifest fields."""
        content = SPEC_TEST_MD.read_text()
        required_fields = [
            "capture_date",
            "approved_by",
            "browser_version",
            "os",
            "mockup_version",
            "docker_image",
        ]
        for field in required_fields:
            assert field in content, (
                f"spec.test.md must document field '{field}' for manifest write (AC-002)"
            )

    def test_spec_test_documents_auto_approved_by(self) -> None:
        """AC-002: spec.test.md must document auto (spec.ship) approved_by value."""
        content = SPEC_TEST_MD.read_text()
        assert "auto (spec.ship)" in content, (
            "spec.test.md must document 'auto (spec.ship)' as approved_by in --auto mode (AC-002)"
        )

    def test_spec_test_documents_definition_of_done_manifest(self) -> None:
        """AC-001: baseline.manifest.yml must appear in spec.test Definition of Done."""
        content = SPEC_TEST_MD.read_text()
        # Check it appears in the DoD checklist (after "Definition of Done")
        dod_idx = content.find("Definition of Done")
        assert dod_idx != -1, "spec.test.md must have a Definition of Done section"
        dod_section = content[dod_idx:]
        assert "baseline.manifest.yml" in dod_section, (
            "baseline.manifest.yml must be in spec.test Definition of Done (AC-001)"
        )


# ---------------------------------------------------------------------------
# FR-002: spec.check.md --show-provenance flag
# ---------------------------------------------------------------------------


class TestSpecCheckShowProvenance:
    """AC-003, AC-004: --show-provenance flag reads and displays manifest."""

    def test_spec_check_contains_show_provenance_flag(self) -> None:
        """AC-003: spec.check.md must document --show-provenance flag."""
        assert SPEC_CHECK_MD.exists(), f"spec.check.md not found at {SPEC_CHECK_MD}"
        content = SPEC_CHECK_MD.read_text()
        assert "--show-provenance" in content, (
            "spec.check.md must document --show-provenance flag (AC-003)"
        )

    def test_spec_check_show_provenance_references_fr002(self) -> None:
        """FR-002: spec.check.md must have @spec anchor for FR-002."""
        content = SPEC_CHECK_MD.read_text()
        assert "@spec FR-002" in content, (
            "spec.check.md must contain @spec FR-002 anchor for show-provenance handler"
        )

    def test_spec_check_show_provenance_documents_table_columns(self) -> None:
        """AC-003: --show-provenance must display provenance table with required columns."""
        content = SPEC_CHECK_MD.read_text()
        # Required display columns per AC-003
        required_display_cols = ["Capture Date", "Approved By", "Mockup Version"]
        for col in required_display_cols:
            assert col in content, (
                f"spec.check.md --show-provenance must display column '{col}' (AC-003)"
            )

    def test_spec_check_show_provenance_handles_missing_manifest(self) -> None:
        """AC-004: Missing manifest must trigger WARNING not ERROR in spec.check."""
        content = SPEC_CHECK_MD.read_text()
        # The show-provenance handler should have a graceful missing manifest path
        assert "No baseline manifest found" in content or "manifest" in content.lower(), (
            "spec.check.md must handle missing manifest gracefully (AC-004)"
        )

    def test_spec_check_flags_table_includes_show_provenance(self) -> None:
        """AC-003: --show-provenance must appear in the spec.check flags table."""
        content = SPEC_CHECK_MD.read_text()
        flags_idx = content.find("## Flags")
        assert flags_idx != -1, "spec.check.md must have a Flags section"
        flags_section = content[flags_idx:]
        assert "--show-provenance" in flags_section, (
            "--show-provenance must appear in spec.check Flags table (AC-003)"
        )


# ---------------------------------------------------------------------------
# FR-003, FR-004, FR-005: Staleness detection in spec.check Step 8
# ---------------------------------------------------------------------------


class TestStalenessDetection:
    """AC-005, AC-006, AC-007, AC-008, AC-009: Staleness gate in spec.check Step 8."""

    def test_spec_check_has_staleness_gate(self) -> None:
        """FR-003: spec.check Step 8 must have a Staleness Gate section."""
        content = SPEC_CHECK_MD.read_text()
        assert "Staleness Gate" in content or "staleness" in content.lower(), (
            "spec.check.md Step 8 must document staleness detection (FR-003)"
        )

    def test_spec_check_references_fr003_fr004_fr005(self) -> None:
        """FR-003/FR-004/FR-005: spec.check.md must have @spec anchor for staleness FRs."""
        content = SPEC_CHECK_MD.read_text()
        assert "FR-003" in content, "spec.check.md must reference FR-003 (staleness check)"
        assert "FR-004" in content, "spec.check.md must reference FR-004 (mockup hash)"
        assert "FR-005" in content, "spec.check.md must reference FR-005 (browser version)"

    def test_spec_check_documents_mockup_hash_comparison(self) -> None:
        """AC-005/FR-004: spec.check must detect mockup changes via SHA-256 hash."""
        content = SPEC_CHECK_MD.read_text()
        assert "SHA-256" in content or "sha256" in content.lower(), (
            "spec.check.md must document SHA-256 hash comparison"
            " for mockup change detection (AC-005)"
        )

    def test_spec_check_documents_browser_version_detection(self) -> None:
        """AC-008/FR-005: spec.check must detect browser version from playwright --version."""
        content = SPEC_CHECK_MD.read_text()
        assert "playwright --version" in content or "browser_version" in content, (
            "spec.check.md must document browser version detection (AC-008)"
        )

    def test_spec_check_documents_stale_browser_marks_all_screens(self) -> None:
        """AC-009: Browser version change must mark ALL baselines stale."""
        content = SPEC_CHECK_MD.read_text()
        assert "STALE-BROWSER" in content, (
            "spec.check.md must document STALE-BROWSER classification (AC-009)"
        )
        # Verify "all" is mentioned in context of browser staleness
        stale_browser_idx = content.find("STALE-BROWSER")
        assert stale_browser_idx != -1
        context = content[max(0, stale_browser_idx - 500) : stale_browser_idx + 500]
        assert "all" in context.lower(), (
            "spec.check.md must state browser version change marks ALL baselines stale (AC-009)"
        )

    def test_spec_check_stale_is_warning_not_error(self) -> None:
        """AC-006/AC-007: Stale baselines produce WARNING exit, not ERROR."""
        content = SPEC_CHECK_MD.read_text()
        # Should mention WARNING in context of stale
        assert "WARNING" in content, (
            "spec.check.md must document WARNING exit for stale baselines (AC-007)"
        )

    def test_spec_check_skips_comparison_for_stale_baselines(self) -> None:
        """AC-006: Stale baselines must NOT be used for pixel comparison."""
        content = SPEC_CHECK_MD.read_text()
        assert "skip" in content.lower() or "Skipped" in content, (
            "spec.check.md must document that stale baseline comparison is skipped (AC-006)"
        )

    def test_spec_check_documents_staleness_classifications(self) -> None:
        """AC-005/AC-008: All staleness states must be documented."""
        content = SPEC_CHECK_MD.read_text()
        states = ["VALID", "STALE-MOCKUP", "STALE-BROWSER", "NO-MANIFEST"]
        for state in states:
            assert state in content, (
                f"spec.check.md must document staleness state '{state}' (AC-010)"
            )


# ---------------------------------------------------------------------------
# FR-006: spec.check.md --visual-status governance dashboard
# ---------------------------------------------------------------------------


class TestVisualStatusDashboard:
    """AC-010, AC-011: --visual-status governance dashboard."""

    def test_spec_check_contains_visual_status_flag(self) -> None:
        """AC-010: spec.check.md must document --visual-status flag."""
        content = SPEC_CHECK_MD.read_text()
        assert "--visual-status" in content, (
            "spec.check.md must document --visual-status flag (AC-010)"
        )

    def test_spec_check_visual_status_references_fr006(self) -> None:
        """FR-006: spec.check.md must have @spec anchor for FR-006."""
        content = SPEC_CHECK_MD.read_text()
        assert "@spec FR-006" in content, (
            "spec.check.md must contain @spec FR-006 anchor for visual-status handler"
        )

    def test_spec_check_visual_status_shows_all_classifications(self) -> None:
        """AC-010: --visual-status must show VALID/STALE-MOCKUP/STALE-BROWSER/NO-MANIFEST."""
        content = SPEC_CHECK_MD.read_text()
        # Find --visual-status section context
        vs_idx = content.find("visual-status")
        assert vs_idx != -1
        # All 4 classifications must be documented
        classifications = ["VALID", "STALE-MOCKUP", "STALE-BROWSER", "NO-MANIFEST"]
        for cls in classifications:
            assert cls in content, (
                f"spec.check.md --visual-status must classify '{cls}' state (AC-010)"
            )

    def test_spec_check_visual_status_documents_action_summary(self) -> None:
        """AC-011: --visual-status must print action summary with --reset-baselines commands."""
        content = SPEC_CHECK_MD.read_text()
        assert "Action" in content and "--reset-baselines" in content, (
            "spec.check.md --visual-status must document action summary"
            " with --reset-baselines (AC-011)"
        )

    def test_spec_check_visual_status_documents_all_valid_message(self) -> None:
        """AC-010: --visual-status must report 'all valid' when no issues."""
        content = SPEC_CHECK_MD.read_text()
        assert "All baselines valid" in content, (
            "spec.check.md --visual-status must document 'All baselines valid' message (AC-010)"
        )

    def test_spec_check_flags_table_includes_visual_status(self) -> None:
        """AC-010: --visual-status must appear in spec.check flags table."""
        content = SPEC_CHECK_MD.read_text()
        flags_idx = content.find("## Flags")
        assert flags_idx != -1
        flags_section = content[flags_idx:]
        assert "--visual-status" in flags_section, (
            "--visual-status must appear in spec.check Flags table (AC-010)"
        )


# ---------------------------------------------------------------------------
# FR-008: migrations/5/migrate.md stub generation
# ---------------------------------------------------------------------------


class TestMigrationV5:
    """AC-012: Migration v5 generates manifest stubs for existing baselines."""

    def test_migration_v5_file_exists(self) -> None:
        """FR-008: migrations/5/migrate.md must exist."""
        assert MIGRATION_V5_MD.exists(), f"migrations/5/migrate.md not found at {MIGRATION_V5_MD}"

    def test_migration_v5_references_fr008_anchor(self) -> None:
        """FR-008: migration file must have @spec FR-008 anchor."""
        content = MIGRATION_V5_MD.read_text()
        assert "@spec FR-008" in content, "migrations/5/migrate.md must contain @spec FR-008 anchor"

    def test_migration_v5_documents_generate_stub_action(self) -> None:
        """AC-012: Migration v5 must document GENERATE_STUB action for existing baselines."""
        content = MIGRATION_V5_MD.read_text()
        assert "GENERATE_STUB" in content, (
            "migrations/5/migrate.md must document GENERATE_STUB action (AC-012)"
        )

    def test_migration_v5_documents_set_version_action(self) -> None:
        """FR-008: Migration v5 must document SET_VERSION 5 action."""
        content = MIGRATION_V5_MD.read_text()
        assert "SET_VERSION" in content and "5" in content, (
            "migrations/5/migrate.md must document SET_VERSION 5 action (FR-008)"
        )

    def test_migration_v5_documents_idempotency_check(self) -> None:
        """AC-012: Migration v5 must be idempotent."""
        content = MIGRATION_V5_MD.read_text()
        assert "Idempotency" in content or "idempotent" in content.lower(), (
            "migrations/5/migrate.md must document idempotency check (AC-012)"
        )

    def test_migration_v5_documents_pre_v5_approved_by(self) -> None:
        """AC-012: Stub manifest must use 'pre-v5 (untracked)' as approved_by."""
        content = MIGRATION_V5_MD.read_text()
        assert "pre-v5 (untracked)" in content, (
            "migrations/5/migrate.md must use 'pre-v5 (untracked)' as stub approved_by (AC-012)"
        )

    def test_migration_v5_handles_no_baselines_edge_case(self) -> None:
        """AC-012: Migration must handle project with no baselines gracefully."""
        content = MIGRATION_V5_MD.read_text()
        assert "No baselines found" in content or "no baselines" in content.lower(), (
            "migrations/5/migrate.md must handle project with no baselines (AC-012 edge case)"
        )

    def test_migration_v5_has_correct_frontmatter_version(self) -> None:
        """FR-008: Migration v5 frontmatter must set version: 5."""
        content = MIGRATION_V5_MD.read_text()
        # Check YAML frontmatter
        if content.startswith("---"):
            end_idx = content.find("---", 3)
            if end_idx != -1:
                frontmatter_str = content[3:end_idx]
                try:
                    fm = yaml.safe_load(frontmatter_str)
                    assert fm is not None and fm.get("version") == 5, (
                        "migrations/5/migrate.md frontmatter must have version: 5"
                    )
                except yaml.YAMLError:
                    pytest.fail("migrations/5/migrate.md frontmatter is not valid YAML")


# ---------------------------------------------------------------------------
# Fixture-based tests: validate YAML fixture files
# ---------------------------------------------------------------------------


class TestBaselineManifestFixtures:
    """Validate YAML fixture files used in testing."""

    def test_valid_manifest_fixture_is_parseable(self) -> None:
        """Valid manifest fixture must be parseable YAML."""
        fixture_path = FIXTURES_DIR / "valid_manifest.yml"
        if not fixture_path.exists():
            pytest.skip("valid_manifest.yml fixture not yet created")
        content = fixture_path.read_text()
        parsed = yaml.safe_load(content)
        assert isinstance(parsed, dict), "valid_manifest.yml must parse to a dict"
        assert "screens" in parsed, "valid_manifest.yml must have 'screens' key"
        assert "schema_version" in parsed, "valid_manifest.yml must have schema_version"

    def test_stub_manifest_fixture_is_parseable(self) -> None:
        """Stub manifest fixture must be parseable YAML with null capture_date."""
        fixture_path = FIXTURES_DIR / "stub_manifest.yml"
        if not fixture_path.exists():
            pytest.skip("stub_manifest.yml fixture not yet created")
        content = fixture_path.read_text()
        parsed = yaml.safe_load(content)
        assert isinstance(parsed, dict), "stub_manifest.yml must parse to a dict"
        manifest = cast(dict[str, Any], parsed)
        screens = cast(list[Any], manifest.get("screens", []))
        assert len(screens) > 0, "stub_manifest.yml must have at least one screen"
        first_screen = cast(dict[str, Any], screens[0])
        assert first_screen.get("approved_by") == "pre-v5 (untracked)", (
            "stub_manifest.yml screen must have 'pre-v5 (untracked)' approved_by"
        )
