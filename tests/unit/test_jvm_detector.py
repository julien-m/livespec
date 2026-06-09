# LiveSpec traceability anchors
# @spec(FR-006)

"""Unit tests for JVM build file parsing and pitest XML parsing."""

# @spec FR-006: Unit tests for build file parser and pitest XML parser
# — .specs/features/022-driver-jvm/spec.md#fr-006

from __future__ import annotations

import tempfile
from pathlib import Path

from validator.drivers.jvm_detector import (
    detect_build_tool,
    has_jvm_dependency,
    parse_gradle_build,
    parse_jvm_dependencies,
    parse_maven_pom,
    parse_pitest_xml,
)

_GRADLE_GROOVY = """
plugins {
    id 'java'
    id 'jacoco'
    id 'info.solidsoft.pitest' version '1.15.0'
}

dependencies {
    testImplementation 'io.kotest:kotest-runner-junit5:5.8.0'
    testImplementation 'io.kotest:kotest-property:5.8.0'
    testImplementation 'io.kotest:kotest-snapshot:5.8.0'
    testImplementation 'net.jqwik:jqwik:1.8.4'
    testImplementation 'com.approvaltests:approvaltests:22.3.2'
}

jacoco {
    toolVersion = '0.8.11'
}
"""

_GRADLE_KOTLIN = """
plugins {
    id("java")
    id("jacoco")
    id("info.solidsoft.pitest") version "1.15.0"
}

dependencies {
    testImplementation("io.kotest:kotest-runner-junit5:5.8.0")
    testImplementation("io.kotest:kotest-property:5.8.0")
}
"""

_MAVEN_POM = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>myapp</artifactId>
  <version>1.0.0</version>

  <build>
    <plugins>
      <plugin>
        <groupId>org.jacoco</groupId>
        <artifactId>jacoco-maven-plugin</artifactId>
        <version>0.8.11</version>
      </plugin>
      <plugin>
        <groupId>org.pitest</groupId>
        <artifactId>pitest-maven</artifactId>
        <version>1.15.0</version>
      </plugin>
    </plugins>
  </build>

  <dependencies>
    <dependency>
      <groupId>net.jqwik</groupId>
      <artifactId>jqwik</artifactId>
      <version>1.8.4</version>
      <scope>test</scope>
    </dependency>
    <dependency>
      <groupId>com.approvaltests</groupId>
      <artifactId>approvaltests</artifactId>
      <version>22.3.2</version>
      <scope>test</scope>
    </dependency>
  </dependencies>
</project>
"""

_PITEST_XML = """<?xml version="1.0" encoding="UTF-8"?>
<mutations>
    <mutation detected="true" status="KILLED" numberOfTestsRun="3">
        <sourceFile>Foo.java</sourceFile>
    </mutation>
    <mutation detected="false" status="SURVIVED" numberOfTestsRun="2">
        <sourceFile>Foo.java</sourceFile>
    </mutation>
    <mutation detected="false" status="SURVIVED" numberOfTestsRun="2">
        <sourceFile>Bar.java</sourceFile>
    </mutation>
    <mutation detected="false" status="TIMED_OUT" numberOfTestsRun="1">
        <sourceFile>Bar.java</sourceFile>
    </mutation>
    <mutation detected="false" status="NO_COVERAGE" numberOfTestsRun="0">
        <sourceFile>Bar.java</sourceFile>
    </mutation>
</mutations>
"""


# ---------------------------------------------------------------------------
# detect_build_tool
# ---------------------------------------------------------------------------


def test_detect_build_tool_gradle_groovy() -> None:
    """``build.gradle`` -> ``"gradle"``."""
    # @spec AC-010
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "build.gradle").write_text("// gradle", encoding="utf-8")

        assert detect_build_tool(tmpdir) == "gradle"


def test_detect_build_tool_gradle_kotlin() -> None:
    """``build.gradle.kts`` -> ``"gradle"``."""
    # @spec AC-010, AC-011
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "build.gradle.kts").write_text("// gradle kts", encoding="utf-8")

        assert detect_build_tool(tmpdir) == "gradle"


def test_detect_build_tool_maven_only() -> None:
    """Only ``pom.xml`` -> ``"maven"``."""
    # @spec AC-010
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "pom.xml").write_text('<?xml version="1.0"?><project/>', encoding="utf-8")

        assert detect_build_tool(tmpdir) == "maven"


def test_detect_build_tool_gradle_priority_over_maven() -> None:
    """Both Gradle + Maven present -> Gradle takes priority."""
    # @spec AC-010
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "build.gradle").write_text("// gradle", encoding="utf-8")
        (Path(tmpdir) / "pom.xml").write_text('<?xml version="1.0"?><project/>', encoding="utf-8")

        assert detect_build_tool(tmpdir) == "gradle"


def test_detect_build_tool_none_when_empty() -> None:
    """Empty directory -> ``None``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assert detect_build_tool(tmpdir) is None


