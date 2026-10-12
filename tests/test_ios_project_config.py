# LiveSpec traceability anchors
# @spec(FR-001)
# @spec(FR-005)
# @spec(AC-010)

"""Project ios.yaml configures the XCUITest runner (CLI > project config > detection)."""

# @spec FR-001: Project ios.yaml configures the iOS runner
# — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-001
# @spec AC-010: Per-scenario launch_arguments reach the XCUITest harness
# — .specs/features/030-ui-runner-ios-watchos/spec.md#ac-010

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from pytest import MonkeyPatch

from validator.ios_project_config import resolve_ios_run_settings
from validator.runner_dispatcher_impl import Surface
from validator.ui_runner_xcuitest import XCUITestRunnerHandler

_CONFIG = """
test_scheme: TopLevelUITests
scenarios:
  - name: default
    launch_arguments: ["--ui-test-mode"]
  - name: logged_in
    test_scheme: MyAppUITests
    launch_arguments: ["--ui-test-mode", "--mock-user=admin"]
"""


def _project(tmp_path: Path, body: str = _CONFIG) -> Path:
    project = tmp_path / "app"
    (project / ".specs").mkdir(parents=True)
    config = project / "livespec" / "ui-runners" / "ios.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(body, encoding="utf-8")
    return project


def _capture_flow(monkeypatch: MonkeyPatch) -> list[dict[str, Any]]:
    """Run the real handler flow while recording the xcodebuild command and env."""
    calls: list[dict[str, Any]] = []

    def fake_process(command: list[str], _cwd: Path, env: dict[str, str] | None) -> Any:
        calls.append({"command": command, "env": env})
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("validator.ios_flow_core._toolchain_blocker", lambda _h: None)
    monkeypatch.setattr(
        "validator.ios_flow_core._resolve_destination", lambda _h, _d, _p: "platform=iOS"
    )
    monkeypatch.setattr("validator.ios_flow_core._run_flow_process", fake_process)
    return calls


def _scheme(command: list[str]) -> str:
    return command[command.index("-scheme") + 1]


def test_run_flow_uses_default_scenario_and_top_level_scheme(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Without CLI values the default scenario args and top-level scheme apply."""
    calls = _capture_flow(monkeypatch)

    result = XCUITestRunnerHandler(_project(tmp_path)).run_flow()

    assert result.success is True
    assert _scheme(calls[0]["command"]) == "TopLevelUITests"
    assert json.loads(calls[0]["env"]["XCUI_LAUNCH_ARGS"]) == ["--ui-test-mode"]


def test_cli_values_win_over_project_config(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Explicit scheme and (even empty) launch arguments are never overridden."""
    calls = _capture_flow(monkeypatch)

    XCUITestRunnerHandler(_project(tmp_path)).run_flow(
        test_scheme="CliUITests", launch_arguments=[]
    )

    assert _scheme(calls[0]["command"]) == "CliUITests"
    assert calls[0]["env"] is None


def test_dispatcher_runner_config_selects_named_scenario(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """`runnerConfig.scenario` resolves scheme and launch args before capture."""
    from validator.dispatcher_core import dispatch_surface

    _project(tmp_path)
    seen: dict[str, Any] = {}

    def fake_capture(self: XCUITestRunnerHandler, screen: str, **kwargs: Any) -> Any:
        seen.update(kwargs)
        from validator.runner_xcuitest_impl import UICapabilityResult

        return UICapabilityResult(success=True)

    monkeypatch.setattr(XCUITestRunnerHandler, "detect", lambda self: True)
    monkeypatch.setattr(XCUITestRunnerHandler, "capture_screenshot", fake_capture)
    surface = Surface(
        id="ios", runner="xcuitest", path="app", runner_config={"scenario": "logged_in"}
    )

    dispatch_surface(tmp_path, surface, ["home"], {"xcuitest": XCUITestRunnerHandler})

    assert seen["test_scheme"] == "MyAppUITests"
    assert seen["launch_arguments"] == ["--ui-test-mode", "--mock-user=admin"]


def test_without_config_the_runner_keeps_autodetection(tmp_path: Path) -> None:
    """No project ios.yaml leaves the scheme to autodetection (None)."""
    (tmp_path / ".specs").mkdir()

    assert resolve_ios_run_settings(tmp_path, None, None) == (None, None)


def test_config_is_found_from_a_subdirectory_up_to_the_project_root(tmp_path: Path) -> None:
    """A surface under `ios/` reads the project-root ios.yaml."""
    project = _project(tmp_path)
    (project / "ios").mkdir()

    assert resolve_ios_run_settings(project / "ios", None, None)[0] == "TopLevelUITests"


@pytest.mark.parametrize(
    ("body", "scenario", "message"),
    [
        (_CONFIG, "missing", "not declared"),
        ("scenarios:\n  - name: a\n    timeout_seconds: 30\n", None, "unsupported keys"),
        ("scenarios:\n  - name: a\n  - name: a\n", None, "unique"),
        ("scenarios:\n  - launch_arguments: []\n", None, "name is required"),
    ],
)
def test_malformed_config_or_unknown_scenario_fails_loudly(
    tmp_path: Path, body: str, scenario: str | None, message: str
) -> None:
    """Invalid configs are reported instead of being silently ignored."""
    with pytest.raises(ValueError, match=message):
        resolve_ios_run_settings(_project(tmp_path, body), None, None, scenario)


def test_invalid_config_surfaces_as_runner_error(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """run_flow returns a failed result naming the config problem."""
    _capture_flow(monkeypatch)
    project = _project(tmp_path, "scenarios: nope\n")

    result = XCUITestRunnerHandler(project).run_flow()

    assert result.success is False
    assert result.error is not None and "Invalid iOS runner config" in result.error
