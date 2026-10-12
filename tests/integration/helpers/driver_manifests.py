"""Shared access to the built-in driver manifests for driver integration tests."""

from __future__ import annotations

from pathlib import Path

from validator.drivers.loader import load_manifest
from validator.drivers.schemas import DriverManifest

BUILTIN_DRIVERS_DIR = Path(__file__).resolve().parents[3] / "livespec" / "drivers"


def load_builtin_manifest(name: str) -> DriverManifest:
    """Load ``livespec/drivers/<name>.yaml`` through the production loader.

    Args:
        name: Built-in driver name (manifest file stem).

    Returns:
        The schema-validated manifest.
    """
    manifest = load_manifest(BUILTIN_DRIVERS_DIR / f"{name}.yaml")
    assert manifest is not None, f"{name}.yaml failed schema validation"
    return manifest


def referenced_scripts(manifest: DriverManifest) -> list[Path]:
    """Return the shipped script paths referenced by a built-in manifest.

    Args:
        manifest: Built-in driver manifest.

    Returns:
        Script paths resolved against the built-in drivers directory.
    """
    scripts: list[Path] = []
    for name in manifest.implemented_capabilities():
        capability = manifest.get_capability(name)
        if capability is not None and capability.script:
            scripts.append(BUILTIN_DRIVERS_DIR / capability.script)
    return scripts
