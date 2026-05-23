"""Web UI runner support for Playwright-based projects.

This module provides a small adapter around the existing Feature 010 shell
commands so the validator can detect a Playwright project and invoke the
expected screenshot, flow, and baseline-comparison commands.
"""

# @spec Feature 028 mapping:
# - FR-001 / AC-001: manifest file at livespec/ui-runners/web.yaml
# - FR-002 / AC-003 / AC-004 / AC-005 / AC-006: handler methods below

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

LEGACY_DESIGN_SCREENS_ENV = "LIVESPEC_LEGACY_DESIGN_SCREENS"

import yaml  # type: ignore[import-untyped]  # PyYAML is installed in the repo, but the stub package is not.

DEFAULT_COMPARE_THRESHOLD = 0.05
SCREENSHOT_TIMEOUT_SECONDS = 300
FLOW_TIMEOUT_SECONDS = 600
COMPARE_TIMEOUT_SECONDS = 60
STDOUT_SNIPPET_LIMIT = 200


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


def _truncate_stdout(stdout: str) -> str:
    """Return a bounded stdout preview for metadata payloads.

    Args:
        stdout: Full stdout emitted by the delegated command.

    Returns:
        At most the first 200 characters so result metadata stays compact.
    """

    # The metadata only needs a short preview because callers can still inspect
    # stderr and the exit code for failure details without storing full logs here.
    return stdout[:STDOUT_SNIPPET_LIMIT]


