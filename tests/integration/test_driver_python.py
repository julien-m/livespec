# LiveSpec traceability anchors
# @spec(FR-006)

"""Integration checks for the built-in Python driver manifest."""

# @spec FR-006: Integration tests for all 4 capabilities
# — .specs/features/017-driver-python/spec.md#fr-006

from __future__ import annotations

from pathlib import Path

from tests.integration.helpers.driver_manifests import load_builtin_manifest
from validator.drivers.registry import DriverRegistry


def test_registry_discovers_python_driver_from_pyproject(tmp_path: Path) -> None:
    """Driver discovery matches projects that include ``pyproject.toml``."""
    # @spec AC-001: Driver registry loads python.yaml
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n', encoding="utf-8")

    drivers = DriverRegistry(tmp_path).discover()

    assert "python" in [driver.name for driver in drivers]


def test_python_manifest_validates_with_all_four_capabilities() -> None:
    """The committed YAML validates and declares the four Python capabilities."""
    # @spec AC-011: Schema validation, AC-012: All 4 capabilities
    manifest = load_builtin_manifest("python")

    assert manifest.name == "python"
    assert manifest.implemented_capabilities() == [
        "coverage",
        "snapshots",
        "properties",
        "mutation",
    ]
