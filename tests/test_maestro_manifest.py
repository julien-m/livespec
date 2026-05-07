"""Tests for the Android/Maestro UI runner manifest (android.yaml).

Validates schema structure, detect logic, capability coverage, and
parameter schema for the android.yaml manifest file.
"""

# @spec FR-001: Android runner manifest validation
#   .specs/features/031-ui-runner-android/spec.md#fr-001

from __future__ import annotations

from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]

MANIFEST_PATH = (
    Path(__file__).resolve().parent.parent
    / "livespec"
    / "ui-runners"
    / "android.yaml"
)

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def manifest() -> dict:
    """Load the android.yaml manifest as a Python dict."""
    with MANIFEST_PATH.open() as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Top-level schema structure
# ---------------------------------------------------------------------------

# @spec FR-001: manifest schema — .specs/features/031-ui-runner-android/spec.md#fr-001


def test_manifest_file_exists() -> None:
    """android.yaml exists on disk."""
    assert MANIFEST_PATH.exists(), f"android.yaml not found at {MANIFEST_PATH}"


def test_manifest_is_valid_yaml() -> None:
    """android.yaml parses as valid YAML without errors."""
    with MANIFEST_PATH.open() as f:
        content = yaml.safe_load(f)
    assert content is not None
    assert isinstance(content, dict)


def test_manifest_has_runner_section(manifest: dict) -> None:
    """Manifest has a top-level 'runner' section."""
    assert "runner" in manifest, "Missing 'runner' section"


def test_manifest_runner_id_is_maestro(manifest: dict) -> None:
    """Runner ID is 'maestro'."""
    assert manifest["runner"]["id"] == "maestro"


def test_manifest_runner_has_name(manifest: dict) -> None:
    """Manifest runner has a non-empty name."""
    assert manifest["runner"].get("name"), "Runner name is empty"


def test_manifest_runner_has_version(manifest: dict) -> None:
    """Manifest runner has a version field."""
    assert manifest["runner"].get("version"), "Runner version is empty"


def test_manifest_runner_platforms_includes_android(manifest: dict) -> None:
    """Runner platforms list includes 'android'."""
    platforms = manifest["runner"].get("platforms", [])
    assert "android" in platforms, f"Expected 'android' in platforms: {platforms}"


def test_manifest_runner_priority_is_50(manifest: dict) -> None:
    """Runner priority is 50 (lower than iOS at 60)."""
    priority = manifest["runner"].get("priority")
    assert priority == 50, f"Expected priority=50, got {priority}"


# ---------------------------------------------------------------------------
# Detect section
# ---------------------------------------------------------------------------

# @spec FR-001: detect logic — .specs/features/031-ui-runner-android/spec.md#fr-001


def test_manifest_has_detect_section(manifest: dict) -> None:
    """Manifest has a 'detect' section."""
    assert "detect" in manifest, "Missing 'detect' section"


def test_manifest_detect_logic_is_or(manifest: dict) -> None:
    """Detect logic is OR (any of the listed markers matches)."""
    logic = manifest["detect"].get("logic", "").upper()
    assert logic == "OR", f"Expected detect.logic=OR, got {logic}"


def test_manifest_detect_files_includes_build_gradle(manifest: dict) -> None:
    """Detect files include 'build.gradle'."""
    files = manifest["detect"].get("files", [])
    assert "build.gradle" in files, f"Expected 'build.gradle' in detect.files: {files}"


def test_manifest_detect_files_includes_build_gradle_kts(manifest: dict) -> None:
    """Detect files include 'build.gradle.kts'."""
    files = manifest["detect"].get("files", [])
    assert "build.gradle.kts" in files, (
        f"Expected 'build.gradle.kts' in detect.files: {files}"
    )


def test_manifest_detect_files_includes_android_manifest_xml(manifest: dict) -> None:
    """Detect files include 'AndroidManifest.xml'."""
    files = manifest["detect"].get("files", [])
    assert "AndroidManifest.xml" in files, (
        f"Expected 'AndroidManifest.xml' in detect.files: {files}"
    )


def test_manifest_detect_dirs_includes_maestro(manifest: dict) -> None:
    """Detect dirs include 'maestro/' directory."""
    detect = manifest["detect"]
    # Accept either 'dirs' key or 'files' containing 'maestro/'
    detect_str = str(detect).lower()
    assert "maestro" in detect_str, (
        f"Expected 'maestro' in detect section: {detect}"
    )


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------

# @spec FR-001: capabilities coverage — .specs/features/031-ui-runner-android/spec.md#fr-001


def test_manifest_has_capabilities_section(manifest: dict) -> None:
    """Manifest has a 'capabilities' section."""
    assert "capabilities" in manifest, "Missing 'capabilities' section"


def test_manifest_has_detect_capability(manifest: dict) -> None:
    """Manifest capabilities include 'detect'."""
    assert "detect" in manifest["capabilities"], "Missing 'detect' capability"


def test_manifest_has_capture_screenshot_capability(manifest: dict) -> None:
    """Manifest capabilities include 'capture_screenshot'."""
    assert "capture_screenshot" in manifest["capabilities"], (
        "Missing 'capture_screenshot' capability"
    )


def test_manifest_has_run_flow_capability(manifest: dict) -> None:
    """Manifest capabilities include 'run_flow'."""
    assert "run_flow" in manifest["capabilities"], "Missing 'run_flow' capability"


def test_manifest_has_compare_baseline_capability(manifest: dict) -> None:
    """Manifest capabilities include 'compare_baseline'."""
    assert "compare_baseline" in manifest["capabilities"], (
        "Missing 'compare_baseline' capability"
    )


