# LiveSpec traceability anchors
# @spec(FR-004)

"""Integration checks for the built-in Go driver manifest."""

# @spec FR-004: Integration tests for the Go driver
# — .specs/features/020-driver-go/spec.md#fr-004

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from validator.drivers.go_detector import (
    has_go_dependency,
    parse_go_dependencies,
    parse_go_module,
)
from validator.drivers.loader import load_manifest
from validator.drivers.registry import DriverRegistry
from validator.drivers.schemas import DriverManifest

_GO_DRIVER_PATH = Path(__file__).resolve().parents[2] / "livespec" / "drivers" / "go.yaml"
_GATE_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "livespec" / "drivers" / "scripts" / "go-coverage-gate.sh"
)


def _load_go_manifest() -> DriverManifest:
    """Load the checked-in Go driver manifest for assertions."""
    manifest = load_manifest(_GO_DRIVER_PATH)
    assert manifest is not None
    return manifest


def test_registry_loads_go_driver() -> None:
    """Driver discovery matches projects that ship a ``go.mod``."""
    # @spec AC-001 — .specs/features/020-driver-go/spec.md#ac-001
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "go.mod").write_text("module example.com/x\n", encoding="utf-8")

        registry = DriverRegistry(project_root)
        drivers = registry.discover()

    assert any(driver.name == "go" for driver in drivers)


def test_go_driver_schema_validation() -> None:
    """The committed Go driver YAML validates against the schema."""
    # @spec AC-008 — .specs/features/020-driver-go/spec.md#ac-008
    manifest = _load_go_manifest()

    assert manifest.name == "go"
    assert manifest.coverage is not None
    assert manifest.snapshots is not None
    assert manifest.properties is not None
    # Mutation is intentionally absent (spec AC-006, Story 4).
    assert manifest.mutation is None


def test_go_driver_capabilities_exist() -> None:
    """The manifest advertises exactly 3 capabilities — mutation is omitted."""
    # @spec AC-006 — .specs/features/020-driver-go/spec.md#ac-006
    manifest = _load_go_manifest()

    assert manifest.implemented_capabilities() == [
        "coverage",
        "snapshots",
        "properties",
    ]


def test_go_driver_detects_go_mod() -> None:
    """``go.mod`` is the only detect rule."""
    # @spec AC-001
    manifest = _load_go_manifest()

    assert "go.mod" in manifest.detect.files


def test_coverage_capability_uses_script_escape_hatch() -> None:
    """Coverage capability is wired to the gate script, not a raw command."""
    # @spec AC-002, AC-003, AC-007
    manifest = _load_go_manifest()
    coverage_capability = manifest.coverage

    assert coverage_capability is not None
    assert coverage_capability.command is None
    assert coverage_capability.script == "scripts/go-coverage-gate.sh"
    assert coverage_capability.report_path == "coverage/lcov.info"
    assert coverage_capability.threshold == 70


def test_coverage_gate_script_is_shipped_and_executable() -> None:
    """The script referenced by the manifest is present on disk and executable."""
    # @spec AC-007
    assert _GATE_SCRIPT_PATH.is_file()
    assert os.access(_GATE_SCRIPT_PATH, os.X_OK)


def test_snapshots_capability_metadata() -> None:
    """Snapshots capability runs ``go test``."""
    # @spec AC-004
    manifest = _load_go_manifest()
    snapshots_capability = manifest.snapshots

    assert snapshots_capability is not None
    assert snapshots_capability.command is not None
    assert "go test" in snapshots_capability.command


def test_properties_capability_metadata() -> None:
    """Properties capability runs ``go test``."""
    # @spec AC-005
    manifest = _load_go_manifest()
    properties_capability = manifest.properties

    assert properties_capability is not None
    assert properties_capability.command is not None
    assert "go test" in properties_capability.command


def test_mutation_capability_is_absent() -> None:
    """Mutation is intentionally absent — runner surfaces ``not implemented``."""
    # @spec AC-006, Story 4
    manifest = _load_go_manifest()

    assert manifest.mutation is None
    assert "mutation" not in manifest.implemented_capabilities()


def test_dependency_detection_in_fixture_go_module() -> None:
    """A Go fixture exposes its dependencies through the parser."""
    # @spec AC-004, AC-005, AC-009
    go_mod = """module github.com/example/fixture

go 1.22

require (
\tgithub.com/leanovate/gopter v0.2.11
\tgithub.com/gkampitakis/go-snaps v0.5.4
)
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "go.mod").write_text(go_mod, encoding="utf-8")

        assert parse_go_module(str(project_root)) == "github.com/example/fixture"

        deps = parse_go_dependencies(str(project_root))

        assert "github.com/leanovate/gopter" in deps
        assert "github.com/gkampitakis/go-snaps" in deps
        assert has_go_dependency(str(project_root), "gopter") is True
        assert has_go_dependency(str(project_root), "GO-SNAPS") is True
        assert has_go_dependency(str(project_root), "cupaloy") is False
