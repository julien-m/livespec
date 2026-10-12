# LiveSpec traceability anchors
# @spec(FR-007)

"""Integration tests for Android/Maestro surface detection in generate-surfaces.js.

Each test builds a synthetic project, runs the real generator in ``--dry-run``
mode and parses the ``surfaces.yaml`` content it would write. Apple detection
lives in ``test_surfaces_xcuitest.py``.
"""

# @spec FR-001: Android/Maestro surface detection
#   .specs/features/031-ui-runner-android/spec.md#fr-001
# @spec FR-003: Maestro flows detection — .specs/features/031-ui-runner-android/spec.md#fr-003

from __future__ import annotations

from pathlib import Path

import pytest

from tests.integration.helpers.surfaces_script import dry_run_surfaces, run_surfaces_script

_FLOW = "appId: com.example\n---\n- launchApp\n"
_WEB_MANIFEST = (
    "surfaces:\n"
    "  - id: web\n"
    "    name: Web\n"
    "    path: .\n"
    "    testDir: tests/e2e\n"
    "    runner: playwright\n"
)


@pytest.mark.level_3a
@pytest.mark.parametrize(
    ("build_file", "flows_dir"),
    [("build.gradle", "maestro"), ("build.gradle.kts", ".specs/maestro")],
)
def test_root_android_project_with_flows_emits_maestro_surface(
    tmp_path: Path, build_file: str, flows_dir: str
) -> None:
    """A Gradle root plus a flows directory yields one Android Maestro surface."""
    (tmp_path / build_file).write_text("// Gradle build file\n")
    (tmp_path / flows_dir).mkdir(parents=True)
    (tmp_path / flows_dir / "home.yaml").write_text(_FLOW)

    surfaces = dry_run_surfaces(run_surfaces_script(tmp_path))

    assert len(surfaces) == 1
    surface = surfaces[0]
    assert (surface["runner"], surface["platform"], surface["path"]) == ("maestro", "android", ".")
    assert surface["testDir"] == flows_dir


@pytest.mark.level_3a
def test_android_project_without_flows_emits_no_surface(tmp_path: Path) -> None:
    """Without a maestro/ or .specs/maestro/ directory no surface is generated."""
    (tmp_path / "build.gradle.kts").write_text("// build file\n")
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "build.gradle.kts").write_text("// app module\n")

    result = run_surfaces_script(tmp_path)

    assert dry_run_surfaces(result) == []
    assert "No UI surfaces detected" in result.stdout


@pytest.mark.level_3a
def test_android_app_in_monorepo_apps_dir_is_detected(tmp_path: Path) -> None:
    """apps/<app>/build.gradle.kts + maestro/ yields a surface scoped to that app."""
    app_dir = tmp_path / "apps" / "android-app"
    (app_dir / "maestro").mkdir(parents=True)
    (app_dir / "build.gradle.kts").write_text('plugins { id("com.android.application") }\n')
    (app_dir / "maestro" / "home.yaml").write_text(_FLOW)

    surfaces = dry_run_surfaces(run_surfaces_script(tmp_path))

    assert [(s["runner"], s["path"]) for s in surfaces] == [("maestro", "apps/android-app")]
    assert surfaces[0]["testDir"].endswith("maestro")


@pytest.mark.level_3a
def test_migrate_native_appends_android_surface(tmp_path: Path) -> None:
    """--migrate-native appends only the new Maestro surface to an existing manifest."""
    (tmp_path / ".specs").mkdir()
    (tmp_path / ".specs" / "surfaces.yaml").write_text(_WEB_MANIFEST)
    (tmp_path / "build.gradle.kts").write_text("// build file\n")
    (tmp_path / "maestro").mkdir()
    (tmp_path / "maestro" / "home.yaml").write_text(_FLOW)

    result = run_surfaces_script(tmp_path, "--migrate-native")

    assert "Would append to .specs/surfaces.yaml" in result.stdout
    assert [(s["runner"], s["platform"]) for s in dry_run_surfaces(result)] == [
        ("maestro", "android")
    ]


@pytest.mark.level_3a
def test_migrate_native_is_noop_when_maestro_already_declared(tmp_path: Path) -> None:
    """--migrate-native writes nothing when a Maestro surface already exists."""
    (tmp_path / ".specs").mkdir()
    (tmp_path / ".specs" / "surfaces.yaml").write_text(
        "surfaces:\n"
        "  - id: default\n"
        "    name: Default\n"
        "    path: .\n"
        "    testDir: maestro\n"
        "    runner: maestro\n"
        "    platform: android\n"
    )
    (tmp_path / "build.gradle.kts").write_text("// build file\n")
    (tmp_path / "maestro").mkdir()
    (tmp_path / "maestro" / "home.yaml").write_text(_FLOW)

    result = run_surfaces_script(tmp_path, "--migrate-native")

    assert dry_run_surfaces(result) == []
    assert "surfaces.yaml is up to date" in result.stdout
