# LiveSpec traceability anchors
# @spec(FR-002)

"""Detect the Python module target used by the built-in driver."""

# @spec FR-002: Module auto-detection logic — .specs/features/017-driver-python/spec.md#fr-002

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any, cast

_MODULE_NAME_PATTERN = re.compile(r"[^a-zA-Z0-9_]")
_TEST_DIRECTORY_NAMES = {"test", "tests"}


def _normalize_module_name(raw_name: str) -> str:
    """Convert a project or directory name into a valid module identifier.

    Args:
        raw_name: Project-facing package name from metadata or the filesystem.

    Returns:
        A snake_case-like module identifier safe for coverage configuration.
    """
    normalized_name = _MODULE_NAME_PATTERN.sub("_", raw_name.strip().lower())
    return normalized_name.strip("_") or "python_project"


def detect_python_module(project_root: str) -> str:
    """Auto-detect the Python module to measure for coverage.

    Args:
        project_root: Path to the Python project root.

    Returns:
        The inferred module or package name used in coverage commands.
    """
    project_root_path = Path(project_root)
    pyproject_path = project_root_path / "pyproject.toml"

    if pyproject_path.exists():
        try:
            with pyproject_path.open("rb") as pyproject_file:
                pyproject_data = tomllib.load(pyproject_file)
        except (OSError, tomllib.TOMLDecodeError):
            pyproject_data = {}

        testpaths = cast(
            list[Any],
            pyproject_data.get("tool", {})
            .get("pytest", {})
            .get("ini_options", {})
            .get("testpaths", []),
        )
        for testpath in testpaths:
            if isinstance(testpath, str):
                candidate_name = Path(testpath).name
                # Ignore conventional tests directories because coverage must
                # target application code rather than the test tree itself.
                if candidate_name and candidate_name not in _TEST_DIRECTORY_NAMES:
                    return _normalize_module_name(candidate_name)

        project_name = pyproject_data.get("project", {}).get("name")
        if isinstance(project_name, str) and project_name.strip():
            return _normalize_module_name(project_name)

    src_dir = project_root_path / "src"
    if src_dir.is_dir():
        return "src"

    return _normalize_module_name(project_root_path.name)
