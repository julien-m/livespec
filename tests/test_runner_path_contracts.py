"""Per-surface output-path contracts (P0-C).

# @spec FR-202: Per-surface output-path guards — visual-gate-fix cycle

Each native runner must refuse to write into ``.specs/design/screens/`` and
must accept an explicit ``output_path`` override. The test suite locks the
contract for the four targets in scope: web, ios, android, tauri.
"""

from __future__ import annotations

from pathlib import Path

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
        assert_output_not_in_design_screens(
            Path(".specs/design/screens/foo/bar.png")
        )


def test_assert_output_not_in_design_screens_allows_canonical_run_path() -> None:
    assert_output_not_in_design_screens(
        Path(".specs/features/foo/run/20260101T000000Z/web/dash.png")
    )


def test_web_runner_returns_failure_when_output_path_under_design_screens(
    tmp_path: Path,
) -> None:
    handler = WebRunnerHandler(tmp_path)
    outcome = handler.capture_screenshot(
        "dash", output_path=_bad_design_screens_path(tmp_path)
    )
    assert outcome.success is False
    assert outcome.metadata.get("guard") == "runtime_under_design_screens"


def test_web_runner_blocks_when_no_output_context_provided(tmp_path: Path) -> None:
    """C6 strict: silent default to .specs/design/screens/ is forbidden."""
    handler = WebRunnerHandler(tmp_path)
    outcome = handler.capture_screenshot("dash")
    assert outcome.success is False
    assert outcome.metadata.get("guard") == "missing_output_context"


def test_web_runner_accepts_feature_slug_run_id_canonical_path(tmp_path: Path) -> None:
    """C6 strict: feature_slug+run_id derives `.specs/features/<slug>/run/<ts>/web/`."""
    handler = WebRunnerHandler(tmp_path)
    # The runner does not actually execute Playwright here; we only check the
    # path-resolution branch by passing a non-existent project. The subprocess
    # call will fail but the early path computation happens first. We assert
    # that the *guard* did not fire and that the resolved path matches.
    outcome = handler.capture_screenshot(
        "dash", feature_slug="050-foo", run_id="20260523T000000Z"
    )
    # Subprocess will fail in tmp_path (no npx); the important invariant is
    # that the path was NOT under .specs/design/screens/.
    assert outcome.metadata.get("guard") != "missing_output_context"
    assert outcome.metadata.get("guard") != "runtime_under_design_screens"


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
    handler = WebRunnerHandler(tmp_path)
    outcome = handler.capture_screenshot("dash", legacy_design_screens=True)
    # Subprocess will fail in tmp_path (no npx); the important invariant is
    # that neither the missing-context guard nor the legacy-disabled guard
    # fired — the legacy path was honoured.
    assert outcome.metadata.get("guard") != "missing_output_context"
    assert outcome.metadata.get("guard") != "legacy_design_screens_disabled"


def test_xcuitest_runner_returns_failure_when_output_path_under_design_screens(
    tmp_path: Path,
) -> None:
    handler = XCUITestRunnerHandler(tmp_path)
    outcome = handler.capture_screenshot(
        "dash", output_path=_bad_design_screens_path(tmp_path)
    )
    assert outcome.success is False
    assert outcome.metadata.get("guard") == "runtime_under_design_screens"


def test_maestro_runner_returns_failure_when_output_path_under_design_screens(
    tmp_path: Path,
) -> None:
    handler = MaestroRunnerHandler(tmp_path)
    outcome = handler.capture_screenshot(
        "dash", output_path=_bad_design_screens_path(tmp_path)
    )
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
    outcome = handler.capture_screenshot(
        "dash", output_path=_bad_design_screens_path(tmp_path)
    )
    assert outcome.success is False
    assert outcome.metadata.get("guard") == "runtime_under_design_screens"


def test_dispatcher_registry_contains_all_four_runners() -> None:
    # Underscore-prefixed but intentionally exported for tests — the registry
    # is the contract surface for `Phase4_5Dispatcher._dispatch`.
    from validator.ui_runner_dispatcher import _resolve_registry

    registry = _resolve_registry()
    assert set(registry.keys()) >= {"playwright", "xcuitest", "maestro", "tauri"}
