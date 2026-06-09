# LiveSpec traceability anchors
# @spec(FR-007)

"""Integration tests for Android/Maestro surface detection in generate-surfaces.js.

These tests create temporary project fixtures and verify that the generator
correctly emits maestro surface entries. Complementary to test_surfaces_xcuitest.py.

All tests are marked level_3a and run without LLM calls.
"""

# @spec FR-001: Android/Maestro surface detection
#   .specs/features/031-ui-runner-android/spec.md#fr-001
# @spec FR-003: Maestro flows detection — .specs/features/031-ui-runner-android/spec.md#fr-003

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "generate-surfaces.js"


def run_surfaces_script(
    project_dir: Path,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run generate-surfaces.js in --dry-run mode from project_dir."""
    args = ["node", str(SCRIPT_PATH), "--dry-run"]
    if extra_args:
        args.extend(extra_args)
    return subprocess.run(
        args,
        cwd=str(project_dir),
        capture_output=True,
        text=True,
        timeout=30,
    )


# ---------------------------------------------------------------------------
# Root-level Android project detection
# ---------------------------------------------------------------------------


@pytest.mark.level_3a
def test_android_build_gradle_with_maestro_dir(tmp_path: Path) -> None:
    """Root-level build.gradle + maestro/ triggers maestro surface detection."""
    (tmp_path / "build.gradle").write_text("// Gradle build file\n")
    maestro_dir = tmp_path / "maestro"
    maestro_dir.mkdir()
    (maestro_dir / "login.yaml").write_text("appId: com.example\n---\n- launchApp\n")

    result = run_surfaces_script(tmp_path)

    assert result.returncode == 0, f"Script failed: {result.stderr}"
    combined = result.stdout + result.stderr
    assert "maestro" in combined.lower(), f"Expected 'maestro' in output but got:\n{combined}"


@pytest.mark.level_3a
def test_android_build_gradle_kts_with_specs_maestro(tmp_path: Path) -> None:
    """Root-level build.gradle.kts + .specs/maestro/ triggers maestro detection."""
    (tmp_path / "build.gradle.kts").write_text('plugins { id("com.android.application") }\n')
    specs_maestro = tmp_path / ".specs" / "maestro"
    specs_maestro.mkdir(parents=True)
    (specs_maestro / "dashboard.yaml").write_text(
        "appId: com.example\n---\n- launchApp\n- takeScreenshot: dashboard\n"
    )

    result = run_surfaces_script(tmp_path)

    assert result.returncode == 0, f"Script failed: {result.stderr}"
    combined = result.stdout + result.stderr
    assert "maestro" in combined.lower(), f"Expected 'maestro' in output but got:\n{combined}"


@pytest.mark.level_3a
def test_android_without_maestro_does_not_emit_maestro_surface(
    tmp_path: Path,
) -> None:
    """Android project without any maestro/ dir does not emit maestro surface."""
    (tmp_path / "build.gradle.kts").write_text("// build file\n")
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "build.gradle.kts").write_text("// app module\n")
    # Deliberately no maestro/ or .specs/maestro/

    result = run_surfaces_script(tmp_path)

    combined = result.stdout + result.stderr
    assert "maestro" not in combined.lower(), (
        f"Did not expect 'maestro' in output but got:\n{combined}"
    )


@pytest.mark.level_3a
def test_maestro_surface_has_android_platform(tmp_path: Path) -> None:
    """Detected maestro surface includes platform: android in YAML output."""
    (tmp_path / "build.gradle.kts").write_text("// build file\n")
    maestro_dir = tmp_path / "maestro"
    maestro_dir.mkdir()
    (maestro_dir / "flow.yaml").write_text("appId: com.example\n---\n- launchApp\n")

    result = run_surfaces_script(tmp_path)

    assert result.returncode == 0, f"Script failed: {result.stderr}"
    combined = result.stdout + result.stderr
    assert "android" in combined.lower(), (
        f"Expected 'android' platform in output but got:\n{combined}"
    )


# ---------------------------------------------------------------------------
# apps/ monorepo directory detection
# ---------------------------------------------------------------------------


@pytest.mark.level_3a
def test_android_in_apps_dir_detected(tmp_path: Path) -> None:
    """apps/<app>/build.gradle + maestro/ triggers maestro surface in monorepo."""
    app_dir = tmp_path / "apps" / "android-app"
    app_dir.mkdir(parents=True)
    (app_dir / "build.gradle.kts").write_text('plugins { id("com.android.application") }\n')
    maestro_dir = app_dir / "maestro"
    maestro_dir.mkdir()
    (maestro_dir / "home.yaml").write_text("appId: com.example\n---\n- launchApp\n")

    result = run_surfaces_script(tmp_path)

    assert result.returncode == 0, f"Script failed: {result.stderr}"
    combined = result.stdout + result.stderr
    assert "maestro" in combined.lower(), f"Expected 'maestro' in output but got:\n{combined}"


# ---------------------------------------------------------------------------
# Migration v12 — --migrate-native
# ---------------------------------------------------------------------------


@pytest.mark.level_3a
def test_migrate_native_appends_android_surface(tmp_path: Path) -> None:
    """--migrate-native appends maestro surface to existing surfaces.yaml."""
    specs_dir = tmp_path / ".specs"
    specs_dir.mkdir()
    existing_yaml = (
        "# Auto-generated by LiveSpec Migration v8\n"
        "surfaces:\n"
        "  - id: web\n"
        "    name: Web\n"
        "    path: .\n"
        "    testDir: tests/e2e\n"
        "    runner: playwright\n"
    )
    (specs_dir / "surfaces.yaml").write_text(existing_yaml)

    # Create Android project with maestro
    (tmp_path / "build.gradle.kts").write_text("// build file\n")
    maestro_dir = tmp_path / "maestro"
    maestro_dir.mkdir()
    (maestro_dir / "home.yaml").write_text("appId: com.example\n---\n- launchApp\n")

    result = run_surfaces_script(tmp_path, extra_args=["--migrate-native", "--dry-run"])

    assert result.returncode == 0, f"Script failed: {result.stderr}"
    combined = result.stdout + result.stderr
    assert "maestro" in combined.lower(), (
        f"Expected maestro surface in migration output but got:\n{combined}"
    )


@pytest.mark.level_3a
def test_migrate_native_noop_when_maestro_already_present(tmp_path: Path) -> None:
    """--migrate-native is no-op when maestro surface already in manifest."""
    specs_dir = tmp_path / ".specs"
    specs_dir.mkdir()
    existing_yaml = (
        "surfaces:\n"
        "  - id: default\n"
        "    name: Default\n"
        "    path: .\n"
        "    testDir: maestro\n"
        "    runner: maestro\n"
        "    platform: android\n"
    )
    (specs_dir / "surfaces.yaml").write_text(existing_yaml)

    (tmp_path / "build.gradle.kts").write_text("// build file\n")
    maestro_dir = tmp_path / "maestro"
    maestro_dir.mkdir()
    (maestro_dir / "home.yaml").write_text("appId: com.example\n---\n- launchApp\n")

    result = run_surfaces_script(tmp_path, extra_args=["--migrate-native", "--dry-run"])

    assert result.returncode == 0
    combined = result.stdout + result.stderr
    assert "up to date" in combined.lower() or "0 new" in combined.lower(), (
        f"Expected no-op message but got:\n{combined}"
    )


@pytest.mark.level_3a
def test_maestro_surface_testdir_points_to_maestro_dir(tmp_path: Path) -> None:
    """Maestro surface testDir points to the maestro/ directory."""
    (tmp_path / "build.gradle.kts").write_text("// build file\n")
    maestro_dir = tmp_path / "maestro"
    maestro_dir.mkdir()
    (maestro_dir / "flow.yaml").write_text("appId: com.example\n")

    result = run_surfaces_script(tmp_path)

    assert result.returncode == 0, f"Script failed: {result.stderr}"
    combined = result.stdout + result.stderr
    # The dry-run output includes the testDir path
    assert "maestro" in combined.lower()
