# LiveSpec traceability anchors
# @spec(FR-006)

"""Unit tests for the jvm-mutation.sh + jvm-snapshots.sh + jvm-properties.sh scripts."""

# @spec FR-006: Unit tests for the gate scripts
# — .specs/features/022-driver-jvm/spec.md#fr-006

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "livespec" / "drivers" / "scripts"
_MUTATION_SCRIPT = _SCRIPTS_DIR / "jvm-mutation.sh"
_SNAPSHOTS_SCRIPT = _SCRIPTS_DIR / "jvm-snapshots.sh"
_PROPERTIES_SCRIPT = _SCRIPTS_DIR / "jvm-properties.sh"


def _run(
    script: Path, cwd: Path, env_overrides: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run ``script`` in ``cwd`` with probe-only mode by default."""
    env = dict(os.environ)
    env.setdefault("LIVESPEC_JVM_SKIP_RUN", "1")
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(script)],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


# ---------------------------------------------------------------------------
# scripts shipped + executable
# ---------------------------------------------------------------------------


def test_all_jvm_scripts_are_shipped_and_executable() -> None:
    """The mutation, snapshots, and properties scripts are on disk and executable."""
    for script in (_MUTATION_SCRIPT, _SNAPSHOTS_SCRIPT, _PROPERTIES_SCRIPT):
        assert script.is_file(), f"missing: {script}"
        assert os.access(script, os.X_OK), f"not executable: {script}"


# ---------------------------------------------------------------------------
# jvm-mutation.sh
# ---------------------------------------------------------------------------


def test_mutation_no_build_file_fails() -> None:
    """No build file -> exit 1."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = _run(_MUTATION_SCRIPT, Path(tmpdir))

    assert result.returncode == 1
    assert "no JVM build file" in result.stdout


def test_mutation_pitest_absent_on_gradle_skips_with_setup_hint() -> None:
    """No pitest in Gradle build -> exit 0 with setup hint."""
    # @spec AC-007
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "build.gradle").write_text("plugins { id 'java' }\n", encoding="utf-8")

        result = _run(_MUTATION_SCRIPT, project_root)

    assert result.returncode == 0
    assert "pitest not configured" in result.stdout


def test_mutation_pitest_absent_on_maven_skips_with_setup_hint() -> None:
    """No pitest in Maven build -> exit 0 with setup hint."""
    # @spec AC-007
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "pom.xml").write_text("<project><build/></project>", encoding="utf-8")

        result = _run(_MUTATION_SCRIPT, project_root)

    assert result.returncode == 0
    assert "pitest not configured" in result.stdout


def test_mutation_pitest_present_on_gradle_probe_only() -> None:
    """pitest configured in Gradle -> probe-only success."""
    # @spec AC-007
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "build.gradle").write_text(
            "plugins { id 'info.solidsoft.pitest' version '1.15.0' }\n",
            encoding="utf-8",
        )

        result = _run(_MUTATION_SCRIPT, project_root)

    assert result.returncode == 0
    assert "pitest detected" in result.stdout


def test_mutation_pitest_present_on_maven_probe_only() -> None:
    """pitest configured in Maven -> probe-only success."""
    # @spec AC-007
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "pom.xml").write_text(
            "<project><build><plugins><plugin>"
            "<artifactId>pitest-maven</artifactId>"
            "</plugin></plugins></build></project>",
            encoding="utf-8",
        )

        result = _run(_MUTATION_SCRIPT, project_root)

    assert result.returncode == 0
    assert "pitest detected" in result.stdout


# ---------------------------------------------------------------------------
# jvm-snapshots.sh
# ---------------------------------------------------------------------------


def test_snapshots_no_library_skips() -> None:
    """No snapshot library -> skip with exit 0."""
    # @spec AC-005
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "build.gradle").write_text("plugins { id 'java' }\n", encoding="utf-8")

        result = _run(_SNAPSHOTS_SCRIPT, project_root)

    assert result.returncode == 0
    assert "No snapshot library detected" in result.stdout


def test_snapshots_kotest_detected_on_gradle_kts() -> None:
    """kotest-snapshot in build.gradle.kts -> probe-only success."""
    # @spec AC-005, AC-011
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "build.gradle.kts").write_text(
            'testImplementation("io.kotest:kotest-snapshot:5.8.0")\n',
            encoding="utf-8",
        )

        result = _run(_SNAPSHOTS_SCRIPT, project_root)

    assert result.returncode == 0
    assert "library detected" in result.stdout


def test_snapshots_approvaltests_detected_on_maven() -> None:
    """approvaltests in pom.xml -> probe-only success."""
    # @spec AC-005
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "pom.xml").write_text(
            "<project><dependencies><dependency>"
            "<artifactId>approvaltests</artifactId>"
            "</dependency></dependencies></project>",
            encoding="utf-8",
        )

        result = _run(_SNAPSHOTS_SCRIPT, project_root)

    assert result.returncode == 0
    assert "library detected" in result.stdout


# ---------------------------------------------------------------------------
# jvm-properties.sh
# ---------------------------------------------------------------------------


def test_properties_no_library_skips() -> None:
    """No property library -> skip with exit 0."""
    # @spec AC-006
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "build.gradle").write_text("plugins { id 'java' }\n", encoding="utf-8")

        result = _run(_PROPERTIES_SCRIPT, project_root)

    assert result.returncode == 0
    assert "No property testing library found" in result.stdout


def test_properties_jqwik_detected_on_maven() -> None:
    """jqwik in pom.xml -> probe-only success."""
    # @spec AC-006
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "pom.xml").write_text(
            "<project><dependencies><dependency>"
            "<artifactId>jqwik</artifactId>"
            "</dependency></dependencies></project>",
            encoding="utf-8",
        )

        result = _run(_PROPERTIES_SCRIPT, project_root)

    assert result.returncode == 0
    assert "library detected" in result.stdout


def test_properties_kotest_property_detected_on_gradle_kts() -> None:
    """kotest-property in build.gradle.kts -> probe-only success."""
    # @spec AC-006, AC-011 — Kotlin-first projects use kotest-property
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "build.gradle.kts").write_text(
            'testImplementation("io.kotest:kotest-property:5.8.0")\n',
            encoding="utf-8",
        )

        result = _run(_PROPERTIES_SCRIPT, project_root)

    assert result.returncode == 0
    assert "library detected" in result.stdout
