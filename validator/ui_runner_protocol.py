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

__all__ = ["RunnerHandler", "UICapabilityResult"]


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
