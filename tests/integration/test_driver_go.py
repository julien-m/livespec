# LiveSpec traceability anchors
# @spec(FR-004)

"""Integration checks for the built-in Go driver manifest."""

# @spec FR-004: Integration tests for the Go driver
# — .specs/features/020-driver-go/spec.md#fr-004

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.integration.helpers.driver_manifests import load_builtin_manifest, referenced_scripts
from validator.drivers.registry import DriverRegistry
from validator.drivers.runner import run_capability
from validator.drivers.schemas import CapabilityNotImplementedError


def test_registry_discovers_go_driver_from_go_mod(tmp_path: Path) -> None:
    """Driver discovery matches projects that ship a ``go.mod``."""
    # @spec AC-001 — .specs/features/020-driver-go/spec.md#ac-001
    (tmp_path / "go.mod").write_text("module example.com/x\n", encoding="utf-8")

    drivers = DriverRegistry(tmp_path).discover()

    assert "go" in [driver.name for driver in drivers]


def test_go_manifest_validates_with_three_capabilities() -> None:
    """The committed YAML validates and omits mutation on purpose."""
    # @spec AC-006, AC-008 — .specs/features/020-driver-go/spec.md#ac-008
    manifest = load_builtin_manifest("go")

    assert manifest.name == "go"
    assert manifest.implemented_capabilities() == ["coverage", "snapshots", "properties"]


def test_go_mutation_is_reported_as_not_implemented(tmp_path: Path) -> None:
    """The runner surfaces the absent mutation capability as an explicit error."""
    # @spec AC-006, Story 4
    with pytest.raises(CapabilityNotImplementedError, match="mutation: not implemented for go"):
        run_capability(load_builtin_manifest("go"), "mutation", project_root=tmp_path)


def test_go_manifest_scripts_are_shipped_and_executable() -> None:
    """The coverage gate script referenced by the manifest is shipped and executable."""
    # @spec AC-007
    scripts = referenced_scripts(load_builtin_manifest("go"))

    assert [script.name for script in scripts] == ["go-coverage-gate.sh"]
    for script in scripts:
        assert script.is_file(), f"missing: {script}"
        assert os.access(script, os.X_OK), f"not executable: {script}"
