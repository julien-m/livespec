"""Shared fixtures for LiveSpec validator tests."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from validator.config import ValidatorConfig

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def specs_root(tmp_path: Path) -> Path:
    """Create a minimal .specs/ structure with a feature subdirectory."""
    root = tmp_path / ".specs"
    root.mkdir()
    (root / "features").mkdir()
    (root / "features" / "001-test").mkdir()
    (root / "stacks").mkdir()
    return root


@pytest.fixture
def valid_spec_path(specs_root: Path) -> Path:
    """Copy valid_spec.md fixture into specs_root/features/001-test/spec.md."""
    dst = specs_root / "features" / "001-test" / "spec.md"
    shutil.copy2(FIXTURES_DIR / "valid_spec.md", dst)
    return dst


@pytest.fixture
def invalid_spec_path(specs_root: Path) -> Path:
    """Copy invalid_spec.md fixture into specs_root/features/001-test/spec.md."""
    dst = specs_root / "features" / "001-test" / "spec.md"
    shutil.copy2(FIXTURES_DIR / "invalid_spec.md", dst)
    return dst


@pytest.fixture
def valid_plan_path(specs_root: Path) -> Path:
    """Copy valid_plan.md fixture into specs_root/features/001-test/plan.md."""
    dst = specs_root / "features" / "001-test" / "plan.md"
    shutil.copy2(FIXTURES_DIR / "valid_plan.md", dst)
    return dst


@pytest.fixture
def invalid_plan_path(specs_root: Path) -> Path:
    """Copy invalid_plan.md fixture into specs_root/features/001-test/plan.md."""
    dst = specs_root / "features" / "001-test" / "plan.md"
    shutil.copy2(FIXTURES_DIR / "invalid_plan.md", dst)
    return dst


@pytest.fixture
def valid_implementation_path(specs_root: Path) -> Path:
    """Copy valid_implementation.md fixture."""
    dst = specs_root / "features" / "001-test" / "implementation.md"
    shutil.copy2(FIXTURES_DIR / "valid_implementation.md", dst)
    return dst


@pytest.fixture
def valid_roadmap_path(specs_root: Path) -> Path:
    """Copy valid_roadmap.md fixture."""
    dst = specs_root / "features" / "001-test" / "roadmap.md"
    shutil.copy2(FIXTURES_DIR / "valid_roadmap.md", dst)
    return dst


@pytest.fixture
def invalid_roadmap_path(specs_root: Path) -> Path:
    """Copy invalid_roadmap.md fixture."""
    dst = specs_root / "features" / "001-test" / "roadmap.md"
    shutil.copy2(FIXTURES_DIR / "invalid_roadmap.md", dst)
    return dst


@pytest.fixture
def valid_changelog_path(specs_root: Path) -> Path:
    """Copy valid_changelog.md fixture."""
    dst = specs_root / "features" / "001-test" / "changelog.md"
    shutil.copy2(FIXTURES_DIR / "valid_changelog.md", dst)
    return dst


@pytest.fixture
def invalid_changelog_path(specs_root: Path) -> Path:
    """Copy invalid_changelog.md fixture."""
    dst = specs_root / "features" / "001-test" / "changelog.md"
    shutil.copy2(FIXTURES_DIR / "invalid_changelog.md", dst)
    return dst


@pytest.fixture
def valid_stack_path(specs_root: Path) -> Path:
    """Copy valid_stack.md fixture into stacks/_default.md."""
    dst = specs_root / "stacks" / "_default.md"
    shutil.copy2(FIXTURES_DIR / "valid_stack.md", dst)
    return dst


@pytest.fixture
def valid_preflight_path(specs_root: Path) -> Path:
    """Copy valid_preflight.md fixture."""
    dst = specs_root / "features" / "001-test" / "preflight.md"
    shutil.copy2(FIXTURES_DIR / "valid_preflight.md", dst)
    return dst


@pytest.fixture
def valid_constitution_path(specs_root: Path) -> Path:
    """Copy valid_constitution.md fixture."""
    dst = specs_root / "features" / "001-test" / "constitution.md"
    shutil.copy2(FIXTURES_DIR / "valid_constitution.md", dst)
    return dst


@pytest.fixture
def invalid_constitution_path(specs_root: Path) -> Path:
    """Copy invalid_constitution.md fixture."""
    dst = specs_root / "features" / "001-test" / "constitution.md"
    shutil.copy2(FIXTURES_DIR / "invalid_constitution.md", dst)
    return dst


@pytest.fixture
def valid_progress_path(specs_root: Path) -> Path:
    """Copy valid_progress.md fixture."""
    dst = specs_root / "features" / "001-test" / "progress.md"
    shutil.copy2(FIXTURES_DIR / "valid_progress.md", dst)
    return dst


@pytest.fixture
def default_config() -> ValidatorConfig:
    """Return a ValidatorConfig with all defaults."""
    return ValidatorConfig()
