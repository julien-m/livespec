"""Run driver capabilities as subprocesses."""

# @spec FR-003: run_driver_capability function — .specs/features/016-cross-language-test-driver-architecture/spec.md#fr-003  # noqa: E501
# @spec AC-009: command field exec via subprocess — .specs/features/016-cross-language-test-driver-architecture/spec.md#ac-009  # noqa: E501
# @spec AC-010: script field exec — .specs/features/016-cross-language-test-driver-architecture/spec.md#ac-010  # noqa: E501
# @spec AC-011: coverage validates report path exists — .specs/features/016-cross-language-test-driver-architecture/spec.md#ac-011  # noqa: E501


from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

from .schemas import (
    CAPABILITY_NAMES,
    CapabilityNotImplementedError,
    CapabilityResult,
    DriverManifest,
)


def _resolve_script(script: str, project_root: Path) -> Path:
    p = Path(script)
    if not p.is_absolute():
        p = project_root / p
    return p


def run_capability(
    driver: DriverManifest,
    capability: str,
    *,
    project_root: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
) -> CapabilityResult:
    """Execute a single capability and return a structured result.

    Raises:
        CapabilityNotImplementedError: capability missing on the driver.
        FileNotFoundError: ``script:`` references a non-existent file.
    """
    if capability not in CAPABILITY_NAMES:
        raise ValueError(f"Unknown capability: {capability!r}")

    cap = driver.get_capability(capability)
    if cap is None:
        raise CapabilityNotImplementedError(driver.name, capability)

    cwd = project_root or Path.cwd()
    proc_env = {**os.environ, **(env or {})}

    if cap.script is not None:
        script_path = _resolve_script(cap.script, cwd)
        if not script_path.exists():
            raise FileNotFoundError(
                f"Driver {driver.name!r} {capability} script not found: {script_path}"
            )
        argv: list[str] = ["bash", str(script_path)]
    else:
        assert cap.command is not None  # enforced by schema validator
        argv = shlex.split(cap.command)

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
        exit_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except FileNotFoundError:
        # Binary not on PATH — surface as 127.
        return CapabilityResult(
            capability_name=capability,
            exit_code=127,
            stdout="",
            stderr=f"command not found: {argv[0]}",
            report_path=cap.report_path,
        )

    report_path = cap.report_path

    # AC-011: coverage capability must produce its declared report file.
    if capability == "coverage" and report_path:
        rp = Path(report_path)
        if not rp.is_absolute():
            rp = cwd / rp
        if not rp.exists():
            return CapabilityResult(
                capability_name=capability,
                exit_code=exit_code if exit_code != 0 else 1,
                stdout=stdout,
                stderr=(stderr + f"\nMissing coverage report at {rp}").strip(),
                report_path=report_path,
            )

    return CapabilityResult(
        capability_name=capability,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        report_path=report_path,
    )
