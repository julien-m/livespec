"""Schema validation tests for the iOS/watchOS XCUITest runner manifest.

Tests that ios.yaml exists, is valid YAML, and satisfies the UIRunnerSchema
requirements defined in Feature 027.
"""

# mypy: disable-error-code=import-untyped
# The project uses PyYAML without installed type stubs in this environment.
# @spec FR-001: iOS/watchOS manifest schema
# .specs/features/030-ui-runner-ios-watchos/spec.md#fr-001

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

MANIFEST_PATH = (
    Path(__file__).resolve().parent.parent / "livespec" / "ui-runners" / "ios.yaml"
)


@pytest.fixture(scope="module")
def manifest() -> dict[str, Any]:
    """Load the ios.yaml manifest once for all tests in this module."""
    with MANIFEST_PATH.open() as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Existence and parsability
# ---------------------------------------------------------------------------

def test_manifest_file_exists() -> None:
    """ios.yaml must exist at the expected path."""
    assert MANIFEST_PATH.exists(), f"ios.yaml not found at {MANIFEST_PATH}"


def test_manifest_is_valid_yaml(manifest: dict[str, Any]) -> None:
    """ios.yaml must be parseable as YAML and return a non-None value."""
    assert manifest is not None
    assert isinstance(manifest, dict)


# ---------------------------------------------------------------------------
# Runner section
# ---------------------------------------------------------------------------

def test_manifest_has_runner_section(manifest: dict[str, Any]) -> None:
    """Manifest must have a 'runner' top-level section."""
    assert "runner" in manifest


def test_manifest_runner_id_is_ios(manifest: dict[str, Any]) -> None:
    """runner.id must be 'ios'."""
    assert manifest["runner"]["id"] == "ios"


def test_manifest_runner_has_name(manifest: dict[str, Any]) -> None:
    """runner.name must be present and non-empty."""
    name = manifest["runner"].get("name", "")
    assert name, "runner.name must not be empty"


def test_manifest_runner_has_version(manifest: dict[str, Any]) -> None:
    """runner.version must be present."""
    assert "version" in manifest["runner"]


def test_manifest_runner_has_platforms(manifest: dict[str, Any]) -> None:
    """runner.platforms must include 'ios' and 'watchos'."""
    platforms = manifest["runner"].get("platforms", [])
    assert "ios" in platforms
    assert "watchos" in platforms


# ---------------------------------------------------------------------------
# Detect section
# ---------------------------------------------------------------------------

def test_manifest_has_detect_section(manifest: dict[str, Any]) -> None:
    """Manifest must have a 'detect' section for project detection."""
    assert "detect" in manifest


def test_manifest_detect_has_files(manifest: dict[str, Any]) -> None:
    """detect.files must be a non-empty list."""
    files = manifest["detect"].get("files", [])
    assert isinstance(files, list)
    assert len(files) > 0


def test_manifest_detect_files_includes_package_swift(
    manifest: dict[str, Any],
) -> None:
    """detect.files must include 'Package.swift' for SPM projects."""
    files = manifest["detect"]["files"]
    assert "Package.swift" in files


def test_manifest_detect_files_includes_xcodeproj(
    manifest: dict[str, Any],
) -> None:
    """detect.files must include a glob matching .xcodeproj directories."""
    files = manifest["detect"]["files"]
    has_xcodeproj = any(".xcodeproj" in f for f in files)
    assert has_xcodeproj, "detect.files must include a *.xcodeproj pattern"


def test_manifest_detect_logic_is_or(manifest: dict[str, Any]) -> None:
    """detect.logic must be 'OR' for Xcode project detection."""
    assert manifest["detect"].get("logic") == "OR"


# ---------------------------------------------------------------------------
# Capabilities section
# ---------------------------------------------------------------------------

def test_manifest_has_capabilities_section(manifest: dict[str, Any]) -> None:
    """Manifest must have a 'capabilities' section."""
    assert "capabilities" in manifest


def test_manifest_capability_capture_screenshot(
    manifest: dict[str, Any],
) -> None:
    """capabilities.capture_screenshot must be defined."""
    caps = manifest["capabilities"]
    assert "capture_screenshot" in caps


