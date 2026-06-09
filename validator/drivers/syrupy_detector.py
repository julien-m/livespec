# LiveSpec traceability anchors
# @spec(FR-003)
# @spec(FR-004)

"""Detect syrupy availability and existing snapshot baselines."""

# @spec FR-003, FR-004: Syrupy detection and first-run detection
# — .specs/features/017-driver-python/spec.md#fr-003

from __future__ import annotations

import subprocess
from pathlib import Path


def is_syrupy_installed() -> bool:
    """Check whether syrupy is available in the current Python environment.

    Returns:
        ``True`` when ``pip show syrupy`` reports an installed package.
    """
    try:
        # This subprocess contract is intentionally narrow: stdout must contain
        # the package name and exit code 0 means the environment can run syrupy.
        result = subprocess.run(
            ["pip", "show", "syrupy"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.SubprocessError, OSError):
        return False

    return result.returncode == 0 and "Name: syrupy" in result.stdout


def has_snapshots(project_root: str) -> bool:
    """Check whether the project already has syrupy baseline snapshots.

    Args:
        project_root: Path to the project root.

    Returns:
        ``True`` when at least one ``.ambr`` snapshot file exists.
    """
    project_root_path = Path(project_root)

    try:
        return any(project_root_path.glob("**/__snapshots__/*.ambr"))
    except OSError:
        return False
