# LiveSpec traceability anchors
# @spec(FR-005)

"""Integration checks for the built-in JVM driver manifest."""

# @spec FR-005: Integration tests for the JVM driver
# — .specs/features/022-driver-jvm/spec.md#fr-005

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from validator.drivers.jvm_detector import (
    detect_build_tool,
    has_jvm_dependency,
    parse_jvm_dependencies,
)
from validator.drivers.loader import load_manifest
from validator.drivers.registry import DriverRegistry
from validator.drivers.schemas import DriverManifest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_JVM_DRIVER_PATH = _REPO_ROOT / "livespec" / "drivers" / "jvm.yaml"
_SCRIPTS_DIR = _REPO_ROOT / "livespec" / "drivers" / "scripts"
_COVERAGE_GATE = _SCRIPTS_DIR / "jvm-coverage-gate.sh"
_SNAPSHOTS_SCRIPT = _SCRIPTS_DIR / "jvm-snapshots.sh"
_PROPERTIES_SCRIPT = _SCRIPTS_DIR / "jvm-properties.sh"
_MUTATION_SCRIPT = _SCRIPTS_DIR / "jvm-mutation.sh"


def _load_jvm_manifest() -> DriverManifest:
    """Load the checked-in JVM driver manifest for assertions."""
    manifest = load_manifest(_JVM_DRIVER_PATH)
    assert manifest is not None
    return manifest


# ---------------------------------------------------------------------------
# Registry detection (3 build files)
# ---------------------------------------------------------------------------


def test_registry_loads_jvm_driver_on_gradle() -> None:
    """Driver discovery matches projects that ship a ``build.gradle``."""
    # @spec AC-001 — .specs/features/022-driver-jvm/spec.md#ac-001
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "build.gradle").write_text("plugins { id 'java' }\n", encoding="utf-8")

        registry = DriverRegistry(project_root)
        drivers = registry.discover()

    assert any(driver.name == "jvm" for driver in drivers)


def test_registry_loads_jvm_driver_on_gradle_kts() -> None:
    """Driver discovery matches Kotlin DSL Gradle projects."""
    # @spec AC-001, AC-011
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "build.gradle.kts").write_text('plugins { id("java") }\n', encoding="utf-8")

        registry = DriverRegistry(project_root)
        drivers = registry.discover()

    assert any(driver.name == "jvm" for driver in drivers)


def test_registry_loads_jvm_driver_on_maven() -> None:
    """Driver discovery matches Maven projects."""
    # @spec AC-001
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "pom.xml").write_text('<?xml version="1.0"?><project/>', encoding="utf-8")

        registry = DriverRegistry(project_root)
        drivers = registry.discover()

    assert any(driver.name == "jvm" for driver in drivers)


# ---------------------------------------------------------------------------
# Schema + capability metadata
# ---------------------------------------------------------------------------


def test_jvm_driver_schema_validation() -> None:
    """The committed JVM driver YAML validates against the schema."""
    # @spec AC-009
    manifest = _load_jvm_manifest()

    assert manifest.name == "jvm"
    assert manifest.coverage is not None
    assert manifest.snapshots is not None
    assert manifest.properties is not None
    assert manifest.mutation is not None


def test_jvm_driver_capabilities_exist() -> None:
    """The manifest advertises all 4 standard capabilities."""
    # @spec SC-002 — single driver covers Java + Kotlin
    manifest = _load_jvm_manifest()

    assert manifest.implemented_capabilities() == [
        "coverage",
        "snapshots",
        "properties",
        "mutation",
    ]


def test_jvm_driver_detect_files() -> None:
    """All three JVM build files appear in the detect rule."""
    # @spec AC-001, AC-010
    manifest = _load_jvm_manifest()

    assert "build.gradle" in manifest.detect.files
    assert "build.gradle.kts" in manifest.detect.files
    assert "pom.xml" in manifest.detect.files


def test_coverage_capability_uses_script_escape_hatch() -> None:
    """Coverage capability is wired to the gate script (Gradle/Maven dispatch)."""
    # @spec AC-002, AC-003
    manifest = _load_jvm_manifest()
    coverage_capability = manifest.coverage

    assert coverage_capability is not None
    assert coverage_capability.command is None
    assert coverage_capability.script == "scripts/jvm-coverage-gate.sh"
    assert coverage_capability.report_path == "build/reports/jacoco/test/lcov.info"
    assert coverage_capability.threshold == 80


def test_snapshots_capability_uses_script_escape_hatch() -> None:
    """Snapshots capability dispatches via script (kotest / approvaltests detection)."""
    # @spec AC-005
    manifest = _load_jvm_manifest()
    snapshots_capability = manifest.snapshots

    assert snapshots_capability is not None
    assert snapshots_capability.script == "scripts/jvm-snapshots.sh"


