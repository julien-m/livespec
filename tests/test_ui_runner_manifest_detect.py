# LiveSpec traceability anchors
# @spec(FR-001)
# @spec(AC-002)

"""The iOS and Android runner handlers detect projects from their manifests."""

# @spec FR-001: Runner manifest drives project detection
# — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-001
# @spec AC-002: detect.files markers select the iOS runner
# — .specs/features/030-ui-runner-ios-watchos/spec.md#ac-002

from __future__ import annotations

from pathlib import Path

import pytest
from pytest import MonkeyPatch

from validator.runner_dispatcher_impl import Surface
from validator.ui_runner_maestro import MaestroRunnerHandler
from validator.ui_runner_manifest import manifest_detects
from validator.ui_runner_xcuitest import XCUITestRunnerHandler


def _manifest(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "runner.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_dispatcher_detection_follows_the_ios_manifest(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Editing ios.yaml detect markers changes what the dispatcher accepts."""
    from validator.dispatcher_core import dispatch_surface

    manifest = _manifest(tmp_path, "detect:\n  files: ['*.marker']\n  logic: OR\n")
    monkeypatch.setattr(
        "validator.runner_xcuitest_impl.xcuitest_runner_manifest_path", lambda: manifest
    )
    project = tmp_path / "app"
    project.mkdir()
    (project / "Package.swift").write_text("// swift", encoding="utf-8")
    surface = Surface(id="ios", runner="ios", path="app")

    rows = dispatch_surface(tmp_path, surface, [], {"ios": XCUITestRunnerHandler})

    assert [row.status for row in rows] == ["blocked"]
    (project / "App.marker").write_text("", encoding="utf-8")
    assert XCUITestRunnerHandler(project).detect() is True


def test_builtin_android_manifest_dirs_are_honoured(tmp_path: Path) -> None:
    """`.specs/maestro` from android.yaml `dirs` selects the Maestro runner."""
    assert MaestroRunnerHandler(tmp_path).detect() is False
    (tmp_path / ".specs" / "maestro").mkdir(parents=True)
    assert MaestroRunnerHandler(tmp_path).detect() is True


def test_and_logic_requires_every_marker(tmp_path: Path) -> None:
    """AND logic needs both the glob file and the directory."""
    detect = {"files": ["*.cfg"], "dirs": ["flows"], "logic": "AND"}
    (tmp_path / "a.cfg").write_text("", encoding="utf-8")
    assert manifest_detects(tmp_path, detect) is False
    (tmp_path / "flows").mkdir()
    assert manifest_detects(tmp_path, detect) is True


@pytest.mark.parametrize(
    "detect", [{"files": ["x"], "logic": "XOR"}, {"logic": "OR"}, {"files": "x"}]
)
def test_malformed_detect_block_is_rejected(tmp_path: Path, detect: dict[str, object]) -> None:
    """Unknown logic, missing markers and non-list markers fail loudly."""
    with pytest.raises(ValueError):
        manifest_detects(tmp_path, detect)
