"""Focused XCUITest flow execution helpers."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any

from validator.ios_runner_core import (
    _license_result,
    _resolve_destination,
    _toolchain_blocker,
    _truncate_stdout,
)
from validator.ios_simulator_core import build_env, extract_failed_tests
from validator.runner_xcuitest_impl import FLOW_TIMEOUT_SECONDS, UICapabilityResult


def run_flow(
    handler: Any,
    destination: str | None,
    test_scheme: str | None,
    launch_arguments: list[str] | None,
    platform_name: str | None,
) -> UICapabilityResult:
    """Run the full XCUITest suite and report pass/fail."""
    blocked = _toolchain_blocker(handler)
    if blocked is not None:
        return blocked
    destination = _resolve_destination(handler, destination, platform_name)
    with tempfile.TemporaryDirectory() as tmp_dir:
        command = handler._build_xcodebuild_command(
            destination, test_scheme, Path(tmp_dir) / "flow_result.xcresult"
        )
        result = _run_flow_process(command, handler.project_dir, build_env(launch_arguments))
        if isinstance(result, UICapabilityResult):
            return result
        return _flow_result(command, result)


def _run_flow_process(
    command: list[str], project_dir: Path, env: dict[str, str] | None
) -> subprocess.CompletedProcess[str] | UICapabilityResult:
    """Run one xcodebuild flow command."""
    try:
        return subprocess.run(
            command,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=FLOW_TIMEOUT_SECONDS,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        return UICapabilityResult(
            success=False,
            error=f"XCUITest flow timed out after {error.timeout}s",
            metadata={"timeout": error.timeout, "command": " ".join(command)},
        )
    except OSError as error:
        return UICapabilityResult(
            success=False,
            error=f"Failed to execute xcodebuild: {error}",
            metadata={"command": " ".join(command)},
        )


def _flow_result(
    command: list[str], result: subprocess.CompletedProcess[str]
) -> UICapabilityResult:
    """Map xcodebuild flow output to a runner result."""
    license_error = _license_result(result, command)
    if license_error is not None:
        return license_error
    failed = extract_failed_tests(result.stdout + result.stderr)
    return UICapabilityResult(
        success=result.returncode == 0,
        error=_flow_error(result, failed),
        metadata={
            "command": " ".join(command),
            "exit_code": result.returncode,
            "failed_tests": failed,
            "stdout_snippet": _truncate_stdout(result.stdout),
        },
    )


def _flow_error(result: subprocess.CompletedProcess[str], failed_tests: list[str]) -> str | None:
    """Return flow error text for failed test output."""
    if failed_tests:
        return f"Tests failed: {', '.join(failed_tests)}"
    return result.stderr or None if result.returncode != 0 else None
