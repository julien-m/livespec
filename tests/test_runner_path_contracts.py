"""Per-surface output-path contracts (P0-C).

# @spec FR-202: Per-surface output-path guards — visual-gate-fix cycle

Each native runner must refuse to write into ``.specs/design/screens/`` and
must accept an explicit ``output_path`` override. The test suite locks the
contract for the four targets in scope: web, ios, android, tauri.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from validator.ui_runner_maestro import MaestroRunnerHandler
from validator.ui_runner_protocol import (
    RuntimeOutputMisplacedError,
    assert_output_not_in_design_screens,
)
from validator.ui_runner_tauri import TAURI_APP_MARKER, TauriRunnerHandler
from validator.ui_runner_web import WebRunnerHandler
from validator.ui_runner_xcuitest import XCUITestRunnerHandler


def _bad_design_screens_path(tmp_path: Path) -> Path:
    return tmp_path / ".specs" / "design" / "screens" / "dash.png"


def test_assert_output_not_in_design_screens_raises_for_relative_path() -> None:
    with pytest.raises(RuntimeOutputMisplacedError):
        assert_output_not_in_design_screens(Path(".specs/design/screens/foo/bar.png"))


def test_assert_output_not_in_design_screens_allows_canonical_run_path() -> None:
    assert_output_not_in_design_screens(
        Path(".specs/features/foo/run/20260101T000000Z/web/dash.png")
    )


def test_web_runner_returns_failure_when_output_path_under_design_screens(
    tmp_path: Path,
) -> None:
    handler = WebRunnerHandler(tmp_path)
    outcome = handler.capture_screenshot("dash", output_path=_bad_design_screens_path(tmp_path))
    assert outcome.success is False
    assert outcome.metadata.get("guard") == "runtime_under_design_screens"


def test_web_runner_blocks_when_no_output_context_provided(tmp_path: Path) -> None:
    """C6 strict: silent default to .specs/design/screens/ is forbidden."""
    handler = WebRunnerHandler(tmp_path)
    outcome = handler.capture_screenshot("dash")
    assert outcome.success is False
    assert outcome.metadata.get("guard") == "missing_output_context"


def _fake_playwright(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Replace the Playwright subprocess: record the call and write the requested PNG."""
    calls: list[dict[str, Any]] = []

    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        target = Path(kwargs["env"]["LIVESPEC_SCREENSHOT_PATH"])
        target.write_bytes(b"\x89PNG")
        calls.append({"command": command, **kwargs})
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    monkeypatch.setattr("validator.web_runner_core.subprocess.run", run)
    return calls


def test_web_runner_accepts_feature_slug_run_id_canonical_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C6 strict: feature_slug+run_id derives `.specs/features/<slug>/run/<ts>/web/`."""
    calls = _fake_playwright(monkeypatch)
    expected = tmp_path / ".specs/features/050-foo/run/20260523T000000Z/web/dash.png"

    outcome = WebRunnerHandler(tmp_path).capture_screenshot(
        "dash", feature_slug="050-foo", run_id="20260523T000000Z"
    )

    assert outcome.success is True
    assert outcome.output_path == expected
    assert calls[0]["command"] == ["npx", "playwright", "test", "--grep", "@capture-dash"]
    assert calls[0]["cwd"] == tmp_path
    assert calls[0]["env"]["LIVESPEC_SCREENSHOT_PATH_DASH"] == str(expected)


def test_web_runner_legacy_design_screens_disabled_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C6 strict: legacy_design_screens=True alone is rejected without env opt-in."""
    monkeypatch.delenv("LIVESPEC_LEGACY_DESIGN_SCREENS", raising=False)
    handler = WebRunnerHandler(tmp_path)
    outcome = handler.capture_screenshot("dash", legacy_design_screens=True)
    assert outcome.success is False
    assert outcome.metadata.get("guard") == "legacy_design_screens_disabled"


def test_web_runner_legacy_design_screens_opt_in_requires_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C6 strict: legacy_design_screens=True only honoured with explicit env var."""
    monkeypatch.setenv("LIVESPEC_LEGACY_DESIGN_SCREENS", "1")
    calls = _fake_playwright(monkeypatch)

    outcome = WebRunnerHandler(tmp_path).capture_screenshot("dash", legacy_design_screens=True)

    assert outcome.success is True
    assert outcome.output_path == tmp_path / ".specs/design/screens/dash.png"
    assert len(calls) == 1


def test_xcuitest_runner_returns_failure_when_output_path_under_design_screens(
    tmp_path: Path,
) -> None:
    handler = XCUITestRunnerHandler(tmp_path)
    outcome = handler.capture_screenshot("dash", output_path=_bad_design_screens_path(tmp_path))
    assert outcome.success is False
    assert outcome.metadata.get("guard") == "runtime_under_design_screens"


def test_maestro_runner_returns_failure_when_output_path_under_design_screens(
    tmp_path: Path,
) -> None:
    handler = MaestroRunnerHandler(tmp_path)
    outcome = handler.capture_screenshot("dash", output_path=_bad_design_screens_path(tmp_path))
    assert outcome.success is False
    assert outcome.metadata.get("guard") == "runtime_under_design_screens"


def test_tauri_runner_returns_failure_when_output_path_under_design_screens(
    tmp_path: Path,
) -> None:
    # Tauri marker still required so we exercise the runner path, not the
    # capability-missing branch.
    marker = tmp_path / TAURI_APP_MARKER
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text('[package]\nname = "demo"\n', encoding="utf-8")
    handler = TauriRunnerHandler(tmp_path)
    outcome = handler.capture_screenshot("dash", output_path=_bad_design_screens_path(tmp_path))
    assert outcome.success is False
    assert outcome.metadata.get("guard") == "runtime_under_design_screens"


def test_dispatcher_registry_contains_all_four_runners() -> None:
    # Underscore-prefixed but intentionally exported for tests — the registry
    # is the contract surface for `Phase4_5Dispatcher._dispatch`.
    from validator.ui_runner_dispatcher import _resolve_registry

    registry = _resolve_registry()
    assert set(registry.keys()) >= {"playwright", "xcuitest", "maestro", "tauri"}
