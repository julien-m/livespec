# LiveSpec traceability anchors
# @spec(FR-003)

"""Run driver capabilities as subprocesses."""

# @spec FR-003: Driver capabilities execute through one subprocess-based API.
# @spec AC-009: Command-backed capabilities capture stdout, stderr, and exit status.
# @spec AC-010: Script-backed capabilities run the referenced file instead of a command.
# @spec AC-011: Coverage capabilities fail when the declared report artifact is missing.

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

from .schemas import (
    CAPABILITY_NAMES,
    CapabilityNotImplementedError,
    CapabilityResult,
    DriverCapability,
    DriverManifest,
)


def _resolve_script(script: str, project_root: Path) -> Path:
    """Resolve a script path against the project root.

    Args:
        script: Script path declared in the manifest.
        project_root: Repository root that anchors relative script paths.

    Returns:
        Absolute or project-relative path to the script file.
    """
    script_path = Path(script)
    if not script_path.is_absolute():
        script_path = project_root / script_path
    return script_path


def run_capability(
    driver: DriverManifest,
    capability: str,
    *,
    project_root: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
    feature: str | None = None,
) -> CapabilityResult:
    """Execute a capability, retaining gaps when its result cannot certify acceptance.

    Args:
        driver: Driver manifest that owns the capability.
        capability: Capability name from ``CAPABILITY_NAMES``.
        project_root: Command working directory; defaults to the current directory.
        env: Overrides merged onto ``os.environ``; capture owns evidence variables.
        timeout: Subprocess limit in seconds; captured timeouts return exit 124.
        feature: Feature bound to receipt capture when a report adapter is declared.

    Returns:
        Process output, exit code and certification gaps; missing commands return 127.
        Captured runs include a receipt path; uncaptured runs cannot certify acceptance.

    Raises:
        ValueError: Invalid capability, command quoting, runner or capture publication.
        CapabilityNotImplementedError: The driver does not define the capability.
        FileNotFoundError: A script reference or capture root does not exist.
        OSError: Process launch or capture storage fails outside handled missing commands.
        subprocess.TimeoutExpired: An uncaptured command exceeds its timeout.

    Side effects:
        Runs the command; captured runs persist immutable evidence under .specs/.execution.
    """
    if capability not in CAPABILITY_NAMES:
        raise ValueError(f"Unknown capability: {capability!r}")

    cap = driver.get_capability(capability)
    if cap is None:
        raise CapabilityNotImplementedError(driver.name, capability)

    cwd = project_root or Path.cwd()
    proc_env = {**os.environ, **(env or {})}

    argv = _capability_argv(driver, capability, cap, cwd)
    if cap.report_adapter is not None and feature is not None:
        return _run_captured(cap, capability, argv, cwd, proc_env, timeout, feature)
    return _run_uncertified(cap, capability, argv, cwd, proc_env, timeout)


def _capability_argv(
    driver: DriverManifest, capability: str, cap: DriverCapability, cwd: Path
) -> list[str]:
    """Resolve the manifest executable while preserving script validation errors."""
    if cap.script is not None:
        script_path = _resolve_script(cap.script, cwd)
        if not script_path.exists():
            raise FileNotFoundError(
                f"Driver {driver.name!r} {capability} script not found: {script_path}"
            )
        # Scripts keep explicit shell semantics; commands remain list-form subprocesses.
        return ["bash", str(script_path)]
    assert cap.command is not None
    return shlex.split(cap.command)


def _run_captured(
    cap: DriverCapability,
    capability: str,
    argv: list[str],
    cwd: Path,
    proc_env: dict[str, str],
    timeout: float | None,
    feature: str,
) -> CapabilityResult:
    """Use runner-owned execution evidence for supported feature-scoped reports."""
    from validator.execution_capture import capture_execution
    from validator.execution_evidence import verify_execution_receipt

    assert cap.report_adapter is not None
    captured = capture_execution(
        argv,
        project_root=cwd,
        feature=feature,
        adapter=cap.report_adapter,
        env=proc_env,
        timeout=timeout,
        acceptance_mapping=cap.acceptance_mapping,
        required_report_path=cap.report_path if capability == "coverage" else None,
    )
    verified = verify_execution_receipt(Path(captured.receipt_path), cwd, feature)
    return CapabilityResult(
        capability_name=capability,
        exit_code=captured.exit_code,
        stdout=captured.stdout,
        stderr=captured.stderr,
        report_path=cap.report_path,
        execution_receipt_path=captured.receipt_path,
        certification_gaps=verified.gaps,
    )


def _run_uncertified(
    cap: DriverCapability,
    capability: str,
    argv: list[str],
    cwd: Path,
    proc_env: dict[str, str],
    timeout: float | None,
) -> CapabilityResult:
    """Keep legacy subprocess results and coverage-artifact failure semantics."""
    try:
        completed = subprocess.run(
            argv,
            cwd=str(cwd),
            env=proc_env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return CapabilityResult(
            capability_name=capability,
            exit_code=127,
            stdout="",
            stderr=f"command not found: {argv[0]}",
            report_path=cap.report_path,
        )
    result = CapabilityResult(
        capability_name=capability,
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        report_path=cap.report_path,
    )
    if capability == "coverage" and cap.report_path:
        report = _resolve_script(cap.report_path, cwd)
        if not report.exists():
            result.exit_code = result.exit_code or 1
            result.stderr = (result.stderr + f"\nMissing coverage report at {report}").strip()
            return result
    result.certification_gaps = [
        "Execution certification requires a supported report adapter and feature"
    ]
    return result


# Feature 023: partial-driver capability loop.
# @spec FR-005: Run implemented capabilities, report None for the rest
# @spec AC-009: Skip non-implemented capabilities without raising
def run_all_capabilities(
    driver: DriverManifest,
    *,
    project_root: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
    feature: str | None = None,
) -> dict[str, CapabilityResult | None]:
    """Run declared capabilities sequentially and skip undeclared slots.

    Args:
        driver: Driver manifest whose capabilities are exercised.
        project_root: Command working directory; defaults to the current directory.
        env: Environment overrides forwarded to each capability.
        timeout: Per-command subprocess limit in seconds.
        feature: Feature forwarded to adapter-backed receipt capture for each capability.

    Returns:
        Capability results with receipts and certification gaps, or None if undeclared.

    Raises:
        ValueError: A command, runner or capture publication is invalid.
        OSError: A script/root is missing, launch fails or capture storage fails.
        subprocess.TimeoutExpired: An uncaptured command exceeds its timeout.

    Side effects:
        Runs each command and persists adapter-backed execution evidence, as run_capability.
    """
    out: dict[str, CapabilityResult | None] = {}
    for cap in CAPABILITY_NAMES:
        try:
            out[cap] = run_capability(
                driver,
                cap,
                project_root=project_root,
                env=env,
                timeout=timeout,
                feature=feature,
            )
        except CapabilityNotImplementedError:
            out[cap] = None
    return out