# ---------------------------------------------------------------------------
# parse_gradle_build
# ---------------------------------------------------------------------------


def test_parse_gradle_build_groovy_extracts_plugin_and_dependency_tokens() -> None:
    """Groovy DSL plugin/dependency tokens are recognised."""
    # @spec FR-003, AC-010
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "build.gradle").write_text(_GRADLE_GROOVY, encoding="utf-8")

        tokens = parse_gradle_build(tmpdir)

    # The regex captures dotted coordinates as a single token, so we assert
    # by substring (matching the contract of `has_jvm_dependency`).
    joined = " ".join(tokens)
    assert "jacoco" in joined
    assert "pitest" in joined
    assert "kotest-property" in joined
    assert "kotest-snapshot" in joined
    assert "jqwik" in joined
    assert "approvaltests" in joined


def test_parse_gradle_build_kotlin_dsl() -> None:
    """Kotlin DSL build files are walked the same way as Groovy."""
    # @spec AC-011
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "build.gradle.kts").write_text(_GRADLE_KOTLIN, encoding="utf-8")

        tokens = parse_gradle_build(tmpdir)

    joined = " ".join(tokens)
    assert "jacoco" in joined
    assert "pitest" in joined
    assert "kotest-property" in joined


def test_parse_gradle_build_strips_comments() -> None:
    """Tokens inside line / block comments are not returned."""
    contents = """
plugins {
    // id 'jacoco'  -- this comment must NOT yield jacoco
    /* id 'pitest' -- block-commented out */
    id 'java'
}
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "build.gradle").write_text(contents, encoding="utf-8")

        tokens = parse_gradle_build(tmpdir)

    assert "java" in tokens
    assert "jacoco" not in tokens
    assert "pitest" not in tokens


def test_parse_gradle_build_missing_returns_empty() -> None:
    """No Gradle build file -> empty list, no raise."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assert parse_gradle_build(tmpdir) == []


# ---------------------------------------------------------------------------
# parse_maven_pom
# ---------------------------------------------------------------------------


def test_parse_maven_pom_extracts_artifact_ids() -> None:
    """``<artifactId>`` elements (plugins + dependencies) are extracted."""
    # @spec FR-003, AC-010
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "pom.xml").write_text(_MAVEN_POM, encoding="utf-8")

        ids = parse_maven_pom(tmpdir)

    # The project's own artifactId is also returned (it is an <artifactId> node).
    assert "jacoco-maven-plugin" in ids
    assert "pitest-maven" in ids
    assert "jqwik" in ids
    assert "approvaltests" in ids


def test_parse_maven_pom_missing_returns_empty() -> None:
    """No ``pom.xml`` -> empty list, no raise."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assert parse_maven_pom(tmpdir) == []


def test_parse_maven_pom_malformed_returns_empty() -> None:
    """Malformed XML -> empty list (no exception)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "pom.xml").write_text("<project><not-closed", encoding="utf-8")

        assert parse_maven_pom(tmpdir) == []


