# LiveSpec traceability anchors
# @spec(AC-001)
# @spec(AC-003)

"""Tests for the Android/Maestro UI runner manifest (android.yaml).

The manifest is loaded through the production loader and its declarative
detect rules are checked against the runner handler that implements them.
"""

# @spec FR-001: Android runner manifest validation
#   .specs/features/031-ui-runner-android/spec.md#fr-001

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from validator.ui_runner_maestro import MaestroRunnerHandler, load_maestro_runner_manifest

REQUIRED_CAPABILITIES = {"detect", "capture_screenshot", "run_flow", "compare_baseline"}


@pytest.fixture
def manifest() -> dict[str, Any]:
    """Load android.yaml with the loader the runner uses."""
    return load_maestro_runner_manifest()


def _default(items: list[dict[str, Any]], key: str, value: object) -> dict[str, Any]:
    matches = [item for item in items if item.get(key) == value]
    assert len(matches) == 1, f"expected exactly one {key}={value!r}, got {matches}"
    return matches[0]


def test_manifest_is_valid_yaml(manifest: dict[str, Any]) -> None:
    """AC-001: the manifest carries every section the Android runner contract needs."""
    runner = manifest["runner"]
    assert runner["id"] == "maestro"
    assert runner["name"] and runner["version"]
    assert "android" in runner["platforms"]
    assert manifest["detect"]["logic"].upper() == "OR"

    capabilities = manifest["capabilities"]
    assert set(capabilities) >= REQUIRED_CAPABILITIES
    assert all(capabilities[name].get("description") for name in REQUIRED_CAPABILITIES)
    assert "pixelmatch" in capabilities["compare_baseline"]["command"]

    default_destination = _default(manifest["destinations"], "default", True)
    default_avd = default_destination["avd_name"]
    assert default_avd == "Pixel_8_API_35"
    for capability in ("capture_screenshot", "run_flow"):
        parameters = capabilities[capability]["parameters"]
        assert parameters["avd_name"]["default"] == default_avd
        assert "adb_port" in parameters

    assert _default(manifest["scenarios"], "name", "default")["timeout_seconds"] > 0


def test_manifest_runner_priority_is_50(manifest: dict[str, Any]) -> None:
    """AC-003: runner priority is 50 (lower than iOS at 60)."""
    assert manifest["runner"]["priority"] == 50


def test_manifest_detect_rules_match_runner_handler(
    manifest: dict[str, Any], tmp_path: Path
) -> None:
    """Every declared detect marker is honoured by the handler, and nothing else is."""
    detect = manifest["detect"]
    assert not MaestroRunnerHandler(tmp_path).detect()

    for marker in detect["files"]:
        project = tmp_path / f"file-{marker}"
        project.mkdir()
        (project / marker).write_text("", encoding="utf-8")
        assert MaestroRunnerHandler(project).detect(), marker

    for directory in detect["dirs"]:
        project = tmp_path / f"dir-{directory.replace('/', '-')}"
        (project / directory).mkdir(parents=True)
        assert MaestroRunnerHandler(project).detect(), directory