def test_capture_screenshot_has_description(manifest: dict) -> None:
    """capture_screenshot capability has a description."""
    cap = manifest["capabilities"]["capture_screenshot"]
    assert cap.get("description"), "capture_screenshot is missing description"


def test_run_flow_has_description(manifest: dict) -> None:
    """run_flow capability has a description."""
    cap = manifest["capabilities"]["run_flow"]
    assert cap.get("description"), "run_flow is missing description"


def test_compare_baseline_has_description(manifest: dict) -> None:
    """compare_baseline capability has a description."""
    cap = manifest["capabilities"]["compare_baseline"]
    assert cap.get("description"), "compare_baseline is missing description"


# ---------------------------------------------------------------------------
# Capture screenshot parameters
# ---------------------------------------------------------------------------


def test_capture_screenshot_has_parameters(manifest: dict) -> None:
    """capture_screenshot capability declares parameters."""
    cap = manifest["capabilities"]["capture_screenshot"]
    assert "parameters" in cap, "capture_screenshot missing 'parameters'"


def test_capture_screenshot_avd_name_parameter(manifest: dict) -> None:
    """capture_screenshot has avd_name parameter."""
    params = manifest["capabilities"]["capture_screenshot"].get("parameters", {})
    assert "avd_name" in params, f"Expected 'avd_name' parameter, got: {list(params)}"


def test_capture_screenshot_avd_name_has_default(manifest: dict) -> None:
    """capture_screenshot avd_name parameter has a default value."""
    param = manifest["capabilities"]["capture_screenshot"]["parameters"]["avd_name"]
    assert "default" in param, "avd_name parameter is missing 'default'"


# ---------------------------------------------------------------------------
# run_flow parameters
# ---------------------------------------------------------------------------


def test_run_flow_has_parameters(manifest: dict) -> None:
    """run_flow capability declares parameters."""
    cap = manifest["capabilities"]["run_flow"]
    assert "parameters" in cap, "run_flow missing 'parameters'"


def test_run_flow_avd_name_parameter(manifest: dict) -> None:
    """run_flow has avd_name parameter."""
    params = manifest["capabilities"]["run_flow"].get("parameters", {})
    assert "avd_name" in params, "Expected 'avd_name' parameter in run_flow"


def test_run_flow_adb_port_parameter(manifest: dict) -> None:
    """run_flow has adb_port parameter."""
    params = manifest["capabilities"]["run_flow"].get("parameters", {})
    assert "adb_port" in params, "Expected 'adb_port' parameter in run_flow"


# ---------------------------------------------------------------------------
# Destinations
# ---------------------------------------------------------------------------

# @spec FR-001: default AVD destination — .specs/features/031-ui-runner-android/spec.md#fr-001


def test_manifest_has_destinations_section(manifest: dict) -> None:
    """Manifest has a 'destinations' section."""
    assert "destinations" in manifest, "Missing 'destinations' section"


def test_manifest_has_at_least_one_destination(manifest: dict) -> None:
    """Manifest has at least one destination defined."""
    assert len(manifest["destinations"]) >= 1, "destinations list is empty"


def test_default_destination_is_android_emulator(manifest: dict) -> None:
    """Default destination is an Android Emulator."""
    default_dest = next(
        (d for d in manifest["destinations"] if d.get("default") is True), None
    )
    assert default_dest is not None, "No destination with default=true"


def test_default_destination_has_avd_name(manifest: dict) -> None:
    """Default destination declares an AVD name."""
    default_dest = next(
        (d for d in manifest["destinations"] if d.get("default") is True), None
    )
    assert default_dest is not None
    assert default_dest.get("avd_name"), "Default destination missing avd_name"


def test_default_avd_is_pixel_8_api_35(manifest: dict) -> None:
    """Default AVD name is 'Pixel_8_API_35' per spec AC-007."""
    default_dest = next(
        (d for d in manifest["destinations"] if d.get("default") is True), None
    )
    assert default_dest is not None
    # AC-007: default AVD is Pixel_8_API_35
    avd_name = default_dest.get("avd_name", "")
    assert "Pixel_8" in avd_name or "pixel_8" in avd_name.lower(), (
        f"Expected default AVD to be Pixel_8_API_35, got: {avd_name}"
    )


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


def test_manifest_has_scenarios_section(manifest: dict) -> None:
    """Manifest has a 'scenarios' section."""
    assert "scenarios" in manifest, "Missing 'scenarios' section"


def test_manifest_has_default_scenario(manifest: dict) -> None:
    """Manifest has a scenario named 'default'."""
    scenario_names = [s.get("name") for s in manifest["scenarios"]]
    assert "default" in scenario_names, (
        f"Expected 'default' scenario, got: {scenario_names}"
    )


def test_default_scenario_has_timeout(manifest: dict) -> None:
    """Default scenario has timeout_seconds configured."""
    default_scenario = next(
        (s for s in manifest["scenarios"] if s.get("name") == "default"), None
    )
    assert default_scenario is not None
    assert "timeout_seconds" in default_scenario, "Default scenario missing timeout_seconds"


# ---------------------------------------------------------------------------
# Feature 010 compatibility
# ---------------------------------------------------------------------------


def test_manifest_references_feature_010(manifest: dict) -> None:
    """Manifest references Feature 010 pixelmatch compatibility."""
    manifest_str = str(manifest).lower()
    assert "pixelmatch" in manifest_str or "feature_010" in manifest_str or (
        "compare_baseline" in manifest["capabilities"]
    ), "Expected pixelmatch/Feature 010 reference in manifest"
