"""Registry handlers honour the uniform ``RunnerHandler`` protocol (037 FR-002).

The registry used to ``cast`` each handler class to ``type[RunnerHandler]``,
hiding that Web/XCUITest/Maestro ``run_flow`` rejected the protocol's keyword
arguments. Calls below go through the registry exactly as the dispatcher does.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from validator.runner_dispatcher_impl import _resolve_registry
from validator.ui_runner_web import UICapabilityResult

_PROTOCOL_KWARGS: dict[str, Any] = {
    "screen": "main",
    "output_path": None,
    "feature_slug": "001-demo",
    "run_id": "20261012T000000Z",
}

_FLOW_CORES = {
    "playwright": ("validator.web_runner_core.run_flow_command", lambda project_dir: None),
    "xcuitest": ("validator.ios_runner_core.run_flow", lambda *args: None),
    "maestro": ("validator.android_runner_core.run_flow", lambda *args: None),
}


@pytest.mark.parametrize("runner", sorted(_FLOW_CORES))
def test_registry_run_flow_accepts_protocol_keywords(
    runner: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target, _ = _FLOW_CORES[runner]
    observed = UICapabilityResult(success=True)
    monkeypatch.setattr(target, lambda *args, **kwargs: observed)
    handler = _resolve_registry()[runner](tmp_path)

    try:
        result: object = handler.run_flow(**_PROTOCOL_KWARGS)
    except TypeError as exc:  # the pre-fix signatures rejected protocol keywords
        result = exc
    assert result is observed


@pytest.mark.parametrize("runner", ["playwright", "xcuitest", "maestro", "tauri"])
def test_registry_compare_baseline_accepts_paths(
    runner: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[tuple[str, str]] = []

    def fake_compare(project_dir: Path, baseline: str, screenshot: str, threshold: float) -> Any:
        seen.append((baseline, screenshot))
        return UICapabilityResult(success=True)

    monkeypatch.setattr("validator.web_runner_core.compare_pixel_baseline", fake_compare)
    handler = _resolve_registry()[runner](tmp_path)

    result = handler.compare_baseline(tmp_path / "base.png", tmp_path / "shot.png")

    if runner == "tauri":  # tauri compares bytes itself; missing inputs fail cleanly
        assert result.success is False
    else:
        assert result.success is True
        assert [(Path(b), Path(s)) for b, s in seen] == [
            (tmp_path / "base.png", tmp_path / "shot.png")
        ]
