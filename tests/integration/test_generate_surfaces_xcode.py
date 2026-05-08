"""Integration tests for generate-surfaces.js against Xcode multi-target fixtures.

Spawns the Node script as a subprocess on a synthesized fixture project that
declares three test targets (AppTests, AppUITests, AppWatchTests) and asserts
the resulting surfaces.yaml contains one surface per target with stable ids
and existing `testDir` paths.
"""

# @spec FR-004: enumerate Xcode test targets — .specs/features/037-test-multi-runner-integration/spec.md#fr-004  # noqa: E501
# @spec FR-006: omit non-existent testDir — .specs/features/037-test-multi-runner-integration/spec.md#fr-006  # noqa: E501
# @spec FR-007: watchOS classification — .specs/features/037-test-multi-runner-integration/spec.md#fr-007  # noqa: E501

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest
import yaml  # type: ignore[import-untyped]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GENERATE_SCRIPT = REPO_ROOT / "scripts" / "generate-surfaces.js"

_UNIT_PT = "com.apple.product-type.bundle.unit-test"
_UI_PT = "com.apple.product-type.bundle.ui-testing"
PBXPROJ_TEMPLATE = (
    "// !$*UTF8*$!\n"
    "{\n"
    "\trootObject = ABC;\n"
    "\tobjects = {\n"
    "/* Begin PBXNativeTarget section */\n"
    "\t\tT1 /* AppTests */ = {isa = PBXNativeTarget; name = AppTests; "
    f'productType = "{_UNIT_PT}"; }};\n'
    "\t\tT2 /* AppUITests */ = {isa = PBXNativeTarget; name = AppUITests; "
    f'productType = "{_UI_PT}"; }};\n'
    "\t\tT3 /* AppWatchTests */ = {isa = PBXNativeTarget; name = AppWatchTests; "
    f'productType = "{_UNIT_PT}"; }};\n'
    "/* End PBXNativeTarget section */\n"
    "\t};\n"
    "}\n"
)


def _node_available() -> bool:
    return shutil.which("node") is not None


@pytest.fixture
def xcode_multi_target_project(tmp_path: Path) -> Path:
    """Build a fixture project with three Xcode test targets at apps/App/."""
    project = tmp_path / "project"
    app = project / "apps" / "App"
    xcodeproj = app / "App.xcodeproj"
    xcodeproj.mkdir(parents=True)
    (xcodeproj / "project.pbxproj").write_text(PBXPROJ_TEMPLATE, encoding="utf-8")
    for target in ("AppTests", "AppUITests", "AppWatchTests"):
        (app / target).mkdir()
        (app / target / "placeholder.swift").write_text("// stub", encoding="utf-8")
    (project / ".specs").mkdir()
    return project


@pytest.mark.skipif(not _node_available(), reason="Node.js not installed")
def test_three_targets_emit_three_surfaces(xcode_multi_target_project: Path) -> None:
    """AC-005: three Xcode test targets produce three surfaces."""
    result = subprocess.run(
        ["node", str(GENERATE_SCRIPT), "--force"],
        cwd=xcode_multi_target_project,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    yaml_path = xcode_multi_target_project / ".specs" / "surfaces.yaml"
    assert yaml_path.exists(), "surfaces.yaml not created"
    raw = cast(dict[str, Any], yaml.safe_load(yaml_path.read_text(encoding="utf-8")))
    surfaces = cast(list[dict[str, Any]], raw.get("surfaces", []))
    xcuitest_surfaces = [s for s in surfaces if s.get("runner") == "xcuitest"]
    assert len(xcuitest_surfaces) == 3, (
        f"Expected 3 xcuitest surfaces, got {len(xcuitest_surfaces)}: {xcuitest_surfaces}"
    )
    ids = {s["id"] for s in xcuitest_surfaces}
    assert ids == {
        "App-app-tests",
        "App-app-uitests",
        "App-app-watch-tests",
    }


@pytest.mark.skipif(not _node_available(), reason="Node.js not installed")
def test_watch_target_classified_as_watchos(xcode_multi_target_project: Path) -> None:
    """AC-007: WatchTests target carries platform: watchos."""
    subprocess.run(
        ["node", str(GENERATE_SCRIPT), "--force"],
        cwd=xcode_multi_target_project,
        capture_output=True,
        text=True,
        check=False,
    )
    yaml_path = xcode_multi_target_project / ".specs" / "surfaces.yaml"
    raw = cast(dict[str, Any], yaml.safe_load(yaml_path.read_text(encoding="utf-8")))
    surfaces = cast(list[dict[str, Any]], raw.get("surfaces", []))
    watch_surfaces = [s for s in surfaces if "watch" in s.get("id", "").lower()]
    assert watch_surfaces, "Expected at least one watchOS surface"
    assert all(s.get("platform") == "watchos" for s in watch_surfaces)


@pytest.mark.skipif(not _node_available(), reason="Node.js not installed")
def test_test_dirs_resolve_to_existing_paths(xcode_multi_target_project: Path) -> None:
    """AC-006: every emitted testDir points to an existing directory."""
    subprocess.run(
        ["node", str(GENERATE_SCRIPT), "--force"],
        cwd=xcode_multi_target_project,
        capture_output=True,
        text=True,
        check=False,
    )
    yaml_path = xcode_multi_target_project / ".specs" / "surfaces.yaml"
    raw = cast(dict[str, Any], yaml.safe_load(yaml_path.read_text(encoding="utf-8")))
    surfaces = cast(list[dict[str, Any]], raw.get("surfaces", []))
    xcuitest_surfaces = [s for s in surfaces if s.get("runner") == "xcuitest"]
    assert xcuitest_surfaces
    for surface in xcuitest_surfaces:
        test_dir = Path(surface["testDir"])
        if not test_dir.is_absolute():
            test_dir = xcode_multi_target_project / test_dir
        assert test_dir.exists(), f"testDir {test_dir} does not exist for surface {surface}"


@pytest.mark.skipif(not _node_available(), reason="Node.js not installed")
def test_orphan_target_is_omitted_with_warning(xcode_multi_target_project: Path) -> None:
    """AC-006: declared targets without directories are skipped with a warning."""
    shutil.rmtree(xcode_multi_target_project / "apps" / "App" / "AppWatchTests")
    result = subprocess.run(
        ["node", str(GENERATE_SCRIPT), "--force"],
        cwd=xcode_multi_target_project,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "AppWatchTests" in result.stderr
    assert "not found — skipping" in result.stderr
    yaml_path = xcode_multi_target_project / ".specs" / "surfaces.yaml"
    raw = cast(dict[str, Any], yaml.safe_load(yaml_path.read_text(encoding="utf-8")))
    surfaces = cast(list[dict[str, Any]], raw.get("surfaces", []))
    ids = {surface["id"] for surface in surfaces if surface.get("runner") == "xcuitest"}
    assert ids == {"App-app-tests", "App-app-uitests"}
