# LiveSpec traceability anchors
# @spec(FR-005)

"""Integration checks for the built-in Swift driver manifest."""

# @spec FR-005: Integration tests for the Swift driver
# — .specs/features/019-driver-swift/spec.md#fr-005

from __future__ import annotations

import tempfile
from pathlib import Path

from validator.drivers.loader import load_manifest
from validator.drivers.registry import DriverRegistry
from validator.drivers.schemas import DriverManifest
from validator.drivers.swift_detector import (
    has_swift_dependency,
    parse_package_dependencies,
)

_SWIFT_DRIVER_PATH = Path(__file__).resolve().parents[2] / "livespec" / "drivers" / "swift.yaml"
_GATE_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "livespec"
    / "drivers"
    / "scripts"
    / "swift-coverage-gate.sh"
)


def _load_swift_manifest() -> DriverManifest:
    """Load the checked-in Swift driver manifest for assertions."""
    manifest = load_manifest(_SWIFT_DRIVER_PATH)
    assert manifest is not None
    return manifest


def test_registry_loads_swift_driver() -> None:
    """Driver discovery matches projects that ship a ``Package.swift``."""
    # @spec AC-001 — .specs/features/019-driver-swift/spec.md#ac-001
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "Package.swift").write_text("// swift", encoding="utf-8")

        registry = DriverRegistry(project_root)
        drivers = registry.discover()

    assert any(driver.name == "swift" for driver in drivers)


def test_swift_driver_schema_validation() -> None:
    """The committed Swift driver YAML validates against the schema."""
    # @spec AC-009 — .specs/features/019-driver-swift/spec.md#ac-009
    manifest = _load_swift_manifest()

    assert manifest.name == "swift"
    assert manifest.coverage is not None
    assert manifest.snapshots is not None
    assert manifest.properties is not None
    assert manifest.mutation is not None


def test_swift_driver_capabilities_exist() -> None:
    """The manifest advertises all four Swift capabilities in canonical order."""
    manifest = _load_swift_manifest()

    assert manifest.implemented_capabilities() == [
        "coverage",
        "snapshots",
        "properties",
        "mutation",
    ]


def test_swift_driver_detects_package_swift() -> None:
    """``Package.swift`` is the only detect rule — Xcode-only projects skip."""
    # @spec AC-001
    manifest = _load_swift_manifest()

    assert "Package.swift" in manifest.detect.files


def test_coverage_capability_uses_script_escape_hatch() -> None:
    """Coverage capability is wired to the gate script, not a raw command."""
    # @spec AC-002, AC-003, AC-008
    manifest = _load_swift_manifest()
    coverage_capability = manifest.coverage

    assert coverage_capability is not None
    # Escape-hatch contract: script set, command absent.
    assert coverage_capability.command is None
    assert coverage_capability.script == "scripts/swift-coverage-gate.sh"
    assert coverage_capability.report_path == ".build/coverage/lcov.info"
    assert coverage_capability.threshold == 75


def test_coverage_gate_script_is_shipped_and_executable() -> None:
    """The script referenced by the manifest is present on disk and executable."""
    # @spec AC-008
    import os

    assert _GATE_SCRIPT_PATH.is_file()
    assert os.access(_GATE_SCRIPT_PATH, os.X_OK)


def test_snapshots_capability_metadata() -> None:
    """Snapshots capability runs ``swift test``."""
    # @spec AC-005
    manifest = _load_swift_manifest()
    snapshots_capability = manifest.snapshots

    assert snapshots_capability is not None
    assert snapshots_capability.command is not None
    assert "swift test" in snapshots_capability.command


def test_properties_capability_metadata() -> None:
    """Properties capability runs ``swift test`` (filtered)."""
    # @spec AC-006
    manifest = _load_swift_manifest()
    properties_capability = manifest.properties

    assert properties_capability is not None
    assert properties_capability.command is not None
    assert "swift test" in properties_capability.command


def test_mutation_capability_metadata() -> None:
    """Mutation capability invokes ``muter``."""
    # @spec AC-007
    manifest = _load_swift_manifest()
    mutation_capability = manifest.mutation

    assert mutation_capability is not None
    assert mutation_capability.command is not None
    assert "muter" in mutation_capability.command


def test_xcode_only_project_does_not_match_swift_driver() -> None:
    """A project with only an .xcodeproj does not trigger the SwiftPM driver.

    The gate script handles the graceful Xcode message itself; the registry
    only matches when ``Package.swift`` is present per AC-001.
    """
    # @spec AC-004
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "MyApp.xcodeproj").mkdir()

        registry = DriverRegistry(project_root)
        drivers = registry.discover()

    assert not any(driver.name == "swift" for driver in drivers)


def test_dependency_detection_in_fixture_swiftpm() -> None:
    """A SwiftPM fixture exposes its dependencies through the parser."""
    # @spec AC-005, AC-006, AC-010 — .specs/features/019-driver-swift/spec.md#ac-010
    package_swift = """\
// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "FixtureApp",
    dependencies: [
        .package(url: "https://github.com/pointfreeco/swift-snapshot-testing.git", from: "1.15.0"),
        .package(url: "https://github.com/typelift/SwiftCheck", from: "0.12.0"),
    ],
    targets: []
)
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "Package.swift").write_text(package_swift, encoding="utf-8")

        deps = parse_package_dependencies(str(project_root))

        assert "swift-snapshot-testing" in deps
        assert "swiftcheck" in deps
        assert has_swift_dependency(str(project_root), "swift-snapshot-testing") is True
        assert has_swift_dependency(str(project_root), "SwiftCheck") is True
