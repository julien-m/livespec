"""Tests for validator.config — configuration loading and file type resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from validator.config import (
    ALL_TYPES,
    DEFAULT_EXCLUSIONS,
    ValidatorConfig,
    is_excluded,
    load_config,
    resolve_file_type,
)


class TestLoadConfig:
    """load_config from validator.yml or defaults."""

    def test_no_config_file_returns_defaults(self, specs_root: Path) -> None:
        config = load_config(specs_root)
        assert config.block_on == "error"
        assert config.validate_types == list(ALL_TYPES)
        assert config.exclude == list(DEFAULT_EXCLUSIONS)

    def test_parses_config_file(self, specs_root: Path) -> None:
        config_path = specs_root / "validator.yml"
        config_path.write_text(
            "block_on: warning\n"
            "validate:\n  - spec\n  - plan\n"
            "exclude:\n  - README.md\n  - draft/*.md\n"
        )
        config = load_config(specs_root)
        assert config.block_on == "warning"
        assert config.validate_types == ["spec", "plan"]
        assert config.exclude == ["README.md", "draft/*.md"]

    def test_invalid_yaml_returns_defaults(self, specs_root: Path) -> None:
        config_path = specs_root / "validator.yml"
        config_path.write_text("just a plain string\n")
        config = load_config(specs_root)
        assert config.block_on == "error"

    def test_partial_config_uses_defaults_for_missing(self, specs_root: Path) -> None:
        config_path = specs_root / "validator.yml"
        config_path.write_text("block_on: warning\n")
        config = load_config(specs_root)
        assert config.block_on == "warning"
        assert config.validate_types == list(ALL_TYPES)
        assert config.exclude == list(DEFAULT_EXCLUSIONS)


class TestIsExcluded:
    """Exclusion pattern matching."""

    def test_readme_excluded(self) -> None:
        config = ValidatorConfig()
        assert is_excluded("README.md", config)

    def test_feature_spec_not_excluded(self) -> None:
        config = ValidatorConfig()
        assert not is_excluded("features/001-auth/spec.md", config)

    def test_archive_excluded(self) -> None:
        config = ValidatorConfig()
        assert is_excluded("archive/old-spec.md", config)

    def test_nested_archive_excluded(self) -> None:
        config = ValidatorConfig()
        assert is_excluded("archive/v1/old.md", config)

    def test_custom_exclusion(self) -> None:
        config = ValidatorConfig(exclude=["draft/*.md"])
        assert is_excluded("draft/wip.md", config)
        assert not is_excluded("features/001/spec.md", config)

    @pytest.mark.parametrize(
        "path",
        [
            "stacks/decisions/adr-001.md",
            "features/001/logs/debug.md",
            "features/001/checks/ci.md",
            "design/mockups/home.md",
            "testing/unit.md",
            "hooks/pre-commit.md",
        ],
    )
    def test_default_exclusions(self, path: str) -> None:
        config = ValidatorConfig()
        assert is_excluded(path, config)


class TestResolveFileType:
    """File type resolution from path."""

    def test_feature_spec(self, specs_root: Path) -> None:
        path = specs_root / "features" / "001-auth" / "spec.md"
        assert resolve_file_type(path, specs_root) == "spec"

    def test_feature_plan(self, specs_root: Path) -> None:
        path = specs_root / "features" / "001-auth" / "plan.md"
        assert resolve_file_type(path, specs_root) == "plan"

    def test_feature_implementation(self, specs_root: Path) -> None:
        path = specs_root / "features" / "001-auth" / "implementation.md"
        assert resolve_file_type(path, specs_root) == "implementation"

    def test_stack_default(self, specs_root: Path) -> None:
        path = specs_root / "stacks" / "_default.md"
        assert resolve_file_type(path, specs_root) == "stack"

    def test_root_level_roadmap(self, specs_root: Path) -> None:
        path = specs_root / "roadmap.md"
        assert resolve_file_type(path, specs_root) == "roadmap"

    def test_root_level_changelog(self, specs_root: Path) -> None:
        path = specs_root / "changelog.md"
        assert resolve_file_type(path, specs_root) == "changelog"

    def test_outside_specs_root_returns_unknown(self, tmp_path: Path, specs_root: Path) -> None:
        path = tmp_path / "random.md"
        assert resolve_file_type(path, specs_root) == "unknown"
