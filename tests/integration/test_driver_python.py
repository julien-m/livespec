# LiveSpec traceability anchors
# @spec(FR-006)

"""Integration checks for the built-in Python driver manifest."""

# @spec FR-006: Integration tests for all 4 capabilities
# — .specs/features/017-driver-python/spec.md#fr-006

from __future__ import annotations

import tempfile
from pathlib import Path

from validator.drivers.loader import load_manifest
from validator.drivers.registry import DriverRegistry
from validator.drivers.schemas import DriverManifest

_PYTHON_DRIVER_PATH = Path(__file__).resolve().parents[2] / "livespec" / "drivers" / "python.yaml"


def _load_python_manifest() -> DriverManifest:
    """Load the checked-in Python driver manifest for assertions.

    Returns:
        The validated Python driver manifest.
    """
    manifest = load_manifest(_PYTHON_DRIVER_PATH)
    assert manifest is not None
    return manifest


def test_registry_loads_python_driver() -> None:
    """Driver discovery should match projects that include ``pyproject.toml``."""
    # @spec AC-001: Driver registry loads python.yaml
    # — .specs/features/017-driver-python/spec.md#ac-001
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "pyproject.toml").write_text(
            '[project]\nname = "test"\n',
            encoding="utf-8",
        )

        registry = DriverRegistry(project_root)
        drivers = registry.discover()

    assert any(driver.name == "python" for driver in drivers)


def test_python_driver_schema_validation() -> None:
    """The committed Python driver YAML should validate against the schema."""
    # @spec AC-011: Schema validation
    # — .specs/features/017-driver-python/spec.md#ac-011
    manifest = _load_python_manifest()

    assert manifest.name == "python"
    assert manifest.coverage is not None
    assert manifest.snapshots is not None
    assert manifest.properties is not None
    assert manifest.mutation is not None


def test_python_driver_capabilities_exist() -> None:
    """The manifest should advertise all four Python capabilities."""
    # @spec AC-012: All 4 capabilities appear in spec-test output
    # — .specs/features/017-driver-python/spec.md#ac-012
    manifest = _load_python_manifest()

    assert manifest.implemented_capabilities() == [
        "coverage",
        "snapshots",
        "properties",
        "mutation",
    ]


def test_coverage_capability_metadata() -> None:
    """Coverage capability should include its command and report path."""
    # @spec AC-002: Coverage capability has proper metadata
    # — .specs/features/017-driver-python/spec.md#ac-002
    manifest = _load_python_manifest()
    coverage_capability = manifest.coverage

    assert coverage_capability is not None
    assert coverage_capability.command is not None
    assert coverage_capability.report_path == "lcov.info"
    assert coverage_capability.threshold == 80


def test_snapshots_capability_metadata() -> None:
    """Snapshot capability should expose an executable command."""
    manifest = _load_python_manifest()
    snapshots_capability = manifest.snapshots

    assert snapshots_capability is not None
    assert snapshots_capability.command is not None


def test_python_driver_detects_project_with_pyproject() -> None:
    """The detect rules should include ``pyproject.toml`` for Python projects."""
    manifest = _load_python_manifest()

    assert "pyproject.toml" in manifest.detect.files
