"""Focused helpers for Playwright UI runner execution."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from validator.runner_web_impl import (
    COMPARE_TIMEOUT_SECONDS,
    FLOW_TIMEOUT_SECONDS,
    LEGACY_DESIGN_SCREENS_ENV,
    SCREENSHOT_TIMEOUT_SECONDS,
    UICapabilityResult,
)

STDOUT_SNIPPET_LIMIT = 200


def _truncate_stdout(stdout: str) -> str:
    """Return a bounded stdout preview for metadata payloads."""
    return stdout[:STDOUT_SNIPPET_LIMIT]


def _resolve_project_path(project_dir: Path, candidate: str) -> Path:
    """Resolve absolute or project-relative artifact paths."""
    candidate_path = Path(candidate)
    return candidate_path if candidate_path.is_absolute() else project_dir / candidate_path


def resolve_screenshot_output(
    project_dir: Path,
    screen: str,
    output_path: Path | None,
    feature_slug: str | None,
    run_id: str | None,
    legacy_design_screens: bool,
    command: list[str],
) -> tuple[Path | None, UICapabilityResult | None]:
    """Resolve the Playwright screenshot destination or return a guard result."""
    if output_path is not None:
        return output_path, None
    if feature_slug and run_id:
        return _canonical_screenshot_output(project_dir, screen, feature_slug, run_id), None
    if legacy_design_screens:
        return _legacy_design_output(project_dir, screen, command)
    return None, _missing_screenshot_context_result(command)


def _canonical_screenshot_output(
    project_dir: Path, screen: str, feature_slug: str, run_id: str
) -> Path:
    """Return the canonical feature run screenshot path."""
    return (
        project_dir
        / ".specs"
        / "features"
        / feature_slug
        / "run"
        / run_id
        / "web"
        / f"{screen}.png"
    )


def _missing_screenshot_context_result(command: list[str]) -> UICapabilityResult:
    """Return the C6 strict missing-output guard result."""
    return UICapabilityResult(
        success=False,
        error=(
            "Web runner refuses to write into .specs/design/screens/ by default "
            "(C6 strict). Provide --output_path, feature_slug+run_id, or "
            "legacy_design_screens=True explicitly."
        ),
        metadata={"command": " ".join(command), "guard": "missing_output_context"},
    )


def _legacy_design_output(
    project_dir: Path,
    screen: str,
    command: list[str],
) -> tuple[Path | None, UICapabilityResult | None]:
    """Resolve the explicitly authorized legacy design-screens output path."""
    if os.environ.get(LEGACY_DESIGN_SCREENS_ENV) != "1":
        return None, UICapabilityResult(
            success=False,
            error=(
                "legacy_design_screens=True is forbidden in normal execution. "
                f"Set {LEGACY_DESIGN_SCREENS_ENV}=1 explicitly to authorise the "
                "legacy .specs/design/screens/ destination (cleanup/migration tooling only)."
            ),
            metadata={"command": " ".join(command), "guard": "legacy_design_screens_disabled"},
        )
    return project_dir / ".specs" / "design" / "screens" / f"{screen}.png", None


def guard_screenshot_output(
    output_path: Path,
    command: list[str],
    legacy_design_screens: bool,
) -> UICapabilityResult | None:
    """Reject runtime screenshots that would be written into design screens."""
    if legacy_design_screens:
        return None
    from validator.ui_runner_protocol import (
        RuntimeOutputMisplacedError,
        assert_output_not_in_design_screens,
    )

    try:
        assert_output_not_in_design_screens(output_path)
    except RuntimeOutputMisplacedError as exc:
        return UICapabilityResult(
            success=False,
            error=str(exc),
            metadata={"command": " ".join(command), "guard": "runtime_under_design_screens"},
        )
    return None


def run_screenshot_command(
    project_dir: Path, command: list[str], output_path: Path, screen: str
) -> UICapabilityResult:
    """Run Playwright and verify it created the expected screenshot file."""
    playwright_env = _playwright_screenshot_env(output_path, screen)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            command,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=SCREENSHOT_TIMEOUT_SECONDS,
            check=False,
            env=playwright_env,
        )
    except subprocess.TimeoutExpired as error:
        return UICapabilityResult(
            success=False,
            error=f"Playwright screenshot timed out after {error.timeout}s for screen={screen}",
            metadata={"timeout": error.timeout, "command": " ".join(command)},
        )
    except OSError as error:
        return UICapabilityResult(
            success=False,
            error=f"Failed to execute Playwright screenshot command: {error}",
            metadata={"command": " ".join(command)},
        )
    return _screenshot_result(command, output_path, result)


def _playwright_screenshot_env(output_path: Path, screen: str) -> dict[str, str]:
    """Return Playwright env with the screenshot path variables."""
    playwright_env = os.environ.copy()
    playwright_env["LIVESPEC_SCREENSHOT_PATH"] = str(output_path)
    playwright_env[f"LIVESPEC_SCREENSHOT_PATH_{screen.upper()}"] = str(output_path)
    return playwright_env


def _screenshot_result(
    command: list[str],
    output_path: Path,
    result: subprocess.CompletedProcess[str],
) -> UICapabilityResult:
    """Map a Playwright screenshot subprocess result to a runner result."""
    success = result.returncode == 0
    if success and not output_path.exists():
        return _missing_screenshot_result(command, output_path, result)
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


def _missing_screenshot_result(
    command: list[str],
    output_path: Path,
    result: subprocess.CompletedProcess[str],
) -> UICapabilityResult:
    """Return the anti-false-positive result for missing PNG output."""
    return UICapabilityResult(
        success=False,
        error=(
            f"Playwright reported success but no PNG was written at {output_path}. "
            "Check that the test honours LIVESPEC_SCREENSHOT_PATH."
        ),
        metadata={
            "command": " ".join(command),
            "exit_code": result.returncode,
            "guard": "output_missing",
            "expected_output_path": str(output_path),
            "stdout_snippet": _truncate_stdout(result.stdout),
        },
    )


def run_flow_command(project_dir: Path) -> UICapabilityResult:
    """Run the default Playwright test command and map its output."""
    command = ["npx", "playwright", "test"]
    report_path = project_dir / "playwright-report"
    result = _run_flow_process(project_dir, command)
    if isinstance(result, UICapabilityResult):
        return result
    return _flow_result(command, report_path, result)


def _run_flow_process(
    project_dir: Path,
    command: list[str],
) -> subprocess.CompletedProcess[str] | UICapabilityResult:
    """Run the Playwright flow subprocess."""
    try:
        return subprocess.run(
            command,
            cwd=project_dir,
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


def _flow_result(
    command: list[str],
    report_path: Path,
    result: subprocess.CompletedProcess[str],
) -> UICapabilityResult:
    """Map Playwright flow output to a runner result."""
    return UICapabilityResult(
        success=result.returncode == 0,
        output_path=report_path if report_path.exists() else None,
        error=result.stderr or None if result.returncode != 0 else None,
        metadata={
            "command": " ".join(command),
            "exit_code": result.returncode,
            "report_exists": report_path.exists(),
            "stdout_snippet": _truncate_stdout(result.stdout),
        },
    )


def compare_pixel_baseline(
    project_dir: Path,
    baseline: str,
    screenshot: str,
    threshold: float,
) -> UICapabilityResult:
    """Compare two PNGs with the project pixelmatch helper."""
    script_path = project_dir / "scripts" / "pixelmatch-cli.js"
    if not script_path.exists():
        return UICapabilityResult(
            success=False,
            error=f"Feature 010 pixelmatch script not found: {script_path}",
            metadata={"script_path": str(script_path)},
        )
    baseline_path = _resolve_project_path(project_dir, baseline)
    screenshot_path = _resolve_project_path(project_dir, screenshot)
    missing = _missing_input_result(baseline_path, screenshot_path)
    if missing is not None:
        return missing
    return _run_pixelmatch(project_dir, script_path, baseline_path, screenshot_path, threshold)


def _missing_input_result(baseline_path: Path, screenshot_path: Path) -> UICapabilityResult | None:
    """Return a structured missing-input result when either PNG is absent."""
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
    return None


def _run_pixelmatch(
    project_dir: Path,
    script_path: Path,
    baseline_path: Path,
    screenshot_path: Path,
    threshold: float,
) -> UICapabilityResult:
    """Run pixelmatch and map its exit code into runner metadata."""
    command = ["node", str(script_path), str(baseline_path), str(screenshot_path), str(threshold)]
    result = _run_pixelmatch_process(project_dir, command)
    if isinstance(result, UICapabilityResult):
        return result
    diff_path = project_dir / f"{baseline_path.stem}.diff.png"
    return _pixelmatch_result(command, baseline_path, screenshot_path, threshold, diff_path, result)


def _run_pixelmatch_process(
    project_dir: Path,
    command: list[str],
) -> subprocess.CompletedProcess[str] | UICapabilityResult:
    """Run the pixelmatch subprocess."""
    try:
        return subprocess.run(
            command,
            cwd=project_dir,
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


def _pixelmatch_result(
    command: list[str],
    baseline_path: Path,
    screenshot_path: Path,
    threshold: float,
    diff_path: Path,
    result: subprocess.CompletedProcess[str],
) -> UICapabilityResult:
    """Map pixelmatch output to a runner result."""
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
