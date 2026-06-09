# LiveSpec traceability anchors
# @spec(FR-004)

"""Integration checks for the built-in Rust driver manifest."""

# @spec FR-004: Integration tests for the Rust driver
# — .specs/features/021-driver-rust/spec.md#fr-004

from __future__ import annotations

import tempfile
from pathlib import Path

from validator.drivers.loader import load_manifest
from validator.drivers.registry import DriverRegistry
from validator.drivers.rust_detector import (
    has_cargo_dependency,
    parse_cargo_dependencies,
)
from validator.drivers.schemas import DriverManifest

_RUST_DRIVER_PATH = Path(__file__).resolve().parents[2] / "livespec" / "drivers" / "rust.yaml"


def _load_rust_manifest() -> DriverManifest:
    """Load the checked-in Rust driver manifest for assertions."""
    manifest = load_manifest(_RUST_DRIVER_PATH)
    assert manifest is not None
    return manifest


def test_registry_loads_rust_driver() -> None:
    """Driver discovery matches projects that ship a ``Cargo.toml``."""
    # @spec AC-001 — .specs/features/021-driver-rust/spec.md#ac-001
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "Cargo.toml").write_text(
            '[package]\nname = "x"\nversion = "0.1.0"\n', encoding="utf-8"
        )

        registry = DriverRegistry(project_root)
        drivers = registry.discover()

    assert any(driver.name == "rust" for driver in drivers)


def test_rust_driver_schema_validation() -> None:
    """The committed Rust driver YAML validates against the schema."""
    # @spec AC-009 — .specs/features/021-driver-rust/spec.md#ac-009
    manifest = _load_rust_manifest()

    assert manifest.name == "rust"
    # All four capabilities are implemented natively.
    assert manifest.coverage is not None
    assert manifest.snapshots is not None
    assert manifest.properties is not None
    assert manifest.mutation is not None


def test_rust_driver_capabilities_exist() -> None:
    """The manifest advertises all 4 standard capabilities."""
    # @spec SC-002 — Rust is the only stack with full capability coverage
    manifest = _load_rust_manifest()

    assert manifest.implemented_capabilities() == [
        "coverage",
        "snapshots",
        "properties",
        "mutation",
    ]


def test_rust_driver_detects_cargo_toml() -> None:
    """``Cargo.toml`` is the only detect rule."""
    # @spec AC-001
    manifest = _load_rust_manifest()

    assert "Cargo.toml" in manifest.detect.files


def test_coverage_capability_uses_native_command() -> None:
    """Coverage capability uses native ``cargo llvm-cov`` — no escape-hatch script."""
    # @spec AC-002, SC-001 — no script, native --fail-under-lines flag
    manifest = _load_rust_manifest()
    coverage_capability = manifest.coverage

    assert coverage_capability is not None
    # SC-001: no escape hatch script.
    assert coverage_capability.script is None
    assert coverage_capability.command is not None
    assert "cargo llvm-cov" in coverage_capability.command
    # AC-002: native --fail-under-lines flag must be wired.
    assert "--fail-under-lines" in coverage_capability.command
    # Native lcov output flags must be present.
    assert "--lcov" in coverage_capability.command
    assert "--output-path" in coverage_capability.command
    assert coverage_capability.report_path == "lcov.info"
    assert coverage_capability.threshold == 80


def test_snapshots_capability_metadata() -> None:
    """Snapshots capability runs ``cargo insta test`` with stale-snap rejection."""
    # @spec AC-004, AC-005
    manifest = _load_rust_manifest()
    snapshots_capability = manifest.snapshots

    assert snapshots_capability is not None
    assert snapshots_capability.command is not None
    assert "cargo insta test" in snapshots_capability.command
    # --unreferenced=reject ensures stale snapshots fail the run.
    assert "--unreferenced=reject" in snapshots_capability.command


def test_properties_capability_metadata() -> None:
    """Properties capability runs ``cargo test``."""
    # @spec AC-006
    manifest = _load_rust_manifest()
    properties_capability = manifest.properties

    assert properties_capability is not None
    assert properties_capability.command is not None
    assert "cargo test" in properties_capability.command


def test_mutation_capability_metadata() -> None:
    """Mutation capability runs ``cargo mutants --json``."""
    # @spec AC-007, AC-008
    manifest = _load_rust_manifest()
    mutation_capability = manifest.mutation

    assert mutation_capability is not None
    assert mutation_capability.command is not None
    assert "cargo mutants" in mutation_capability.command
    # --json output is what the JSON parser consumes.
    assert "--json" in mutation_capability.command


def test_dependency_detection_in_fixture_cargo_project() -> None:
    """A Cargo fixture exposes its dependencies through the parser."""
    # @spec AC-004, AC-006, AC-010
    cargo_toml = """[package]
name = "fixture"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = "1.0"

[dev-dependencies]
insta = "1.34"
proptest = { version = "1.4", default-features = false }
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "Cargo.toml").write_text(cargo_toml, encoding="utf-8")

        deps = parse_cargo_dependencies(str(project_root))

        assert "insta" in deps
        assert "proptest" in deps
        assert "serde" in deps
        assert has_cargo_dependency(str(project_root), "INSTA") is True
        assert has_cargo_dependency(str(project_root), "Proptest") is True
        assert has_cargo_dependency(str(project_root), "quickcheck") is False


def test_dependency_detection_proptest_takes_priority_over_quickcheck() -> None:
    """When both libraries are declared, callers can prefer proptest."""
    # @spec AC-006 — proptest preferred over quickcheck per spec Story 3
    cargo_toml = """[package]
name = "fixture"
version = "0.1.0"

[dev-dependencies]
proptest = "1.4"
quickcheck = "1.0"
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "Cargo.toml").write_text(cargo_toml, encoding="utf-8")

        deps = parse_cargo_dependencies(str(project_root))

        # Both detected; downstream callers consult them in spec priority order.
        assert "proptest" in deps
        assert "quickcheck" in deps
        # proptest appears before quickcheck in [dev-dependencies] order.
        assert deps.index("proptest") < deps.index("quickcheck")
