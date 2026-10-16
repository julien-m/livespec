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
from collections.abc import Sequence
from pathlib import Path

from ..exceptions import DriverTestSelectionError
from ..execution_deadline import BudgetExpired, command_scope, run_owned
from .placeholders import resolve_argv_placeholders
from .preconditions import capability_skip_message
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
    test_paths: Sequence[str] | None = None,
) -> CapabilityResult:
    """Run a capability within one bounded preparation/execution lifecycle.

    Report adapter and feature enable captured execution; otherwise results remain
    uncertified. Existing timeout arguments may only tighten the declared budget.
    Test selection requires the capability's explicit append support.
    """
    cwd = project_root or Path.cwd()
    cap = driver.get_capability(capability)
    identity = (
        _capability_argv(driver, capability, cap, cwd)
        if cap is not None
        else ["livespec", "capability", capability]
    )
    if test_paths is not None and cap is not None:
        identity = _append_test_paths(driver, capability, cap, identity, test_paths)
    with command_scope(cwd, identity, timeout):
        return _run_capability(
            driver,
            capability,
            project_root=project_root,
            env=env,
            timeout=timeout,
            feature=feature,
            test_paths=test_paths,
        )


def _run_capability(
    driver: DriverManifest,
    capability: str,
    *,
    project_root: Path | None,
    env: dict[str, str] | None,
    timeout: float | None,
    feature: str | None,
    test_paths: Sequence[str] | None,
) -> CapabilityResult:
    """Resolve one capability within the already active preparation envelope."""
    if capability not in CAPABILITY_NAMES:
        raise ValueError(f"Unknown capability: {capability!r}")

    cap = driver.get_capability(capability)
    if cap is None:
        raise CapabilityNotImplementedError(driver.name, capability)

    cwd = project_root or Path.cwd()
    skip = capability_skip_message(driver, capability, cwd)
    if skip is not None:
        return _skipped_result(capability, cap, skip)
    proc_env = {**os.environ, **(env or {})}

    argv = _capability_argv(driver, capability, cap, cwd)
    if test_paths is not None:
        argv = _append_test_paths(driver, capability, cap, argv, test_paths)
    with command_scope(cwd, argv, timeout) as scope:
        try:
            if cap.report_adapter is not None and feature is not None:
                result = _run_captured(cap, capability, argv, cwd, proc_env, timeout, feature)
            else:
                result = _run_uncertified(cap, capability, argv, cwd, proc_env, timeout)
        except BudgetExpired:
            scope.timed_out = True
            result = CapabilityResult(
                capability_name=capability,
                exit_code=124,
                stderr="TIMEOUT during capability preparation",
            )
        result.budget = result.budget or scope.evidence()
        if scope.timed_out:
            result.exit_code = 124
            result.certification_gaps.append("Execution timed out; cannot certify acceptance")
        return result


def _skipped_result(capability: str, cap: DriverCapability, skip: str) -> CapabilityResult:
    """Report a skipped capability as an uncertified success.

    A missing optional library is "not configured", not a failure (018 AC-008/AC-009).
    """
    return CapabilityResult(
        capability_name=capability,
        exit_code=0,
        stdout=skip,
        report_path=cap.report_path,
        certification_gaps=[f"Capability skipped: {skip}"],
    )


def _append_test_paths(
    driver: DriverManifest,
    capability: str,
    cap: DriverCapability,
    argv: list[str],
    test_paths: Sequence[str],
) -> list[str]:
    """Append selected test files when the capability opts in to test selection.

    Raises:
        DriverTestSelectionError: The capability does not declare ``test_selection: append``.
    """
    # @spec AC-002: Append selected tests only on opt-in
    # — .specs/features/035-unified-cli-surface/spec.md#ac-002
    if cap.test_selection != "append":
        raise DriverTestSelectionError(driver.name, capability)
    return [*argv, *test_paths]


def _capability_argv(
    driver: DriverManifest, capability: str, cap: DriverCapability, cwd: Path
) -> list[str]:
    """Resolve the manifest executable while preserving script validation errors."""
    if cap.script is not None:
        # @spec FR-003: Built-in scripts ship beside their manifest (livespec/drivers/scripts);
        #   custom `.specs/drivers` scripts stay project-relative.
        #   — .specs/features/016-cross-language-test-driver-architecture/spec.md#fr-003
        anchor = cwd
        if not driver.is_custom and driver.source_path is not None:
            anchor = driver.source_path.parent
        script_path = _resolve_script(cap.script, anchor)
        if not script_path.exists():
            raise FileNotFoundError(
                f"Driver {driver.name!r} {capability} script not found: {script_path}"
            )
        # Scripts keep explicit shell semantics; commands remain list-form subprocesses.
        return ["bash", str(script_path)]
    assert cap.command is not None
    return resolve_argv_placeholders(shlex.split(cap.command), cap, cwd, driver.name)


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
    from validator.execution_evidence import EvidenceVerification, verify_execution_receipt

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
    verified = (
        verify_execution_receipt(Path(captured.receipt_path), cwd, feature)
        if captured.receipt_path
        else EvidenceVerification(
            valid=False, certified_acs=[], gaps=captured.gaps or ["No fresh execution receipt"]
        )
    )
    return CapabilityResult(
        capability_name=capability,
        exit_code=captured.exit_code if captured.receipt_path else captured.exit_code or 1,
        stdout=captured.stdout,
        stderr=captured.stderr,
        report_path=cap.report_path,
        execution_receipt_path=captured.receipt_path,
        budget=captured.budget,
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
    del timeout
    from tempfile import TemporaryDirectory

    from ..execution_runner import prepare_uncaptured

    with TemporaryDirectory(prefix="livespec-test-") as directory:
        argv, proc_env = prepare_uncaptured(argv, cwd, proc_env, Path(directory))
        code, stdout, stderr = run_owned(argv, cwd, proc_env)
    result = CapabilityResult(
        capability_name=capability,
        exit_code=code,
        stdout=stdout,
        stderr=stderr,
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
    """Run declared capabilities sequentially within one shared command budget."""
    with command_scope(project_root or Path.cwd(), ["livespec", "capabilities"], timeout):
        return _run_all(driver, project_root, env, timeout, feature)


def _run_all(
    driver: DriverManifest,
    project_root: Path | None,
    env: dict[str, str] | None,
    timeout: float | None,
    feature: str | None,
) -> dict[str, CapabilityResult | None]:
    """All capabilities consume one shared invocation deadline."""
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
