"""Uniform `RunnerHandler` Protocol consumed by the Phase 4.5 dispatcher.

This module declares the contract that every concrete UI runner handler must
satisfy so the Phase 4.5 dispatcher can route surfaces uniformly to the right
backend (Playwright web, XCUITest iOS/watchOS, Maestro Android).
"""

# @spec FR-002: Runner registry + uniform handler API — .specs/features/037-test-multi-runner-integration/spec.md#fr-002  # noqa: E501
# @spec FR-011: Dispatcher detect() preflight — .specs/features/037-test-multi-runner-integration/spec.md#fr-011  # noqa: E501

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from validator.ui_runner_web import UICapabilityResult

__all__ = [
    "RunnerHandler",
    "RuntimeOutputMisplacedError",
    "UICapabilityResult",
    "assert_output_not_in_design_screens",
]


class RuntimeOutputMisplacedError(RuntimeError):
    """Raised when a runner attempts to write a capture under
    ``.specs/design/screens/``.

    The design-screens tree is the *mockup registry*; storing a runtime
    capture there creates a circular comparison (the runtime artefact would
    later be promoted as its own baseline). Every native runner must call
    :func:`assert_output_not_in_design_screens` before persisting a PNG.
    """


def assert_output_not_in_design_screens(path: Path) -> None:
    """Raise :class:`RuntimeOutputMisplacedError` when ``path`` lives under
    ``.specs/design/screens/``.

    Accepts either absolute or relative paths; works on any host since it
    only inspects ``Path.parts``.
    """
    parts = path.parts
    try:
        specs_idx = parts.index(".specs")
    except ValueError:
        return
    tail = parts[specs_idx:]
    if len(tail) >= 3 and tail[1] == "design" and tail[2] == "screens":
        raise RuntimeOutputMisplacedError(
            f"Runtime capture attempted under .specs/design/screens/: {path}. "
            "Write to .specs/features/<slug>/run/<ts>/<target>/<screen>.png "
            "instead, then promote via `livespec visual-gate promote`."
        )


@runtime_checkable
class RunnerHandler(Protocol):
    """Uniform handler surface consumed by Phase 4.5 dispatcher.

    Every concrete handler MUST be constructible from a project directory and
    expose the methods below. The dispatcher relies on `detect()` for the
    preflight gate and `preflight_message()` to surface actionable error text
    when the gate fails.
    """

    project_dir: Path

    def detect(self) -> bool:
        """Return True when the handler can run on the current project/host."""
        ...

    def preflight_message(self) -> str:
        """Return an actionable diagnostic when `detect()` is False."""
        ...

    def capture_screenshot(self, screen: str, **kwargs: Any) -> UICapabilityResult:
        """Capture a single screenshot for the named screen.

        Concrete handlers accept additional runner-specific kwargs propagated
        from `surfaces.yaml` runnerConfig (e.g. `test_scheme`, `destination`
        for xcuitest; `avd_name`, `platform` for maestro).
        """
        ...

    def run_flow(self, **kwargs: Any) -> UICapabilityResult:
        """Run the handler's default end-to-end flow."""
        ...

    def compare_baseline(
        self,
        baseline: Path | str,
        screenshot: Path | str,
        threshold: float = 0.05,
    ) -> UICapabilityResult:
        """Compare a captured screenshot against a baseline image."""
        ...