def test_parse_maven_pom_unreadable_returns_empty() -> None:
    """A binary / unreadable pom.xml degrades to an empty list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "pom.xml").write_bytes(b"\xff\xfe\x00\x00")

        assert parse_maven_pom(tmpdir) == []


# ---------------------------------------------------------------------------
# parse_jvm_dependencies + has_jvm_dependency
# ---------------------------------------------------------------------------


def test_parse_jvm_dependencies_combines_gradle_and_maven() -> None:
    """When both build files exist, both contribute to the dependency list."""
    # @spec AC-010, AC-011
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "build.gradle").write_text(_GRADLE_GROOVY, encoding="utf-8")
        (Path(tmpdir) / "pom.xml").write_text(_MAVEN_POM, encoding="utf-8")

        deps = parse_jvm_dependencies(tmpdir)

    joined = " ".join(deps)
    assert "jacoco" in joined
    assert "pitest-maven" in deps  # exact artifact id from pom.xml


def test_has_jvm_dependency_substring_match() -> None:
    """``has_jvm_dependency`` does case-insensitive substring matching."""
    # @spec FR-003 — Gradle plugin coordinates and Maven artifact ids are dotted.
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "pom.xml").write_text(_MAVEN_POM, encoding="utf-8")

        assert has_jvm_dependency(tmpdir, "jacoco") is True
        assert has_jvm_dependency(tmpdir, "JACOCO") is True
        assert has_jvm_dependency(tmpdir, "PITEST") is True
        assert has_jvm_dependency(tmpdir, "jqwik") is True
        assert has_jvm_dependency(tmpdir, "approvaltests") is True
        assert has_jvm_dependency(tmpdir, "stryker") is False


def test_has_jvm_dependency_empty_returns_false() -> None:
    """Empty / whitespace needle never matches."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "pom.xml").write_text(_MAVEN_POM, encoding="utf-8")

        assert has_jvm_dependency(tmpdir, "") is False
        assert has_jvm_dependency(tmpdir, "   ") is False


def test_has_jvm_dependency_no_build_file_returns_false() -> None:
    """When no build file exists, all lookups return False."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assert has_jvm_dependency(tmpdir, "jacoco") is False


# ---------------------------------------------------------------------------
# parse_pitest_xml
# ---------------------------------------------------------------------------


def test_parse_pitest_xml_extracts_counts() -> None:
    """KILLED / SURVIVED / TIMED_OUT / NO_COVERAGE counts are extracted."""
    # @spec FR-004, AC-008, SC-004
    counts = parse_pitest_xml(_PITEST_XML)

    assert counts["killed"] == 1
    assert counts["survived"] == 2
    assert counts["timed_out"] == 1
    assert counts["no_coverage"] == 1
    # Other statuses are zero-filled.
    assert counts["memory_error"] == 0
    assert counts["run_error"] == 0


def test_parse_pitest_xml_zero_fills_missing_statuses() -> None:
    """Statuses not present in the XML default to zero."""
    # @spec FR-004
    payload = """<?xml version="1.0"?>
<mutations>
    <mutation status="KILLED"/>
</mutations>
"""

    counts = parse_pitest_xml(payload)

    assert counts == {
        "killed": 1,
        "survived": 0,
        "timed_out": 0,
        "no_coverage": 0,
        "memory_error": 0,
        "run_error": 0,
    }


def test_parse_pitest_xml_handles_lowercase_status() -> None:
    """Status strings are normalised case-insensitively."""
    # @spec SC-004 — handle KILLED and SURVIVED in any case
    payload = """<?xml version="1.0"?>
<mutations>
    <mutation status="killed"/>
    <mutation status="Survived"/>
    <mutation status="TIMED_OUT"/>
</mutations>
"""

    counts = parse_pitest_xml(payload)

    assert counts["killed"] == 1
    assert counts["survived"] == 1
    assert counts["timed_out"] == 1


def test_parse_pitest_xml_malformed_returns_zeros() -> None:
    """Garbage input that doesn't look like XML yields all-zero counts."""
    counts = parse_pitest_xml("not xml at all { just text }")

    assert counts == {
        "killed": 0,
        "survived": 0,
        "timed_out": 0,
        "no_coverage": 0,
        "memory_error": 0,
        "run_error": 0,
    }


def test_parse_pitest_xml_empty_returns_zeros() -> None:
    """Empty input yields all-zero counts."""
    counts = parse_pitest_xml("")

    assert all(v == 0 for v in counts.values())


def test_parse_pitest_xml_ignores_unknown_statuses() -> None:
    """Unknown status strings are silently ignored."""
    payload = """<?xml version="1.0"?>
<mutations>
    <mutation status="KILLED"/>
    <mutation status="TOTALLY_UNKNOWN"/>
    <mutation status="SURVIVED"/>
</mutations>
"""

    counts = parse_pitest_xml(payload)

    assert counts["killed"] == 1
    assert counts["survived"] == 1


def test_parse_pitest_xml_ignores_mutation_without_status_attribute() -> None:
    """Mutation elements lacking a ``status`` attribute are skipped."""
    payload = """<?xml version="1.0"?>
<mutations>
    <mutation status="KILLED"/>
    <mutation/>
</mutations>
"""

    counts = parse_pitest_xml(payload)

    assert counts["killed"] == 1
