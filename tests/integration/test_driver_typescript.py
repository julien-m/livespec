# LiveSpec traceability anchors
# @spec(FR-005)

"""Integration checks for the built-in TypeScript/JavaScript driver manifest."""

# @spec FR-005: Integration tests for the TS/JS driver
# — .specs/features/018-driver-typescript-javascript/spec.md#fr-005

from __future__ import annotations

import json
from pathlib import Path

from tests.integration.helpers.driver_manifests import load_builtin_manifest
from validator.drivers.registry import DriverRegistry


def test_registry_discovers_typescript_driver_from_package_json(tmp_path: Path) -> None:
    """Driver discovery matches projects that include ``package.json``."""
    # @spec AC-001
    (tmp_path / "package.json").write_text(json.dumps({"name": "test"}), encoding="utf-8")

    drivers = DriverRegistry(tmp_path).discover()

    assert "typescript" in [driver.name for driver in drivers]


def test_typescript_manifest_validates_with_all_four_capabilities() -> None:
    """The committed YAML validates and declares the four TS/JS capabilities."""
    # @spec AC-003, AC-009, AC-011
    manifest = load_builtin_manifest("typescript")

    assert manifest.name == "typescript"
    assert manifest.implemented_capabilities() == [
        "coverage",
        "snapshots",
        "properties",
        "mutation",
    ]