def test_properties_capability_uses_script_escape_hatch() -> None:
    """Properties capability dispatches via script (kotest-property / jqwik detection)."""
    # @spec AC-006
    manifest = _load_jvm_manifest()
    properties_capability = manifest.properties

    assert properties_capability is not None
    assert properties_capability.script == "scripts/jvm-properties.sh"


def test_mutation_capability_uses_script_escape_hatch() -> None:
    """Mutation capability dispatches via script (pitest detection + XML parse)."""
    # @spec AC-007, AC-008
    manifest = _load_jvm_manifest()
    mutation_capability = manifest.mutation

    assert mutation_capability is not None
    assert mutation_capability.script == "scripts/jvm-mutation.sh"


# ---------------------------------------------------------------------------
# Script artifacts shipped + executable
# ---------------------------------------------------------------------------


def test_all_jvm_scripts_are_shipped_and_executable() -> None:
    """Every script referenced by the manifest is on disk and executable."""
    for script in (
        _COVERAGE_GATE,
        _SNAPSHOTS_SCRIPT,
        _PROPERTIES_SCRIPT,
        _MUTATION_SCRIPT,
    ):
        assert script.is_file(), f"missing: {script}"
        assert os.access(script, os.X_OK), f"not executable: {script}"


# ---------------------------------------------------------------------------
# Dependency detection on three build files
# ---------------------------------------------------------------------------


def test_dependency_detection_in_gradle_groovy_fixture() -> None:
    """A Gradle Groovy fixture exposes its plugins/dependencies through the parser."""
    # @spec AC-005, AC-006, AC-010
    contents = """
plugins {
    id 'java'
    id 'jacoco'
    id 'info.solidsoft.pitest' version '1.15.0'
}
dependencies {
    testImplementation 'io.kotest:kotest-snapshot:5.8.0'
    testImplementation 'net.jqwik:jqwik:1.8.4'
}
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "build.gradle").write_text(contents, encoding="utf-8")

        deps = parse_jvm_dependencies(str(project_root))

        joined = " ".join(deps)
        assert "jacoco" in joined
        assert "pitest" in joined
        assert "kotest-snapshot" in joined
        assert "jqwik" in joined
        assert has_jvm_dependency(str(project_root), "JACOCO") is True
        assert has_jvm_dependency(str(project_root), "Kotest-Snapshot") is True


def test_dependency_detection_in_gradle_kotlin_fixture() -> None:
    """A Gradle Kotlin DSL fixture exposes the same tokens."""
    # @spec AC-011 — Kotlin-first projects work transparently
    contents = """
plugins {
    id("java")
    id("jacoco")
}
dependencies {
    testImplementation("io.kotest:kotest-property:5.8.0")
}
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "build.gradle.kts").write_text(contents, encoding="utf-8")

        deps = parse_jvm_dependencies(str(project_root))

        joined = " ".join(deps)
        assert "jacoco" in joined
        assert "kotest-property" in joined
        assert has_jvm_dependency(str(project_root), "kotest-property") is True


def test_dependency_detection_in_maven_fixture() -> None:
    """A Maven fixture exposes plugin + dependency artifact ids."""
    # @spec AC-005, AC-006, AC-007
    pom = """<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>x</groupId><artifactId>y</artifactId><version>1</version>
  <build>
    <plugins>
      <plugin><artifactId>jacoco-maven-plugin</artifactId></plugin>
      <plugin><artifactId>pitest-maven</artifactId></plugin>
    </plugins>
  </build>
  <dependencies>
    <dependency><artifactId>jqwik</artifactId></dependency>
    <dependency><artifactId>approvaltests</artifactId></dependency>
  </dependencies>
</project>
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "pom.xml").write_text(pom, encoding="utf-8")

        deps = parse_jvm_dependencies(str(project_root))

        assert "jacoco-maven-plugin" in deps
        assert "pitest-maven" in deps
        assert "jqwik" in deps
        assert "approvaltests" in deps
        assert has_jvm_dependency(str(project_root), "jacoco") is True
        assert has_jvm_dependency(str(project_root), "pitest") is True


def test_gradle_priority_over_maven_in_detect_build_tool() -> None:
    """``detect_build_tool`` returns ``"gradle"`` when both build files exist."""
    # @spec AC-010
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "build.gradle").write_text("plugins { id 'java' }\n", encoding="utf-8")
        (project_root / "pom.xml").write_text('<?xml version="1.0"?><project/>', encoding="utf-8")

        assert detect_build_tool(str(project_root)) == "gradle"