def _resolve_project_path(project_dir: Path, candidate: str) -> Path:
    """Resolve absolute or project-relative artifact paths.

    Args:
        project_dir: Project root used for relative paths.
        candidate: User- or manifest-provided path string.

    Returns:
        An absolute filesystem path.
    """

    candidate_path = Path(candidate)
    if candidate_path.is_absolute():
        return candidate_path
    return project_dir / candidate_path


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

    # @spec FR-011: Playwright preflight diagnostic — .specs/features/037-test-multi-runner-integration/spec.md#fr-011  # noqa: E501
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
            return (
                "@playwright/test not installed — npm install -D @playwright/test"
            )
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
        """Capture one tagged Playwright screenshot.

        Output path resolution (C6 strict — visual-gate-fix cycle):
        * ``output_path`` provided → guard runs; design-screens forbidden.
        * ``output_path`` omitted but ``feature_slug`` + ``run_id`` provided →
          canonical path
          ``.specs/features/<slug>/run/<run_id>/web/<screen>.png`` is used.
        * ``legacy_design_screens=True`` → explicit opt-in to the legacy
          ``.specs/design/screens/<screen>.png`` path. No silent default.
        * Otherwise → return a BLOCKED ``UICapabilityResult`` with
          ``guard='missing_output_context'`` so the caller surfaces the
          contract violation instead of writing into design/screens.

        Args:
            screen: Screen identifier matched against `@capture-<screen>` tags.
            output_path: Optional explicit destination PNG path.
            feature_slug: Feature slug used to derive the canonical run path.
            run_id: Timestamp folder name under the feature's ``run/`` dir.
            legacy_design_screens: Opt-in switch for the pre-visual-gate
                ``.specs/design/screens/`` layout. Never the default.

        Returns:
            Result object containing the expected screenshot path on success
            or the explicit ``guard`` diagnostic on contract failure.
        """

        # Local import keeps the protocol module from importing the web runner
        # at module load (web runner already imports its own deps lazily).
        from validator.ui_runner_protocol import (
            RuntimeOutputMisplacedError,
            assert_output_not_in_design_screens,
        )

        command = ["npx", "playwright", "test", "--grep", f"@capture-{screen}"]
        if output_path is None:
            if feature_slug and run_id:
                output_path = (
                    self.project_dir
                    / ".specs"
                    / "features"
                    / feature_slug
                    / "run"
                    / run_id
                    / "web"
                    / f"{screen}.png"
                )
            elif legacy_design_screens:
                # Legacy opt-in — only honoured when the explicit env var is
                # set so production callers cannot accidentally re-enable
                # the forbidden mockup-registry write path. Used exclusively
                # by cleanup/migration tooling on pre-visual-gate apps.
                if os.environ.get(LEGACY_DESIGN_SCREENS_ENV) != "1":
                    return UICapabilityResult(
                        success=False,
                        error=(
                            "legacy_design_screens=True is forbidden in normal "
                            "execution. Set "
                            f"{LEGACY_DESIGN_SCREENS_ENV}=1 explicitly to "
                            "authorise the legacy .specs/design/screens/ "
                            "destination (cleanup/migration tooling only)."
                        ),
                        metadata={
                            "command": " ".join(command),
                            "guard": "legacy_design_screens_disabled",
                        },
                    )
                output_path = (
                    self.project_dir / ".specs" / "design" / "screens" / f"{screen}.png"
                )
            else:
                return UICapabilityResult(
                    success=False,
                    error=(
                        "Web runner refuses to write into "
                        ".specs/design/screens/ by default (C6 strict). "
                        "Provide --output_path, feature_slug+run_id, or "
                        "legacy_design_screens=True explicitly."
                    ),
                    metadata={
                        "command": " ".join(command),
                        "guard": "missing_output_context",
                    },
                )
        if not legacy_design_screens:
            try:
                assert_output_not_in_design_screens(output_path)
            except RuntimeOutputMisplacedError as exc:
                return UICapabilityResult(
                    success=False,
                    error=str(exc),
                    metadata={
                        "command": " ".join(command),
                        "guard": "runtime_under_design_screens",
                    },
                )
        # Thread the resolved output_path through to Playwright so the test
        # can write the PNG into the canonical location instead of relying on
        # a hardcoded .specs/design/screens path. The test harness reads
        # `LIVESPEC_SCREENSHOT_PATH` (and the per-screen variant) from env.
        playwright_env = os.environ.copy()
        playwright_env["LIVESPEC_SCREENSHOT_PATH"] = str(output_path)
        playwright_env[f"LIVESPEC_SCREENSHOT_PATH_{screen.upper()}"] = str(output_path)
        # Ensure the destination directory exists so Playwright can write
        # directly into it without a "file not found" intermediate failure.
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            # This subprocess contract mirrors Feature 010: exit code 0 means the
            # tagged Playwright test ran successfully and the PNG must be at
            # the path Playwright was instructed to write via the env vars
            # above. If the test ignores those env vars, the result.output_path
            # may still be missing — callers must check `output_path.exists()`.
            result = subprocess.run(
                command,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=SCREENSHOT_TIMEOUT_SECONDS,
                check=False,
                env=playwright_env,
            )
        except subprocess.TimeoutExpired as error:
            return UICapabilityResult(
                success=False,
                error=(
                    "Playwright screenshot timed out after "
                    f"{error.timeout}s for screen={screen}"
                ),
                metadata={"timeout": error.timeout, "command": " ".join(command)},
            )
        except OSError as error:
            return UICapabilityResult(
                success=False,
                error=f"Failed to execute Playwright screenshot command: {error}",
                metadata={"command": " ".join(command)},
            )

        success = result.returncode == 0
        # Anti-false-positive: Playwright exit 0 alone is not enough — if the
        # PNG was not written at `output_path` we MUST refuse success so the
        # gate cannot silently PASS on a runner that ignored the env vars.
        if success and not output_path.exists():
            return UICapabilityResult(
                success=False,
                error=(
                    f"Playwright reported success but no PNG was written at "
                    f"{output_path}. Check that the test honours "
                    "LIVESPEC_SCREENSHOT_PATH (or per-screen variant)."
                ),
                metadata={
                    "command": " ".join(command),
                    "exit_code": result.returncode,
                    "guard": "output_missing",
                    "expected_output_path": str(output_path),
                    "stdout_snippet": _truncate_stdout(result.stdout),
                },
            )
        return UICapabilityResult(
            success=success,
            output_path=output_path if success else None,
            error=result.stderr or None if not success else None,
            metadata={
                "command": " ".join(command),
                "exit_code": result.returncode,
                "stdout_snippet": _truncate_stdout(result.stdout),
            },
        )

    def run_flow(self) -> UICapabilityResult:
        """Run the default Playwright flow for the project.

        Returns:
            Result object containing the Playwright report directory when present.
        """

        command = ["npx", "playwright", "test"]
        report_path = self.project_dir / "playwright-report"
        try:
            # The full flow uses the default Playwright entrypoint, so callers can
            # preserve existing downstream project behavior without new scripts.
            result = subprocess.run(
                command,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=FLOW_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            return UICapabilityResult(
                success=False,
                error=f"Playwright test flow timed out after {error.timeout}s",
                metadata={"timeout": error.timeout, "command": " ".join(command)},
            )
        except OSError as error:
            return UICapabilityResult(
                success=False,
                error=f"Failed to execute Playwright flow command: {error}",
                metadata={"command": " ".join(command)},
            )

        success = result.returncode == 0
        return UICapabilityResult(
            success=success,
            output_path=report_path if report_path.exists() else None,
            error=result.stderr or None if not success else None,
            metadata={
                "command": " ".join(command),
                "exit_code": result.returncode,
                "report_exists": report_path.exists(),
                "stdout_snippet": _truncate_stdout(result.stdout),
            },
        )

    def compare_baseline(
        self,
        baseline: str,
        screenshot: str,
        threshold: float = DEFAULT_COMPARE_THRESHOLD,
    ) -> UICapabilityResult:
        """Compare a screenshot against a baseline image.

        Args:
            baseline: Baseline PNG path, absolute or project-relative.
            screenshot: Screenshot PNG path, absolute or project-relative.
            threshold: Pixel diff tolerance used by the Feature 010 script.

        Returns:
            Result object containing the diff path when the script creates one.
        """

        script_path = self.project_dir / "scripts" / "pixelmatch-cli.js"
        if not script_path.exists():
            return UICapabilityResult(
                success=False,
                error=f"Feature 010 pixelmatch script not found: {script_path}",
                metadata={"script_path": str(script_path)},
            )

        baseline_path = _resolve_project_path(self.project_dir, baseline)
        screenshot_path = _resolve_project_path(self.project_dir, screenshot)

        if not baseline_path.exists():
            return UICapabilityResult(
                success=False,
                error=f"Baseline PNG not found: {baseline_path}",
                metadata={"baseline_path": str(baseline_path)},
            )

        if not screenshot_path.exists():
            return UICapabilityResult(
                success=False,
                error=f"Screenshot PNG not found: {screenshot_path}",
                metadata={"screenshot_path": str(screenshot_path)},
            )

        # Feature 010 established 0.05 as the visual diff default, so the runner
        # keeps the same threshold to preserve existing comparison behavior.
        command = [
            "node",
            str(script_path),
            str(baseline_path),
            str(screenshot_path),
            str(threshold),
        ]
        try:
            # The pixelmatch helper uses exit code 0 for pass, 1 for visual diff,
            # and values above 1 for execution failures such as bad input.
            result = subprocess.run(
                command,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=COMPARE_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            return UICapabilityResult(
                success=False,
                error=f"Pixelmatch comparison timed out after {error.timeout}s",
                metadata={"timeout": error.timeout, "command": " ".join(command)},
            )
        except OSError as error:
            return UICapabilityResult(
                success=False,
                error=f"Failed to execute pixelmatch comparison command: {error}",
                metadata={"command": " ".join(command)},
            )

        diff_path = self.project_dir / f"{baseline_path.stem}.diff.png"
        return UICapabilityResult(
            success=result.returncode == 0,
            output_path=diff_path if diff_path.exists() else None,
            error=result.stderr or None if result.returncode > 1 else None,
            metadata={
                "command": " ".join(command),
                "exit_code": result.returncode,
                "threshold": threshold,
                "baseline": str(baseline_path),
                "screenshot": str(screenshot_path),
                "diff_produced": diff_path.exists(),
                "stdout_snippet": _truncate_stdout(result.stdout),
            },
        )


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
