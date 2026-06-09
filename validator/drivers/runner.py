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
) -> CapabilityResult:
    """Execute a single capability and return a structured result.

    Args:
        driver: Driver manifest that owns the capability.
        capability: Capability name from ``CAPABILITY_NAMES``.
        project_root: Working directory used for command execution.
        env: Optional environment overrides merged onto ``os.environ``.
        timeout: Optional subprocess timeout in seconds.

    Returns:
        Structured subprocess result, including synthetic failures such as
        ``command not found`` and missing coverage artifacts.

    Raises:
        ValueError: ``capability`` is not a supported capability identifier.
        CapabilityNotImplementedError: The driver does not define the capability.
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
        # Run scripts through bash so driver manifests can rely on standard shell semantics.
        argv: list[str] = ["bash", str(script_path)]
    else:
        # The manifest validator guarantees one executable field is present, but mypy
        # cannot infer that contract across the Pydantic model boundary.
        assert cap.command is not None
        argv = shlex.split(cap.command)

    try:
        # Use list-form subprocess invocation with shell=False so driver commands do not
        # inherit shell interpolation beyond the manifest's explicit command tokenization.
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
        # Map a missing executable to 127 so callers get the conventional shell failure code.
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


# Feature 023: partial-driver capability loop.
# @spec FR-005: Run implemented capabilities, report None for the rest
# @spec AC-009: Skip non-implemented capabilities without raising
def run_all_capabilities(
    driver: DriverManifest,
    *,
    project_root: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
) -> dict[str, CapabilityResult | None]:
    """Run every capability the driver implements and skip the rest.

    Each capability slot in :data:`CAPABILITY_NAMES` is mapped to either the
    real :class:`CapabilityResult` produced by execution, or ``None`` when the
    driver does not declare that capability. Callers can render
    ``"not implemented for {driver}"`` for the ``None`` entries without having
    to handle :class:`CapabilityNotImplementedError` themselves.

    Args:
        driver: Driver manifest whose capabilities are exercised.
        project_root: Working directory used for command execution.
        env: Optional environment overrides merged onto ``os.environ``.
        timeout: Optional subprocess timeout in seconds.

    Returns:
        Mapping from capability name to result (``None`` if not implemented).
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
            )
        except CapabilityNotImplementedError:
            out[cap] = None
    return out
