# LiveSpec traceability anchors
# @spec(FR-004)

"""Integration checks for the built-in Rust driver manifest."""

# @spec FR-004: Integration tests for the Rust driver
# — .specs/features/021-driver-rust/spec.md#fr-004

from __future__ import annotations

from pathlib import Path

from tests.integration.helpers.driver_manifests import load_builtin_manifest, referenced_scripts
from validator.drivers.registry import DriverRegistry


def test_registry_discovers_rust_driver_from_cargo_toml(tmp_path: Path) -> None:
    """Driver discovery matches projects that ship a ``Cargo.toml``."""
    # @spec AC-001 — .specs/features/021-driver-rust/spec.md#ac-001
    (tmp_path / "Cargo.toml").write_text(
        '[package]\nname = "x"\nversion = "0.1.0"\n', encoding="utf-8"
    )

    drivers = DriverRegistry(tmp_path).discover()

    assert "rust" in [driver.name for driver in drivers]


def test_rust_manifest_validates_with_native_commands_only() -> None:
    """The YAML validates, declares all four capabilities and needs no gate script."""
    # @spec AC-002, AC-009, SC-001, SC-002 — .specs/features/021-driver-rust/spec.md#ac-009
    manifest = load_builtin_manifest("rust")

    assert manifest.name == "rust"
    assert manifest.implemented_capabilities() == [
        "coverage",
        "snapshots",
        "properties",
        "mutation",
    ]
    assert referenced_scripts(manifest) == []
