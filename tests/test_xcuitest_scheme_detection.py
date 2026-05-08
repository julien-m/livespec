"""XCUITest scheme/project auto-detection tests (Feature 038).

These tests pin the contract that XCUITestRunnerHandler can recover scheme
information from `<xcodeproj>/xcshareddata/xcschemes/*.xcscheme` when a
caller does not pass `test_scheme` explicitly. This is what unblocks
`livespec ui-runner dispatch` on projects whose `surfaces.yaml` was
generated before runnerConfig was wired (migration v8/v12 era).
"""

# @spec FR-003: xcuitest auto-detect scheme — .specs/features/038-runner-config-wiring/spec.md#fr-003  # noqa: E501
# @spec FR-004: xcuitest auto-detect project — .specs/features/038-runner-config-wiring/spec.md#fr-004  # noqa: E501

from __future__ import annotations

from pathlib import Path

from validator.ui_runner_xcuitest import XCUITestRunnerHandler


def _make_xcodeproj(root: Path, name: str = "STRAPT", schemes: list[str] | None = None) -> Path:
    """Create a minimal .xcodeproj fixture with shared schemes."""
    xcodeproj = root / f"{name}.xcodeproj"
    xcodeproj.mkdir(parents=True, exist_ok=True)
    # Mark it as a real project so handler.detect() returns True
    (xcodeproj / "project.pbxproj").write_text("// minimal pbxproj", encoding="utf-8")
    if schemes:
        scheme_dir = xcodeproj / "xcshareddata" / "xcschemes"
        scheme_dir.mkdir(parents=True, exist_ok=True)
        for scheme in schemes:
            (scheme_dir / f"{scheme}.xcscheme").write_text(
                "<?xml version='1.0'?><Scheme/>", encoding="utf-8"
            )
    return xcodeproj


def test_find_xcodeproj_returns_first_project(tmp_path: Path) -> None:
    _make_xcodeproj(tmp_path, "MyApp")
    handler = XCUITestRunnerHandler(tmp_path)
    found = handler._find_xcodeproj()
    assert found is not None
    assert found.name == "MyApp.xcodeproj"


def test_find_xcodeproj_prefers_workspace(tmp_path: Path) -> None:
    _make_xcodeproj(tmp_path, "MyApp")
    workspace = tmp_path / "MyApp.xcworkspace"
    workspace.mkdir()
    handler = XCUITestRunnerHandler(tmp_path)
    found = handler._find_xcodeproj()
    assert found is not None
    assert found.name == "MyApp.xcworkspace"


def test_find_xcodeproj_returns_none_when_absent(tmp_path: Path) -> None:
    handler = XCUITestRunnerHandler(tmp_path)
    assert handler._find_xcodeproj() is None


def test_list_shared_schemes_reads_xcshareddata(tmp_path: Path) -> None:
    xcodeproj = _make_xcodeproj(
        tmp_path, "STRAPT", schemes=["STRAPT", "STRAPT Watch App"]
    )
    handler = XCUITestRunnerHandler(tmp_path)
    schemes = handler._list_shared_schemes(xcodeproj)
    assert schemes == ["STRAPT", "STRAPT Watch App"]


def test_list_shared_schemes_empty_when_none_shared(tmp_path: Path) -> None:
    xcodeproj = _make_xcodeproj(tmp_path, "MyApp")
    handler = XCUITestRunnerHandler(tmp_path)
    assert handler._list_shared_schemes(xcodeproj) == []


def test_autodetect_scheme_picks_ios_first(tmp_path: Path) -> None:
    xcodeproj = _make_xcodeproj(
        tmp_path, "STRAPT", schemes=["STRAPT", "STRAPT Watch App"]
    )
    handler = XCUITestRunnerHandler(tmp_path)
    assert handler._autodetect_scheme(xcodeproj, platform="ios") == "STRAPT"


def test_autodetect_scheme_picks_watch_for_watchos(tmp_path: Path) -> None:
    xcodeproj = _make_xcodeproj(
        tmp_path, "STRAPT", schemes=["STRAPT", "STRAPT Watch App"]
    )
    handler = XCUITestRunnerHandler(tmp_path)
    assert (
        handler._autodetect_scheme(xcodeproj, platform="watchos")
        == "STRAPT Watch App"
    )


def test_autodetect_scheme_returns_none_when_no_schemes(tmp_path: Path) -> None:
    xcodeproj = _make_xcodeproj(tmp_path, "Empty")
    handler = XCUITestRunnerHandler(tmp_path)
    assert handler._autodetect_scheme(xcodeproj, platform="ios") is None


def test_autodetect_scheme_returns_none_for_watchos_when_no_watch_scheme(
    tmp_path: Path,
) -> None:
    xcodeproj = _make_xcodeproj(tmp_path, "STRAPT", schemes=["STRAPT"])
    handler = XCUITestRunnerHandler(tmp_path)
    assert handler._autodetect_scheme(xcodeproj, platform="watchos") is None