def test_manifest_capability_run_flow(manifest: dict[str, Any]) -> None:
    """capabilities.run_flow must be defined."""
    caps = manifest["capabilities"]
    assert "run_flow" in caps


def test_manifest_capability_compare_baseline(
    manifest: dict[str, Any],
) -> None:
    """capabilities.compare_baseline must be defined."""
    caps = manifest["capabilities"]
    assert "compare_baseline" in caps


def test_manifest_capture_screenshot_has_destination_param(
    manifest: dict[str, Any],
) -> None:
    """capture_screenshot capability must declare a 'destination' parameter."""
    cap = manifest["capabilities"]["capture_screenshot"]
    params = cap.get("parameters", {})
    assert "destination" in params


def test_manifest_capture_screenshot_destination_has_default(
    manifest: dict[str, Any],
) -> None:
    """capture_screenshot.destination must have a default iOS Simulator value."""
    params = manifest["capabilities"]["capture_screenshot"]["parameters"]
    default = params["destination"].get("default", "")
    assert "iOS Simulator" in default


def test_manifest_capture_screenshot_has_launch_arguments_param(
    manifest: dict[str, Any],
) -> None:
    """capture_screenshot must expose launch_arguments parameter for state presets."""
    params = manifest["capabilities"]["capture_screenshot"].get("parameters", {})
    assert "launch_arguments" in params


# ---------------------------------------------------------------------------
# Destinations section
# ---------------------------------------------------------------------------

def test_manifest_has_destinations_section(manifest: dict[str, Any]) -> None:
    """Manifest must have a 'destinations' array."""
    assert "destinations" in manifest


def test_manifest_destinations_is_list(manifest: dict[str, Any]) -> None:
    """destinations must be a list."""
    assert isinstance(manifest["destinations"], list)


def test_manifest_destinations_has_at_least_one_entry(
    manifest: dict[str, Any],
) -> None:
    """destinations must declare at least one simulator entry."""
    assert len(manifest["destinations"]) >= 1


def test_manifest_has_ios_simulator_destination(
    manifest: dict[str, Any],
) -> None:
    """destinations must include at least one iOS Simulator entry."""
    destinations = manifest["destinations"]
    ios_dests = [d for d in destinations if "iOS Simulator" in d.get("platform", "")]
    assert len(ios_dests) >= 1, "No iOS Simulator destination declared"


def test_manifest_ios_destination_is_default(manifest: dict[str, Any]) -> None:
    """The primary iOS Simulator destination must be marked as default."""
    destinations = manifest["destinations"]
    ios_dests = [d for d in destinations if "iOS Simulator" in d.get("platform", "")]
    assert any(d.get("default") is True for d in ios_dests), (
        "At least one iOS Simulator destination must be marked as default"
    )


def test_manifest_has_watchos_simulator_destination(
    manifest: dict[str, Any],
) -> None:
    """destinations must include at least one watchOS Simulator entry."""
    destinations = manifest["destinations"]
    watch_dests = [d for d in destinations if "watchOS Simulator" in d.get("platform", "")]
    assert len(watch_dests) >= 1, "No watchOS Simulator destination declared"


# ---------------------------------------------------------------------------
# Scenarios section
# ---------------------------------------------------------------------------

def test_manifest_has_scenarios_section(manifest: dict[str, Any]) -> None:
    """Manifest must have a 'scenarios' list."""
    assert "scenarios" in manifest


def test_manifest_default_scenario_exists(manifest: dict[str, Any]) -> None:
    """A 'default' scenario must be declared."""
    scenarios = manifest["scenarios"]
    default = [s for s in scenarios if s.get("name") == "default"]
    assert len(default) >= 1, "No 'default' scenario declared"


def test_manifest_default_scenario_has_launch_arguments(
    manifest: dict[str, Any],
) -> None:
    """Default scenario must have a 'launch_arguments' field."""
    scenarios = manifest["scenarios"]
    default = next(s for s in scenarios if s.get("name") == "default")
    assert "launch_arguments" in default
