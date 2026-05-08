"""Pure-string assertions for handler preflight diagnostics.

These tests cover FR-011, FR-012, and FR-013. They monkeypatch the underlying
checks so the dispatcher gets actionable text on every failure mode.
"""

# @spec FR-011: dispatcher preflight diagnostic — .specs/features/037-test-multi-runner-integration/spec.md#fr-011  # noqa: E501
# @spec FR-012: XCUITest preflight messaging — .specs/features/037-test-multi-runner-integration/spec.md#fr-012  # noqa: E501
# @spec FR-013: Maestro preflight messaging — .specs/features/037-test-multi-runner-integration/spec.md#fr-013  # noqa: E501

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from validator.ui_runner_maestro import MaestroRunnerHandler
from validator.ui_runner_web import WebRunnerHandler
from validator.ui_runner_xcuitest import XCUITestRunnerHandler

# ---------------------------------------------------------------------------
# Web (Playwright)
# ---------------------------------------------------------------------------


def test_web_preflight_missing_package_json(tmp_path: Path) -> None:
    msg = WebRunnerHandler(tmp_path).preflight_message()
    assert "@playwright/test not installed" in msg
    assert "no package.json" in msg


def test_web_preflight_missing_playwright_config(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    msg = WebRunnerHandler(tmp_path).preflight_message()
    assert "@playwright/test not installed" in msg
    assert "npm install -D @playwright/test" in msg


def test_web_preflight_ready(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "playwright.config.ts").write_text("// stub", encoding="utf-8")
    assert WebRunnerHandler(tmp_path).preflight_message() == ""


# ---------------------------------------------------------------------------
# XCUITest (iOS / watchOS)
# ---------------------------------------------------------------------------


def test_xcuitest_preflight_on_linux(tmp_path: Path) -> None:
    handler = XCUITestRunnerHandler(tmp_path)
    with patch("validator.ui_runner_xcuitest.platform.system", return_value="Linux"):
        msg = handler.preflight_message()
    assert "XCUITest runner requires macOS host" in msg
    assert "linux" in msg


def test_xcuitest_preflight_xcrun_missing(tmp_path: Path) -> None:
    handler = XCUITestRunnerHandler(tmp_path)
    with (
        patch("validator.ui_runner_xcuitest.platform.system", return_value="Darwin"),
        patch.object(handler, "_get_toolchain_path", return_value=None),
    ):
        msg = handler.preflight_message()
    assert "xcrun simctl not found" in msg


def test_xcuitest_preflight_ready(tmp_path: Path) -> None:
    handler = XCUITestRunnerHandler(tmp_path)
    with (
        patch("validator.ui_runner_xcuitest.platform.system", return_value="Darwin"),
        patch.object(handler, "_get_toolchain_path", return_value="/usr/bin/xcodebuild"),
        patch.object(handler, "_check_xcode_license", return_value=True),
    ):
        assert handler.preflight_message() == ""


# ---------------------------------------------------------------------------
# Maestro (Android)
# ---------------------------------------------------------------------------


def test_maestro_preflight_no_cli(tmp_path: Path) -> None:
    handler = MaestroRunnerHandler(tmp_path)
    with patch.object(handler, "_check_maestro", return_value=False):
        msg = handler.preflight_message()
    assert "maestro CLI not on PATH" in msg
    assert "get.maestro.mobile.dev" in msg


def test_maestro_preflight_no_emulator(tmp_path: Path) -> None:
    handler = MaestroRunnerHandler(tmp_path)
    with (
        patch.object(handler, "_check_maestro", return_value=True),
        patch.object(handler, "_check_android_sdk", return_value=True),
        patch.object(handler, "_get_running_emulator", return_value=None),
    ):
        msg = handler.preflight_message()
    assert "no Android emulator available" in msg
    assert "emulator -avd" in msg


def test_maestro_preflight_ready(tmp_path: Path) -> None:
    handler = MaestroRunnerHandler(tmp_path)
    with (
        patch.object(handler, "_check_maestro", return_value=True),
        patch.object(handler, "_check_android_sdk", return_value=True),
        patch.object(handler, "_get_running_emulator", return_value="emulator-5554"),
    ):
        assert handler.preflight_message() == ""