def test_build_xcodebuild_command_includes_scheme_and_project(tmp_path: Path) -> None:
    handler = XCUITestRunnerHandler(tmp_path)
    cmd = handler._build_xcodebuild_command(
        destination="platform=iOS Simulator,name=iPhone 16",
        test_scheme="STRAPT",
        xcresult_path=tmp_path / "r.xcresult",
        project="STRAPT.xcodeproj",
    )
    assert "-scheme" in cmd
    assert "STRAPT" in cmd
    assert "-project" in cmd
    assert "STRAPT.xcodeproj" in cmd


def test_build_xcodebuild_command_workspace_takes_precedence(tmp_path: Path) -> None:
    handler = XCUITestRunnerHandler(tmp_path)
    cmd = handler._build_xcodebuild_command(
        destination="platform=iOS Simulator,name=iPhone 16",
        test_scheme="STRAPT",
        xcresult_path=tmp_path / "r.xcresult",
        project="STRAPT.xcodeproj",
        workspace="STRAPT.xcworkspace",
    )
    assert "-workspace" in cmd
    assert "STRAPT.xcworkspace" in cmd
    assert "-project" not in cmd


# --------------------------------------------------------------------------
# Destination auto-detection (Strapt regression: hardcoded iPhone 16 fails on
# machines that only ship iPhone 17+ runtimes).
# --------------------------------------------------------------------------


def _fake_simctl_list(devices_by_runtime: dict[str, list[dict[str, object]]]) -> dict[str, object]:
    return {"devices": devices_by_runtime}


def test_autodetect_destination_picks_first_available_iphone(
    tmp_path: Path, monkeypatch: object
) -> None:
    handler = XCUITestRunnerHandler(tmp_path)
    fake = _fake_simctl_list(
        {
            "com.apple.CoreSimulator.SimRuntime.iOS-26-4": [
                {"name": "iPhone 17", "isAvailable": True},
                {"name": "iPhone 17 Pro", "isAvailable": True},
            ],
        }
    )
    handler._list_simulators = lambda: fake  # type: ignore[method-assign]
    assert (
        handler._autodetect_destination(platform="ios")
        == "platform=iOS Simulator,name=iPhone 17"
    )


def test_autodetect_destination_skips_unavailable_devices(tmp_path: Path) -> None:
    handler = XCUITestRunnerHandler(tmp_path)
    fake = _fake_simctl_list(
        {
            "com.apple.CoreSimulator.SimRuntime.iOS-26-4": [
                {"name": "iPhone 16", "isAvailable": False},
                {"name": "iPhone 17", "isAvailable": True},
            ],
        }
    )
    handler._list_simulators = lambda: fake  # type: ignore[method-assign]
    assert (
        handler._autodetect_destination(platform="ios")
        == "platform=iOS Simulator,name=iPhone 17"
    )


def test_autodetect_destination_picks_apple_watch_for_watchos(tmp_path: Path) -> None:
    handler = XCUITestRunnerHandler(tmp_path)
    fake = _fake_simctl_list(
        {
            "com.apple.CoreSimulator.SimRuntime.watchOS-11-0": [
                {"name": "Apple Watch Series 10 (46mm)", "isAvailable": True},
            ],
            "com.apple.CoreSimulator.SimRuntime.iOS-26-4": [
                {"name": "iPhone 17", "isAvailable": True},
            ],
        }
    )
    handler._list_simulators = lambda: fake  # type: ignore[method-assign]
    assert (
        handler._autodetect_destination(platform="watchos")
        == "platform=watchOS Simulator,name=Apple Watch Series 10 (46mm)"
    )


def test_autodetect_destination_excludes_watch_for_ios(tmp_path: Path) -> None:
    handler = XCUITestRunnerHandler(tmp_path)
    fake = _fake_simctl_list(
        {
            "com.apple.CoreSimulator.SimRuntime.iOS-26-4": [
                # An old runtime listing that mistakenly included a watch entry
                {"name": "Apple Watch Series 10", "isAvailable": True},
                {"name": "iPhone 17", "isAvailable": True},
            ],
        }
    )
    handler._list_simulators = lambda: fake  # type: ignore[method-assign]
    assert (
        handler._autodetect_destination(platform="ios")
        == "platform=iOS Simulator,name=iPhone 17"
    )


def test_autodetect_destination_returns_none_when_no_simulators(tmp_path: Path) -> None:
    handler = XCUITestRunnerHandler(tmp_path)
    handler._list_simulators = lambda: {}  # type: ignore[method-assign]
    assert handler._autodetect_destination(platform="ios") is None


def test_autodetect_destination_prefers_newest_runtime(tmp_path: Path) -> None:
    handler = XCUITestRunnerHandler(tmp_path)
    fake = _fake_simctl_list(
        {
            "com.apple.CoreSimulator.SimRuntime.iOS-17-0": [
                {"name": "iPhone 15", "isAvailable": True},
            ],
            "com.apple.CoreSimulator.SimRuntime.iOS-26-4": [
                {"name": "iPhone 17", "isAvailable": True},
            ],
        }
    )
    handler._list_simulators = lambda: fake  # type: ignore[method-assign]
    # Reverse-sorted runtime keys → iOS-26-4 wins → iPhone 17 returned.
    assert (
        handler._autodetect_destination(platform="ios")
        == "platform=iOS Simulator,name=iPhone 17"
    )
