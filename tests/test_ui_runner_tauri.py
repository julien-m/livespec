"""Unit tests for validator/ui_runner_tauri.py.

# @spec FR-200/201: Tauri runner in-scope per Manager override — visual-gate-fix
"""

from __future__ import annotations

from pathlib import Path

import pytest

from validator.ui_runner_protocol import RuntimeOutputMisplacedError
from validator.ui_runner_tauri import (
    TAURI_APP_MARKER,
    TauriRunnerHandler,
    detect_tauri_runner,
)


def _seed_tauri_app(project_dir: Path) -> Path:
    marker = project_dir / TAURI_APP_MARKER
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text('[package]\nname = "demo"\n', encoding="utf-8")
    return marker


def test_detect_capability_returns_tauri_app_missing(tmp_path: Path) -> None:
    handler = TauriRunnerHandler(tmp_path)
    status = handler.detect_capability()
    assert status.state == "tauri_app_missing"
    assert handler.detect() is False
    assert "Tauri app" in handler.preflight_message()


def test_detect_capability_returns_tauri_driver_missing(tmp_path: Path) -> None:
    _seed_tauri_app(tmp_path)
    handler = TauriRunnerHandler(tmp_path)
    status = handler.detect_capability()
    # CI / dev hosts rarely have tauri-driver installed; the test pins the
    # diagnostic exactly so missing the binary surfaces as a structured
    # capability outcome rather than a crash.
    assert status.state in ("tauri_driver_missing", "available")
    if status.state == "tauri_driver_missing":
        assert status.driver_path is None
        assert "tauri-driver" in handler.preflight_message()


def test_capture_screenshot_blocks_runtime_under_design_screens(tmp_path: Path) -> None:
    _seed_tauri_app(tmp_path)
    handler = TauriRunnerHandler(tmp_path)
    target = tmp_path / ".specs" / "design" / "screens" / "dash.png"
    outcome = handler.capture_screenshot("dash", output_path=target)
    assert outcome.success is False
    assert outcome.metadata.get("guard") == "runtime_under_design_screens"


def test_capture_screenshot_returns_capability_unsupported_when_driver_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_tauri_app(tmp_path)
    monkeypatch.setattr("validator.ui_runner_tauri.shutil.which", lambda _bin: None)
    handler = TauriRunnerHandler(tmp_path)
    outcome = handler.capture_screenshot("dash", feature_slug="050-foo", run_id="20260523T000000Z")
    assert outcome.success is False
    assert outcome.metadata.get("capability_state") == "tauri_driver_missing"
    assert outcome.metadata.get("target") == "tauri"


def test_capture_screenshot_blocks_when_no_output_context_provided(
    tmp_path: Path,
) -> None:
    """C6 strict: silent default to .specs/_runs/tauri/ is forbidden."""
    _seed_tauri_app(tmp_path)
    handler = TauriRunnerHandler(tmp_path)
    outcome = handler.capture_screenshot("dash")
    assert outcome.success is False
    assert outcome.metadata.get("guard") == "missing_output_context"


def test_capture_screenshot_returns_capability_unsupported_when_no_capture_fn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No `_noop_capture_fn` in production — missing capture_fn → BLOCKED."""
    _seed_tauri_app(tmp_path)
    monkeypatch.setattr(
        "validator.ui_runner_tauri.shutil.which",
        lambda _bin: "/usr/local/bin/tauri-driver",
    )
    handler = TauriRunnerHandler(tmp_path)
    outcome = handler.capture_screenshot("dash", feature_slug="050-foo", run_id="20260523T000000Z")
    assert outcome.success is False
    assert outcome.metadata.get("capability_state") == "no_capture_implementation"


def test_capture_screenshot_invokes_injected_capture_fn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_tauri_app(tmp_path)
    monkeypatch.setattr(
        "validator.ui_runner_tauri.shutil.which",
        lambda _bin: "/usr/local/bin/tauri-driver",
    )
    calls: list[tuple[str, Path]] = []

    def fake_capture(screen: str, output_path: Path) -> bool:
        calls.append((screen, output_path))
        output_path.write_bytes(b"PNG")
        return True

    handler = TauriRunnerHandler(tmp_path, capture_fn=fake_capture)
    outcome = handler.capture_screenshot("home", feature_slug="050-foo", run_id="20260523T000000Z")
    assert outcome.success is True
    assert outcome.output_path is not None
    assert outcome.output_path.exists()
    assert calls and calls[0][0] == "home"
    # Canonical layout: .specs/features/050-foo/run/<ts>/tauri/home.png
    assert "/features/050-foo/run/" in str(outcome.output_path)
    assert outcome.output_path.parent.name == "tauri"


def test_module_level_detect_helper(tmp_path: Path) -> None:
    assert detect_tauri_runner(tmp_path) is False


def test_assert_output_not_in_design_screens_raises_for_misplaced_path() -> None:
    bad = Path(".specs/design/screens/foo/bar.png")
    with pytest.raises(RuntimeOutputMisplacedError):
        from validator.ui_runner_protocol import assert_output_not_in_design_screens

        assert_output_not_in_design_screens(bad)


def test_assert_output_not_in_design_screens_allows_runs_path() -> None:
    good = Path(".specs/features/foo/run/20260523T000000Z/web/dash.png")
    from validator.ui_runner_protocol import assert_output_not_in_design_screens

    # Must not raise.
    assert_output_not_in_design_screens(good)
