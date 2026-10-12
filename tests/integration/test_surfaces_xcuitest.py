"""Integration tests for iOS/watchOS surface detection in generate-surfaces.js.

Each test builds a synthetic project, runs the real generator in ``--dry-run``
mode and parses the ``surfaces.yaml`` content it would write. Android/Maestro
detection lives in ``test_surfaces_maestro.py``.
"""

# @spec FR-001: iOS/watchOS surface detection
# .specs/features/030-ui-runner-ios-watchos/spec.md#fr-001

from __future__ import annotations

from pathlib import Path

import pytest

from tests.integration.helpers.surfaces_script import dry_run_surfaces, run_surfaces_script


@pytest.mark.level_3a
def test_root_xcodeproj_emits_xcuitest_surface(tmp_path: Path) -> None:
    """A root .xcodeproj without test targets yields the iOS fallback surface."""
    (tmp_path / "MyApp.xcodeproj").mkdir()
    (tmp_path / "MyApp.xcodeproj" / "project.pbxproj").write_text("// Xcode project file\n")

    result = run_surfaces_script(tmp_path)
    surfaces = dry_run_surfaces(result)

    assert len(surfaces) == 1
    surface = surfaces[0]
    assert (surface["runner"], surface["platform"], surface["path"]) == ("xcuitest", "ios", ".")
    assert surface["runnerConfig"]["project"] == "MyApp.xcodeproj"
    assert "no test targets" in result.stdout + result.stderr


@pytest.mark.level_3a
def test_root_package_swift_emits_xcuitest_surface(tmp_path: Path) -> None:
    """A root Package.swift yields one xcuitest surface at the project root."""
    (tmp_path / "Package.swift").write_text(
        "// swift-tools-version: 5.9\n"
        "import PackageDescription\n"
        'let package = Package(name: "MyLib")\n'
    )

    surfaces = dry_run_surfaces(run_surfaces_script(tmp_path))

    assert [(s["runner"], s["path"]) for s in surfaces] == [("xcuitest", ".")]


@pytest.mark.level_3a
def test_xcodeproj_in_apps_dir_emits_scoped_surface(tmp_path: Path) -> None:
    """apps/<app>/<app>.xcodeproj yields a surface scoped to that app directory."""
    xcodeproj = tmp_path / "apps" / "iOS" / "iOS.xcodeproj"
    xcodeproj.mkdir(parents=True)
    (xcodeproj / "project.pbxproj").write_text("")

    surfaces = dry_run_surfaces(run_surfaces_script(tmp_path))

    assert [(s["id"], s["runner"], s["path"]) for s in surfaces] == [
        ("iOS", "xcuitest", "apps/iOS")
    ]
    assert surfaces[0]["testDir"] == "apps/iOS/UITests"


@pytest.mark.level_3a
def test_migrate_native_appends_ios_surface_to_existing_manifest(tmp_path: Path) -> None:
    """--migrate-native appends only the new xcuitest surface to a web manifest."""
    (tmp_path / ".specs").mkdir()
    (tmp_path / ".specs" / "surfaces.yaml").write_text(
        "surfaces:\n"
        "  - id: web\n"
        "    name: Web\n"
        "    path: .\n"
        "    testDir: tests/e2e\n"
        "    runner: playwright\n"
    )
    (tmp_path / "Package.swift").write_text("// swift-tools-version: 5.9\n")

    result = run_surfaces_script(tmp_path, "--migrate-native")

    assert "Would append to .specs/surfaces.yaml" in result.stdout
    assert [s["runner"] for s in dry_run_surfaces(result)] == ["xcuitest"]


@pytest.mark.level_3a
def test_migrate_native_is_noop_when_xcuitest_already_declared(tmp_path: Path) -> None:
    """--migrate-native writes nothing when an xcuitest surface already exists."""
    (tmp_path / ".specs").mkdir()
    (tmp_path / ".specs" / "surfaces.yaml").write_text(
        "surfaces:\n"
        "  - id: default\n"
        "    name: Default\n"
        "    path: .\n"
        "    testDir: UITests\n"
        "    runner: xcuitest\n"
        "    platform: ios\n"
    )
    (tmp_path / "Package.swift").write_text("// swift-tools-version: 5.9\n")

    result = run_surfaces_script(tmp_path, "--migrate-native")

    assert dry_run_surfaces(result) == []
    assert "surfaces.yaml is up to date" in result.stdout
