# @spec FR-007: Unit tests for module detection — .specs/features/017-driver-python/spec.md#fr-007
"""
Unit tests for Python module auto-detection.
"""

import tempfile
from pathlib import Path

import pytest

from validator.drivers.python_detector import detect_python_module


def test_detect_python_module_from_pyproject_toml_name():
    """Test detection from [project].name in pyproject.toml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyproject_path = Path(tmpdir) / "pyproject.toml"
        pyproject_path.write_text('[project]\nname = "my-awesome-app"\n')

        module = detect_python_module(tmpdir)
        assert module == "my_awesome_app"


def test_detect_python_module_from_src_directory():
    """Test detection falls back to src/ if it exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = Path(tmpdir) / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text("")

        module = detect_python_module(tmpdir)
        assert module == "src"


def test_detect_python_module_fallback_to_directory_name():
    """Test fallback to directory name when no other detection works."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a directory with a specific name
        test_dir = Path(tmpdir) / "myproject"
        test_dir.mkdir()

        module = detect_python_module(str(test_dir))
        assert module == "myproject"


def test_detect_python_module_invalid_pyproject():
    """Test graceful handling of malformed pyproject.toml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyproject_path = Path(tmpdir) / "pyproject.toml"
        pyproject_path.write_text("invalid toml content {{{")

        # Should fall back to directory name
        module = detect_python_module(tmpdir)
        # Just verify it returns something without crashing
        assert isinstance(module, str)
        assert len(module) > 0
