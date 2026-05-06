# @spec FR-003, FR-004: Syrupy detection and first-run detection
# — .specs/features/017-driver-python/spec.md#fr-003
"""
Syrupy installation detection and snapshot baseline checking.
"""

import subprocess
from pathlib import Path


def is_syrupy_installed() -> bool:
    """
    Check if syrupy is installed in the current environment.

    Returns:
        True if syrupy is installed, False otherwise
    """
    try:
        result = subprocess.run(
            ["pip", "show", "syrupy"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0 and "Name: syrupy" in result.stdout
    except Exception:
        return False


def has_snapshots(project_root: str) -> bool:
    """
    Check if snapshot baselines exist in the project.

    Looks for any .ambr files in __snapshots__/ directories.

    Args:
        project_root: Path to the project root

    Returns:
        True if snapshot files are found, False otherwise
    """
    project_root_path = Path(project_root)

    # Search for __snapshots__/ directories and .ambr files
    try:
        snapshots = list(project_root_path.glob("**/__snapshots__/*.ambr"))
        return len(snapshots) > 0
    except Exception:
        return False
