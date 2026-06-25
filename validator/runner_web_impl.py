# LiveSpec traceability anchors
# @spec(FR-002)

"""Web UI runner support for Playwright-based projects.

This module provides a small adapter around the existing Feature 010 shell
commands so the validator can detect a Playwright project and invoke the
expected screenshot, flow, and baseline-comparison commands.
"""

# @spec Feature 028 mapping:
# - FR-001 / AC-001: manifest file at livespec/ui-runners/web.yaml
# - FR-002 / AC-003 / AC-004 / AC-005 / AC-006: handler methods below

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]  # PyYAML is a runtime dependency without stubs.

LEGACY_DESIGN_SCREENS_ENV = "LIVESPEC_LEGACY_DESIGN_SCREENS"

DEFAULT_COMPARE_THRESHOLD = 0.05
SCREENSHOT_TIMEOUT_SECONDS = 300
FLOW_TIMEOUT_SECONDS = 600
COMPARE_TIMEOUT_SECONDS = 60


@dataclass
class UICapabilityResult:
    """Describe the outcome of one UI runner capability invocation.

    Attributes:
        success: Whether the delegated command completed successfully.
        output_path: Output artifact path when one is expected and available.
        error: Human-readable failure detail when the capability fails.
        metadata: Structured subprocess metadata for higher-level reporting.
    """

    success: bool
    output_path: Path | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=lambda: cast(dict[str, Any], {}))


def _web_runner_manifest_path() -> Path:
    """Return the filesystem path to the built-in web runner manifest.

    Returns:
        Absolute path to `livespec/ui-runners/web.yaml`.
    """

    return Path(__file__).resolve().parent.parent / "livespec" / "ui-runners" / "web.yaml"


class WebRunnerHandler:
    """Handle UI runner capabilities for Playwright-based web projects."""

    def __init__(self, project_dir: Path | str) -> None:
        """Initialize the handler.

        Args:
            project_dir: Project root containing Playwright assets.
        """

        self.project_dir = Path(project_dir).resolve()

    def detect(self) -> bool:
        """Check whether the project looks like a Playwright web project.

        Returns:
            `True` when the project contains both `package.json` and a
            `playwright*.config.*` file, otherwise `False`.
        """

        has_package_json = (self.project_dir / "package.json").exists()
        # The runner contract requires both signals so generic Node projects do
        # not get misclassified as Playwright projects.
        has_playwright_config = any(self.project_dir.glob("playwright*.config.*"))
        return has_package_json and has_playwright_config

    # @spec(FR-011)
    def preflight_message(self) -> str:
        """Return an actionable diagnostic for the dispatcher BLOCKED line.

        Returns:
            Empty string when Playwright is wired up; otherwise the install
            hint surfaced through the Phase 4.5 dispatcher.
        """
        if not (self.project_dir / "package.json").exists():
            return (
                "@playwright/test not installed — npm install -D @playwright/test "
                "(no package.json found)"
            )
        if not any(self.project_dir.glob("playwright*.config.*")):
            return "@playwright/test not installed — npm install -D @playwright/test"
        return ""

    def capture_screenshot(
        self,
        screen: str,
        output_path: Path | None = None,
        feature_slug: str | None = None,
        run_id: str | None = None,
        legacy_design_screens: bool = False,
        **_unused: Any,
    ) -> UICapabilityResult:
        """Capture one tagged Playwright screenshot."""
        from validator import web_runner_core as core

        command = ["npx", "playwright", "test", "--grep", f"@capture-{screen}"]
        output_path, blocked = core.resolve_screenshot_output(
            self.project_dir,
            screen,
            output_path,
            feature_slug,
            run_id,
            legacy_design_screens,
            command,
        )
        if blocked is not None:
            return blocked
        assert output_path is not None
        blocked = core.guard_screenshot_output(output_path, command, legacy_design_screens)
        if blocked is not None:
            return blocked
        return core.run_screenshot_command(self.project_dir, command, output_path, screen)

    def run_flow(self) -> UICapabilityResult:
        """Run the default Playwright flow for the project."""
        from validator.web_runner_core import run_flow_command

        return run_flow_command(self.project_dir)

    def compare_baseline(
        self,
        baseline: str,
        screenshot: str,
        threshold: float = DEFAULT_COMPARE_THRESHOLD,
    ) -> UICapabilityResult:
        """Compare a screenshot against a baseline image."""
        from validator.web_runner_core import compare_pixel_baseline

        return compare_pixel_baseline(self.project_dir, baseline, screenshot, threshold)


def load_web_runner_manifest() -> dict[str, Any]:
    """Load the built-in web runner manifest from disk.

    Returns:
        Parsed YAML content for `livespec/ui-runners/web.yaml`.

    Raises:
        FileNotFoundError: If the built-in manifest cannot be found.
        yaml.YAMLError: If the manifest contents are not valid YAML.
    """

    manifest_path = _web_runner_manifest_path()
    if not manifest_path.exists():
        raise FileNotFoundError(f"Web runner manifest not found: {manifest_path}")

    with manifest_path.open() as manifest_file:
        manifest = yaml.safe_load(manifest_file)
    return cast(dict[str, Any], manifest)


def detect_web_runner(project_dir: Path | str) -> bool:
    """Detect whether a project should use the built-in web runner.

    Args:
        project_dir: Project root to inspect.

    Returns:
        `True` when the web runner should match the project, otherwise `False`.
    """

    return WebRunnerHandler(project_dir).detect()
