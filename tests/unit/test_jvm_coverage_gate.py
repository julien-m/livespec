# LiveSpec traceability anchors
# @spec(AC-003)
# @spec(FR-006)

"""Unit tests for the jvm-coverage-gate.sh escape-hatch script."""

# @spec FR-006: Unit tests for the gate script
# — .specs/features/022-driver-jvm/spec.md#fr-006

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "livespec"
    / "drivers"
    / "scripts"
    / "jvm-coverage-gate.sh"
)


def _run_gate(
    cwd: Path,
    *args: str,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Invoke the gate script with ``args`` from ``cwd``."""
    env = dict(os.environ)
    # Default to probe-only so unit tests never invoke a real build tool.
    env.setdefault("LIVESPEC_JVM_SKIP_RUN", "1")
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(_SCRIPT_PATH), *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_script_exists_and_executable() -> None:
    """The shipped gate script is on disk and executable."""
    assert _SCRIPT_PATH.is_file()
    assert os.access(_SCRIPT_PATH, os.X_OK)


def test_gate_no_build_file_fails() -> None:
    """No build file -> exit 1 with a clear hint."""
    # @spec AC-001
    with tempfile.TemporaryDirectory() as tmpdir:
        result = _run_gate(Path(tmpdir))

    assert result.returncode == 1
    assert "no JVM build file" in result.stdout


def test_gate_jacoco_absent_on_gradle_skips_with_setup_guide() -> None:
    """Gradle build file without JaCoCo -> setup-guide message + exit 0."""
    # @spec AC-004
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "build.gradle").write_text("plugins { id 'java' }\n", encoding="utf-8")

        result = _run_gate(project_root)

    assert result.returncode == 0
    assert "JaCoCo not configured" in result.stdout


def test_gate_jacoco_absent_on_maven_skips_with_setup_guide() -> None:
    """Maven build file without JaCoCo -> setup-guide message + exit 0."""
    # @spec AC-004
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "pom.xml").write_text("<project><build/></project>", encoding="utf-8")

        result = _run_gate(project_root)

    assert result.returncode == 0
    assert "JaCoCo not configured" in result.stdout


def test_gate_jacoco_present_on_gradle_kts_lcov_missing_warns() -> None:
    """JaCoCo configured (Kotlin DSL) but lcov absent -> warning + exit 0."""
    # @spec AC-003 — lcov.info path is configurable; warning, not failure.
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "build.gradle.kts").write_text(
            'plugins { id("jacoco") }\n', encoding="utf-8"
        )

        result = _run_gate(project_root)

    assert result.returncode == 0
    # JaCoCo configured but lcov.info wasn't produced because we skipped the run.
    assert "lcov.info not found" in result.stdout or "PASS" in result.stdout


def test_gate_jacoco_present_with_lcov_passes() -> None:
    """JaCoCo configured AND lcov produced -> PASS message + exit 0."""
    # @spec AC-003
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        (project_root / "build.gradle").write_text("plugins { id 'jacoco' }\n", encoding="utf-8")
        lcov_path = project_root / "build" / "reports" / "jacoco" / "test"
        lcov_path.mkdir(parents=True)
        (lcov_path / "lcov.info").write_text("TN:\nSF:foo\nDA:1,1\n", encoding="utf-8")

        result = _run_gate(project_root)

    assert result.returncode == 0
    assert "PASS" in result.stdout


def test_gate_gradle_priority_over_maven() -> None:
    """When both Gradle and Maven build files are present, Gradle is used."""
    # @spec AC-010
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        # Gradle file with no JaCoCo, Maven file WITH JaCoCo.
        # If Gradle priority works, we should see the no-JaCoCo skip-message
        # (because the Gradle file is consulted, not pom.xml).
        (project_root / "build.gradle").write_text("plugins { id 'java' }\n", encoding="utf-8")
        (project_root / "pom.xml").write_text(
            "<project><build><plugins><plugin>"
            "<artifactId>jacoco-maven-plugin</artifactId>"
            "</plugin></plugins></build></project>",
            encoding="utf-8",
        )

        result = _run_gate(project_root)

    assert result.returncode == 0
    assert "JaCoCo not configured" in result.stdout


def test_bash_available_for_test_environment() -> None:
    """Sanity check that the test environment has bash on PATH."""
    assert shutil.which("bash") is not None
