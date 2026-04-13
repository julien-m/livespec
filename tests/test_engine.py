"""Tests for validator.engine — full validation pipeline."""

from __future__ import annotations

import shutil
from pathlib import Path

from validator.config import ValidatorConfig
from validator.engine import (
    collect_files,
    validate_all,
    validate_file,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestValidateFile:
    """validate_file full pipeline."""

    def test_valid_spec_no_errors(
        self, valid_spec_path: Path, specs_root: Path, default_config: ValidatorConfig
    ) -> None:
        result = validate_file(valid_spec_path, specs_root, default_config)
        assert result.file_type == "spec"
        assert not result.has_errors
        assert result.score == 100

    def test_invalid_spec_has_errors(
        self, invalid_spec_path: Path, specs_root: Path, default_config: ValidatorConfig
    ) -> None:
        result = validate_file(invalid_spec_path, specs_root, default_config)
        assert result.has_errors
        assert result.score < 100

    def test_valid_plan_no_errors(
        self, valid_plan_path: Path, specs_root: Path, default_config: ValidatorConfig
    ) -> None:
        result = validate_file(valid_plan_path, specs_root, default_config)
        assert result.file_type == "plan"
        assert not result.has_errors

    def test_unknown_type_skipped(self, specs_root: Path, default_config: ValidatorConfig) -> None:
        # Root-level files resolve to their stem; "weird_file" is not in
        # validate_types so validation is effectively skipped.
        unknown = specs_root / "weird_file.md"
        unknown.write_text("# Random\n")
        result = validate_file(unknown, specs_root, default_config)
        assert result.file_type == "weird_file"
        assert not result.has_errors

    def test_type_not_in_validate_types_skipped(
        self, valid_spec_path: Path, specs_root: Path
    ) -> None:
        config = ValidatorConfig(validate_types=["plan"])  # spec not included
        result = validate_file(valid_spec_path, specs_root, config)
        assert not result.has_errors
        assert result.score == 100  # untouched default


class TestScoreComputation:
    """Score deduction logic."""

    def test_score_deduction_per_error(
        self, invalid_spec_path: Path, specs_root: Path, default_config: ValidatorConfig
    ) -> None:
        result = validate_file(invalid_spec_path, specs_root, default_config)
        # Score = 100 - errors*20 - warnings*5, capped at 0
        expected = max(0, 100 - len(result.errors) * 20 - len(result.warnings) * 5)
        assert result.score == expected

    def test_score_never_negative(self, specs_root: Path, default_config: ValidatorConfig) -> None:
        # Create a spec with many errors
        bad = specs_root / "features" / "001-test" / "spec.md"
        bad.write_text("---\ntitle: ''\nstatus: bad\n---\n\nNo sections.\n")
        result = validate_file(bad, specs_root, default_config)
        assert result.score >= 0


class TestValidateAll:
    """validate_all multi-file orchestration."""

    def test_finds_and_validates_multiple_files(
        self, specs_root: Path, default_config: ValidatorConfig
    ) -> None:
        # Place multiple fixtures
        feat_dir = specs_root / "features" / "001-test"
        shutil.copy2(FIXTURES_DIR / "valid_spec.md", feat_dir / "spec.md")
        shutil.copy2(FIXTURES_DIR / "valid_plan.md", feat_dir / "plan.md")

        results, _excluded = validate_all(specs_root, default_config)
        assert len(results) >= 2
        types = [r.file_type for r in results]
        assert "spec" in types
        assert "plan" in types


class TestCollectFiles:
    """File collection with exclusions."""

    def test_exclusion_patterns(self, specs_root: Path, default_config: ValidatorConfig) -> None:
        # README.md is excluded by default
        readme = specs_root / "README.md"
        readme.write_text("# README\n")
        feat = specs_root / "features" / "001-test" / "spec.md"
        shutil.copy2(FIXTURES_DIR / "valid_spec.md", feat)

        files, excluded = collect_files(specs_root, default_config)
        excluded_names = [Path(e).name for e in excluded]
        assert "README.md" in excluded_names
        # spec.md should not be excluded
        assert any(f.name == "spec.md" for f in files)

    def test_archive_excluded(self, specs_root: Path, default_config: ValidatorConfig) -> None:
        archive = specs_root / "archive"
        archive.mkdir()
        (archive / "old.md").write_text("# Old\n")

        _files, excluded = collect_files(specs_root, default_config)
        assert any("archive" in e for e in excluded)

    def test_specific_path(
        self, valid_spec_path: Path, specs_root: Path, default_config: ValidatorConfig
    ) -> None:
        files, _ = collect_files(specs_root, default_config, paths=[valid_spec_path])
        assert len(files) == 1
        assert files[0] == valid_spec_path
