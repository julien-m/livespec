"""Run ``scripts/generate-surfaces.js`` in dry-run mode and parse what it would write."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "generate-surfaces.js"
_DRY_RUN_MARKER = "[DRY RUN] Would "


def run_surfaces_script(project_dir: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    """Run the generator with ``--dry-run`` from ``project_dir``.

    Args:
        project_dir: Synthetic project root used as the working directory.
        *extra_args: Additional CLI flags such as ``--migrate-native``.

    Returns:
        The completed Node process.
    """
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; generate-surfaces.js cannot run")
    return subprocess.run(
        [node, str(SCRIPT_PATH), "--dry-run", *extra_args],
        cwd=project_dir,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def dry_run_surfaces(result: subprocess.CompletedProcess[str]) -> list[dict[str, Any]]:
    """Parse the surfaces the generator would create or append.

    Args:
        result: Successful dry-run process.

    Returns:
        Surface mappings from the YAML block after the dry-run marker, or an
        empty list when the generator reports nothing to write.
    """
    assert result.returncode == 0, f"generate-surfaces.js failed:\n{result.stderr}"
    _, marker, rest = result.stdout.partition(_DRY_RUN_MARKER)
    if not marker:
        return []
    document = yaml.safe_load(rest.split("\n", 1)[1])
    surfaces = document["surfaces"] if isinstance(document, dict) else document
    assert isinstance(surfaces, list), f"unexpected dry-run payload:\n{result.stdout}"
    return surfaces
