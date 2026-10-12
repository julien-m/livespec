# LiveSpec traceability anchors
# @spec(FR-005)

"""Integration checks for the built-in Swift driver manifest."""

# @spec FR-005: Integration tests for the Swift driver
# — .specs/features/019-driver-swift/spec.md#fr-005

from __future__ import annotations

import os
from pathlib import Path

from tests.integration.helpers.driver_manifests import load_builtin_manifest, referenced_scripts
from validator.drivers.registry import DriverRegistry


def test_registry_discovers_swift_driver_from_package_swift(tmp_path: Path) -> None:
    """Driver discovery matches projects that ship a ``Package.swift``."""
    # @spec AC-001 — .specs/features/019-driver-swift/spec.md#ac-001
    (tmp_path / "Package.swift").write_text("// swift", encoding="utf-8")

    drivers = DriverRegistry(tmp_path).discover()

    assert "swift" in [driver.name for driver in drivers]


def test_xcode_only_project_does_not_match_swift_driver(tmp_path: Path) -> None:
    """A project with only an ``.xcodeproj`` does not trigger the SwiftPM driver."""
    # @spec AC-004
    (tmp_path / "MyApp.xcodeproj").mkdir()

    drivers = DriverRegistry(tmp_path).discover()

    assert "swift" not in [driver.name for driver in drivers]


def test_swift_manifest_validates_with_all_four_capabilities() -> None:
    """The committed YAML validates and declares the four Swift capabilities."""
    # @spec AC-009 — .specs/features/019-driver-swift/spec.md#ac-009
    manifest = load_builtin_manifest("swift")

    assert manifest.name == "swift"
    assert manifest.implemented_capabilities() == [
        "coverage",
        "snapshots",
        "properties",
        "mutation",
    ]


def test_swift_manifest_scripts_are_shipped_and_executable() -> None:
    """The coverage gate script referenced by the manifest is shipped and executable."""
    # @spec AC-002, AC-008
    scripts = referenced_scripts(load_builtin_manifest("swift"))

    assert [script.name for script in scripts] == ["swift-coverage-gate.sh"]
    for script in scripts:
        assert script.is_file(), f"missing: {script}"
        assert os.access(script, os.X_OK), f"not executable: {script}"
