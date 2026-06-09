# LiveSpec traceability anchors
# @spec(FR-007)

"""Unit tests for Python module auto-detection."""

# @spec FR-007: Unit tests for module detection — .specs/features/017-driver-python/spec.md#fr-007

from __future__ import annotations

import tempfile
from pathlib import Path

from validator.drivers.python_detector import detect_python_module


def test_detect_python_module_from_pyproject_toml_name() -> None:
    """Detection should prefer ``[project].name`` metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyproject_path = Path(tmpdir) / "pyproject.toml"
        pyproject_path.write_text('[project]\nname = "my-awesome-app"\n', encoding="utf-8")

        module = detect_python_module(tmpdir)

    assert module == "my_awesome_app"


def test_detect_python_module_from_src_directory() -> None:
    """Detection should fall back to ``src`` when project metadata is absent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = Path(tmpdir) / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text("", encoding="utf-8")

        module = detect_python_module(tmpdir)

    assert module == "src"


def test_detect_python_module_fallback_to_directory_name() -> None:
    """Detection should use the directory name when no better signal exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir) / "myproject"
        test_dir.mkdir()

        module = detect_python_module(str(test_dir))

    assert module == "myproject"


def test_detect_python_module_invalid_pyproject() -> None:
    """Malformed ``pyproject.toml`` should not crash detection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyproject_path = Path(tmpdir) / "pyproject.toml"
        pyproject_path.write_text("invalid toml content {{{", encoding="utf-8")

        module = detect_python_module(tmpdir)

    assert isinstance(module, str)
    assert len(module) > 0
