"""Tests for validator.fixer — auto-fix Pass 1 mechanical corrections."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import frontmatter
import pytest

from validator.config import ValidatorConfig
from validator.engine import validate_file
from validator.fixer import FixAction, fix_file

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _make_spec(specs_root: Path, content: str) -> Path:
    """Write content to the spec.md position and return the path."""
    dst = specs_root / "features" / "001-test" / "spec.md"
    dst.write_text(content)
    return dst


class TestFixInvalidStatus:
    """Fixes invalid status to Draft."""

    def test_fixes_status_to_draft(
        self, specs_root: Path, default_config: ValidatorConfig
    ) -> None:
        path = _make_spec(
            specs_root,
            "---\ntitle: Test\nstatus: WIP\npriority: P1\n"
            "created: 2026-01-01\nupdated: 2026-01-15\n---\n\n"
            "## User Scenarios\n\n## Acceptance Criteria\n\n"
            "## Functional Requirements\n\n## Edge Cases\n",
        )
        result = validate_file(path, specs_root, default_config)
        actions = fix_file(path, result, specs_root, default_config)
        descriptions = [a.description for a in actions]
        assert any("Draft" in d for d in descriptions)

        # Verify the file was actually fixed
        post = frontmatter.load(str(path))
        assert post["status"] == "Draft"


class TestFixMissingPriority:
    """Fixes missing priority to P2."""

    def test_fixes_priority_to_p2(
        self, specs_root: Path, default_config: ValidatorConfig
    ) -> None:
        path = _make_spec(
            specs_root,
            "---\ntitle: Test\nstatus: Draft\n"
            "created: 2026-01-01\nupdated: 2026-01-15\n---\n\n"
            "## User Scenarios\n\n## Acceptance Criteria\n\n"
            "## Functional Requirements\n\n## Edge Cases\n",
        )
        result = validate_file(path, specs_root, default_config)
        actions = fix_file(path, result, specs_root, default_config)
        descriptions = [a.description for a in actions]
        assert any("P2" in d for d in descriptions)

        post = frontmatter.load(str(path))
        assert post["priority"] == "P2"


class TestFixEmptyTitle:
    """Fixes empty title from folder name."""

    def test_fixes_title_from_folder(
        self, specs_root: Path, default_config: ValidatorConfig
    ) -> None:
        path = _make_spec(
            specs_root,
            "---\ntitle: ''\nstatus: Draft\npriority: P1\n"
            "created: 2026-01-01\nupdated: 2026-01-15\n---\n\n"
            "## User Scenarios\n\n## Acceptance Criteria\n\n"
            "## Functional Requirements\n\n## Edge Cases\n",
        )
        result = validate_file(path, specs_root, default_config)
        actions = fix_file(path, result, specs_root, default_config)
        descriptions = [a.description for a in actions]
        assert any("title" in d.lower() for d in descriptions)

        post = frontmatter.load(str(path))
        # Folder is 001-test, so title should be "Test"
        assert post["title"].strip() != ""


class TestFixUpdatedBeforeCreated:
    """Fixes updated < created to today."""

    def test_fixes_updated_to_today(
        self, specs_root: Path, default_config: ValidatorConfig
    ) -> None:
        path = _make_spec(
            specs_root,
            "---\ntitle: Test\nstatus: Draft\npriority: P1\n"
            "created: 2026-04-01\nupdated: 2026-01-01\n---\n\n"
            "## User Scenarios\n\n## Acceptance Criteria\n\n"
            "## Functional Requirements\n\n## Edge Cases\n",
        )
        result = validate_file(path, specs_root, default_config)
        actions = fix_file(path, result, specs_root, default_config)
        descriptions = [a.description for a in actions]
        assert any("updated" in d.lower() for d in descriptions)

        post = frontmatter.load(str(path))
        assert post["updated"] >= post["created"]


class TestFixMissingSections:
    """Injects missing section skeletons."""

    def test_injects_missing_sections(
        self, specs_root: Path, default_config: ValidatorConfig
    ) -> None:
        path = _make_spec(
            specs_root,
            "---\ntitle: Test\nstatus: Draft\npriority: P1\n"
            "created: 2026-01-01\nupdated: 2026-01-15\n---\n\n"
            "## User Scenarios\n\nContent.\n",
        )
        result = validate_file(path, specs_root, default_config)
        actions = fix_file(path, result, specs_root, default_config)
        descriptions = [a.description for a in actions]
        assert any("skeleton" in d.lower() for d in descriptions)

        content = path.read_text()
        assert "Acceptance Criteria" in content
        assert "Functional Requirements" in content
        assert "Edge Cases" in content


class TestDryRun:
    """Dry run mode does not modify files."""

    def test_dry_run_no_modification(
        self, specs_root: Path, default_config: ValidatorConfig
    ) -> None:
        path = _make_spec(
            specs_root,
            "---\ntitle: Test\nstatus: WIP\npriority: P1\n"
            "created: 2026-01-01\nupdated: 2026-01-15\n---\n\n"
            "## User Scenarios\n\n## Acceptance Criteria\n\n"
            "## Functional Requirements\n\n## Edge Cases\n",
        )
        original_content = path.read_text()
        result = validate_file(path, specs_root, default_config)
        actions = fix_file(path, result, specs_root, default_config, dry_run=True)

        # Actions are returned but file is unchanged
        assert len(actions) > 0
        assert path.read_text() == original_content


class TestBackupHandling:
    """Backup creation and removal."""

    def test_no_bak_remains_after_fix(
        self, specs_root: Path, default_config: ValidatorConfig
    ) -> None:
        path = _make_spec(
            specs_root,
            "---\ntitle: Test\nstatus: WIP\npriority: P1\n"
            "created: 2026-01-01\nupdated: 2026-01-15\n---\n\n"
            "## User Scenarios\n\n## Acceptance Criteria\n\n"
            "## Functional Requirements\n\n## Edge Cases\n",
        )
        result = validate_file(path, specs_root, default_config)
        fix_file(path, result, specs_root, default_config)

        bak = path.with_suffix(".md.bak")
        assert not bak.exists()


class TestNoFixNeeded:
    """Files without errors get no actions."""

    def test_valid_file_returns_empty(
        self, valid_spec_path: Path, specs_root: Path, default_config: ValidatorConfig
    ) -> None:
        result = validate_file(valid_spec_path, specs_root, default_config)
        actions = fix_file(valid_spec_path, result, specs_root, default_config)
        assert actions == []
