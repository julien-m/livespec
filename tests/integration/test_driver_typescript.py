"""Integration checks for the built-in TypeScript/JavaScript driver manifest."""

# @spec FR-005: Integration tests for the TS/JS driver
# — .specs/features/018-driver-typescript-javascript/spec.md#fr-005

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from validator.drivers.loader import load_manifest
from validator.drivers.registry import DriverRegistry
from validator.drivers.schemas import DriverManifest
from validator.drivers.typescript_detector import (
    detect_package_manager,
    detect_test_runner,
)

_TYPESCRIPT_DRIVER_PATH = (
    Path(__file__).resolve().parents[2] / "livespec" / "drivers" / "typescript.yaml"
)


def _load_typescript_manifest() -> DriverManifest:
    """Load the checked-in TS/JS driver manifest for assertions."""
    manifest = load_manifest(_TYPESCRIPT_DRIVER_PATH)
    assert manifest is not None
    return manifest


def test_registry_loads_typescript_driver() -> None:
    """Driver discovery matches projects that include ``package.json``."""
    # @spec AC-001 — .specs/features/018-driver-typescript-javascript/spec.md#ac-001
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "package.json").write_text(
            json.dumps({"name": "test"}),
            encoding="utf-8",
        )

        registry = DriverRegistry(project_root)
        drivers = registry.discover()

    assert any(driver.name == "typescript" for driver in drivers)


def test_typescript_driver_schema_validation() -> None:
    """The committed TS/JS driver YAML validates against the schema."""
    # @spec AC-011 — .specs/features/018-driver-typescript-javascript/spec.md#ac-011
    manifest = _load_typescript_manifest()

    assert manifest.name == "typescript"
    assert manifest.coverage is not None
    assert manifest.snapshots is not None
    assert manifest.properties is not None
    assert manifest.mutation is not None


def test_typescript_driver_capabilities_exist() -> None:
    """The manifest advertises all four TS/JS capabilities."""
    # @spec AC-012 — .specs/features/018-driver-typescript-javascript/spec.md#ac-012
    manifest = _load_typescript_manifest()

    assert manifest.implemented_capabilities() == [
        "coverage",
        "snapshots",
        "properties",
        "mutation",
    ]


def test_coverage_capability_metadata() -> None:
    """Coverage capability declares its lcov report path and threshold."""
    # @spec AC-003, AC-004
    manifest = _load_typescript_manifest()
    coverage_capability = manifest.coverage

    assert coverage_capability is not None
    assert coverage_capability.command is not None
    assert "lcov" in coverage_capability.command
    assert coverage_capability.report_path == "coverage/lcov.info"
    assert coverage_capability.threshold == 80


def test_snapshots_capability_metadata() -> None:
    """Snapshot capability runs the test runner."""
    # @spec AC-005
    manifest = _load_typescript_manifest()
    snapshots_capability = manifest.snapshots

    assert snapshots_capability is not None
    assert snapshots_capability.command is not None


def test_properties_capability_metadata() -> None:
    """Properties capability runs the test runner."""
    # @spec AC-008
    manifest = _load_typescript_manifest()
    properties_capability = manifest.properties

    assert properties_capability is not None
    assert properties_capability.command is not None


def test_mutation_capability_metadata() -> None:
    """Mutation capability points at Stryker's default JSON report."""
    # @spec AC-009, AC-010
    manifest = _load_typescript_manifest()
    mutation_capability = manifest.mutation

    assert mutation_capability is not None
    assert mutation_capability.command is not None
    assert "stryker" in mutation_capability.command
    assert mutation_capability.report_path == "reports/mutation/mutation.json"


def test_typescript_driver_detects_package_json() -> None:
    """Detect rule includes ``package.json`` per AC-001."""
    manifest = _load_typescript_manifest()

    assert "package.json" in manifest.detect.files


def test_runner_detection_in_fixture_vitest() -> None:
    """A fixture project with a vitest config resolves to vitest."""
    # @spec AC-002
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "package.json").write_text(
            json.dumps({"name": "fixture-vitest"}),
            encoding="utf-8",
        )
        (project_root / "vitest.config.ts").write_text(
            "export default {}",
            encoding="utf-8",
        )

        assert detect_test_runner(str(project_root)) == "vitest"


def test_runner_detection_in_fixture_jest() -> None:
    """A fixture project with only a jest config resolves to jest."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "package.json").write_text(
            json.dumps({"name": "fixture-jest"}),
            encoding="utf-8",
        )
        (project_root / "jest.config.js").write_text(
            "module.exports = {}",
            encoding="utf-8",
        )

        assert detect_test_runner(str(project_root)) == "jest"


def test_package_manager_detection_in_fixture_pnpm() -> None:
    """A fixture project with ``pnpm-lock.yaml`` resolves to pnpm."""
    # @spec FR-004
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "package.json").write_text(
            json.dumps({"name": "fixture-pnpm"}),
            encoding="utf-8",
        )
        (project_root / "pnpm-lock.yaml").write_text("", encoding="utf-8")

        assert detect_package_manager(str(project_root)) == "pnpm"
