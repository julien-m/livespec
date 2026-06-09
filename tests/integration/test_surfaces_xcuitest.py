"""Integration tests for iOS/watchOS + Android surface detection in generate-surfaces.js.

These tests create temporary project fixtures and verify that the generator
correctly emits xcuitest and maestro surface entries.

All tests are marked level_3a and run without LLM calls.
"""

# @spec FR-001: iOS/watchOS surface detection
# .specs/features/030-ui-runner-ios-watchos/spec.md#fr-001
# @spec FR-001: Android/Maestro surface detection
# .specs/features/031-ui-runner-android/spec.md#fr-001

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
# iOS/watchOS (xcuitest) detection
# ---------------------------------------------------------------------------


@pytest.mark.level_3a
def test_xcodeproj_at_root_detected_as_xcuitest(tmp_path: Path) -> None:
    """A root-level .xcodeproj directory triggers xcuitest surface detection."""
    # Create minimal Xcode project fixture
    xcodeproj = tmp_path / "MyApp.xcodeproj"
    xcodeproj.mkdir()
    (xcodeproj / "project.pbxproj").write_text("// Xcode project file\n")

    result = run_surfaces_script(tmp_path)

    assert result.returncode == 0, f"Script failed: {result.stderr}"
    combined = result.stdout + result.stderr
    assert "xcuitest" in combined.lower(), f"Expected 'xcuitest' in output but got:\n{combined}"


@pytest.mark.level_3a
def test_package_swift_at_root_detected_as_xcuitest(tmp_path: Path) -> None:
    """A root-level Package.swift triggers xcuitest surface detection."""
    (tmp_path / "Package.swift").write_text(
        "// swift-tools-version: 5.9\n"
        "import PackageDescription\n"
        'let package = Package(name: "MyLib")\n'
    )

    result = run_surfaces_script(tmp_path)

    assert result.returncode == 0, f"Script failed: {result.stderr}"
    combined = result.stdout + result.stderr
    assert "xcuitest" in combined.lower(), f"Expected 'xcuitest' in output but got:\n{combined}"


@pytest.mark.level_3a
def test_xcodeproj_in_apps_dir_detected(tmp_path: Path) -> None:
    """An apps/<app>/<app>.xcodeproj layout triggers xcuitest surface detection."""
    app_dir = tmp_path / "apps" / "iOS"
    app_dir.mkdir(parents=True)
    xcodeproj = app_dir / "iOS.xcodeproj"
    xcodeproj.mkdir()
    (xcodeproj / "project.pbxproj").write_text("")

    result = run_surfaces_script(tmp_path)

    assert result.returncode == 0, f"Script failed: {result.stderr}"
    combined = result.stdout + result.stderr
    assert "xcuitest" in combined.lower(), f"Expected 'xcuitest' in output but got:\n{combined}"


# ---------------------------------------------------------------------------
# Android (maestro) detection
# ---------------------------------------------------------------------------


@pytest.mark.level_3a
def test_android_with_maestro_dir_detected(tmp_path: Path) -> None:
    """An Android project with maestro/ dir triggers maestro surface detection."""
    # Create minimal Android project structure
    (tmp_path / "build.gradle.kts").write_text(
        'plugins { id("com.android.application") version "8.0" }\n'
    )
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "build.gradle.kts").write_text('android { namespace = "com.example" }\n')
    maestro_dir = tmp_path / "maestro"
    maestro_dir.mkdir()
    (maestro_dir / "login.yaml").write_text("appId: com.example\n---\n- launchApp\n")

    result = run_surfaces_script(tmp_path)

    assert result.returncode == 0, f"Script failed: {result.stderr}"
    combined = result.stdout + result.stderr
    assert "maestro" in combined.lower(), f"Expected 'maestro' in output but got:\n{combined}"


@pytest.mark.level_3a
def test_android_without_maestro_not_detected_as_maestro(tmp_path: Path) -> None:
    """An Android project WITHOUT maestro/ dir does not trigger maestro detection."""
    (tmp_path / "build.gradle").write_text("// Gradle build file\n")
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "build.gradle").write_text("// app build file\n")
    # No maestro/ directory

    result = run_surfaces_script(tmp_path)

    # The script may detect no surfaces or a manual surface — but not maestro
    combined = result.stdout + result.stderr
    assert "maestro" not in combined.lower(), (
        f"Did not expect 'maestro' in output (no maestro/ dir) but got:\n{combined}"
    )


@pytest.mark.level_3a
def test_android_with_specs_maestro_dir_detected(tmp_path: Path) -> None:
    """An Android project with .specs/maestro/ dir triggers maestro detection."""
    (tmp_path / "build.gradle.kts").write_text("// build file\n")
    specs_maestro = tmp_path / ".specs" / "maestro"
    specs_maestro.mkdir(parents=True)
    (specs_maestro / "dashboard.yaml").write_text("appId: com.example\n---\n- launchApp\n")

    result = run_surfaces_script(tmp_path)

    assert result.returncode == 0, f"Script failed: {result.stderr}"
    combined = result.stdout + result.stderr
    assert "maestro" in combined.lower(), f"Expected 'maestro' in output but got:\n{combined}"


# ---------------------------------------------------------------------------
# Migration v12 (--migrate-native)
# ---------------------------------------------------------------------------


@pytest.mark.level_3a
def test_migrate_native_appends_ios_surface_to_existing_manifest(tmp_path: Path) -> None:
    """--migrate-native appends xcuitest surface to existing surfaces.yaml."""
    # Create existing surfaces.yaml with a web surface
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

    # Create iOS project
    (tmp_path / "Package.swift").write_text("// swift-tools-version: 5.9\n")

    result = run_surfaces_script(tmp_path, extra_args=["--migrate-native", "--dry-run"])

    assert result.returncode == 0, f"Script failed: {result.stderr}"
    combined = result.stdout + result.stderr
    assert "xcuitest" in combined.lower(), (
        f"Expected xcuitest surface in migration output but got:\n{combined}"
    )


@pytest.mark.level_3a
def test_migrate_native_no_op_when_already_present(tmp_path: Path) -> None:
    """--migrate-native is no-op when xcuitest surface already in manifest."""
    specs_dir = tmp_path / ".specs"
    specs_dir.mkdir()
    existing_yaml = (
        "surfaces:\n"
        "  - id: default\n"
        "    name: Default\n"
        "    path: .\n"
        "    testDir: UITests\n"
        "    runner: xcuitest\n"
        "    platform: ios\n"
    )
    (specs_dir / "surfaces.yaml").write_text(existing_yaml)
    (tmp_path / "Package.swift").write_text("// swift-tools-version: 5.9\n")

    result = run_surfaces_script(tmp_path, extra_args=["--migrate-native", "--dry-run"])

    assert result.returncode == 0
    combined = result.stdout + result.stderr
    assert "up to date" in combined.lower() or "0 new" in combined.lower(), (
        f"Expected no-op message but got:\n{combined}"
    )
