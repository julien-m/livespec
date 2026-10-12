# LiveSpec traceability anchors
# @spec(FR-005)

"""Integration checks for the built-in JVM driver manifest."""

# @spec FR-005: Integration tests for the JVM driver
# — .specs/features/022-driver-jvm/spec.md#fr-005

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.integration.helpers.driver_manifests import load_builtin_manifest, referenced_scripts
from validator.drivers.registry import DriverRegistry


@pytest.mark.parametrize(
    ("build_file", "contents"),
    [
        ("build.gradle", "plugins { id 'java' }\n"),
        ("build.gradle.kts", 'plugins { id("java") }\n'),
        ("pom.xml", '<?xml version="1.0"?><project/>'),
    ],
)
def test_registry_discovers_jvm_driver(tmp_path: Path, build_file: str, contents: str) -> None:
    """Driver discovery matches Gradle Groovy, Gradle Kotlin DSL and Maven projects."""
    # @spec AC-001, AC-011 — .specs/features/022-driver-jvm/spec.md#ac-001
    (tmp_path / build_file).write_text(contents, encoding="utf-8")

    drivers = DriverRegistry(tmp_path).discover()

    assert "jvm" in [driver.name for driver in drivers]


def test_jvm_manifest_validates_with_all_four_capabilities() -> None:
    """The committed YAML validates and declares the four standard capabilities."""
    # @spec AC-009
    manifest = load_builtin_manifest("jvm")

    assert manifest.name == "jvm"
    assert manifest.implemented_capabilities() == [
        "coverage",
        "snapshots",
        "properties",
        "mutation",
    ]


def test_jvm_manifest_scripts_are_shipped_and_executable() -> None:
    """Every capability dispatches through a shipped, executable script."""
    # @spec AC-002, AC-005, AC-006, AC-007
    scripts = referenced_scripts(load_builtin_manifest("jvm"))

    assert sorted(script.name for script in scripts) == [
        "jvm-coverage-gate.sh",
        "jvm-mutation.sh",
        "jvm-properties.sh",
        "jvm-snapshots.sh",
    ]
    for script in scripts:
        assert script.is_file(), f"missing: {script}"
        assert os.access(script, os.X_OK), f"not executable: {script}"
