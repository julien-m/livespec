"""Own subprocess invocations and publish immutable execution captures."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import cast

from pydantic import BaseModel, ConfigDict, Field

from .execution_capture_storage import (
    _open_storage,
    _run_directory,
    _write_new,
    acquire_capture_lock,
)
from .execution_deadline import (
    BudgetExpired,
    arm_finalization,
    command_scope,
    current_deadline,
    disarm_deadline_alarm,
    run_owned,
)
from .execution_mapping import AcceptanceMapping
from .execution_runner import CargoRunnerUnavailable, prepare_runner
from .execution_scope import (
    EXECUTION_SCOPE_POLICY,
    digest,
    read_from_directory,
    read_regular,
    source_manifest,
)
from .goal_archive_file import release_archive_lock


class ExecutionCapture(BaseModel):
    """Runner facts bound to one project, feature, command and input revision."""

    model_config = ConfigDict(extra="forbid")
    schema_version: str = "1"
    acceptance_evidence_policy: str = "1"
    scope_policy_version: str = EXECUTION_SCOPE_POLICY
    invocation: str
    directory_identity: tuple[int, int]
    project_root: str
    feature: str
    argv: list[str]
    runner_provenance: dict[str, str]
    assertion_trace_sha256: str | None = None
    vitest_inventory_sha256: str | None = None
    started_ns: int
    finished_ns: int
    exit_code: int
    before: dict[str, str]
    after: dict[str, str]
    raw_before: dict[str, str]
    raw_after: dict[str, str]
    report_adapter: str
    report_sha256: str | None
    report_identity: tuple[int, int] | None = None
    stdout_sha256: str
    stderr_sha256: str
    acceptance_mapping: str | None = None
    # @spec FR-005: Effective limits and timeout provenance
    # — .specs/features/095-test-time-budgets/spec.md#fr-005
    budget: dict[str, object] | None = None
    verification_pending: bool = False
    gaps: list[str] = Field(default_factory=list)


class CaptureResult(BaseModel):
    """Invocation outcome and the published receipt location."""

    exit_code: int
    stdout: str
    stderr: str
    receipt_path: str
    budget: dict[str, object] | None = None
    gaps: list[str]


def capture_execution(
    argv: list[str],
    *,
    project_root: Path,
    feature: str,
    adapter: str,
    env: dict[str, str],
    timeout: float | None = None,
    acceptance_mapping: str | None = None,
    required_report_path: str | None = None,
    verification_pending: bool = False,
) -> CaptureResult:
    """Include runner preparation and evidence capture in the managed deadline."""
    from .execution_timeout_capture import timeout_capture

    with command_scope(project_root, argv, timeout) as scope:
        try:
            return _capture_execution(
                argv,
                project_root=project_root,
                feature=feature,
                adapter=adapter,
                env=dict(env),
                timeout=timeout,
                acceptance_mapping=acceptance_mapping,
                required_report_path=required_report_path,
                verification_pending=verification_pending,
            )
        except BudgetExpired as exc:
            scope.timed_out = True
            try:
                arm_finalization(scope)
                return timeout_capture(argv, project_root, feature, adapter, scope.evidence())
            except BudgetExpired:
                disarm_deadline_alarm()
                return CaptureResult(
                    exit_code=124,
                    stdout="",
                    stderr=f"TIMEOUT: {exc}; no fresh receipt finalized within command budget",
                    receipt_path="",
                    budget=scope.evidence(),
                    gaps=["Command budget exhausted; no fresh execution receipt"],
                )


def _capture_execution(
    argv: list[str],
    *,
    project_root: Path,
    feature: str,
    adapter: str,
    env: dict[str, str],
    timeout: float | None = None,
    acceptance_mapping: str | None = None,
    required_report_path: str | None = None,
    verification_pending: bool = False,
) -> CaptureResult:
    """Execute once with fresh report env; retain honest gaps on insufficient proof."""
    root = project_root.resolve(strict=True)
    directory, directory_identity = _run_directory(root)
    report = directory / "runner-report"
    gaps: list[str] = []
    try:
        argv, provenance = prepare_runner(argv, adapter, report, root=root, env=env)
    except CargoRunnerUnavailable as exc:
        provenance = {}
        gaps.append(f"Unsupported runner: {exc}")
    if not provenance and not gaps:
        gaps.append("Unsupported runner: structured reports alone cannot certify execution")
    raw_before, before = _manifests(root, feature, gaps, acceptance_mapping)
    started = time.time_ns()
    code, stdout, stderr = _invoke(
        argv, root, directory, feature, env, timeout, required_report_path, gaps
    )
    finished, scope = time.time_ns(), current_deadline()
    if scope is not None and scope.timed_out:
        raw_after: dict[str, str] = {}
        after: dict[str, str] = {}
        gaps.append("Post-execution source snapshot omitted after timeout")
    else:
        raw_after, after = _manifests(root, feature, gaps, acceptance_mapping)
    capture = ExecutionCapture(
        acceptance_evidence_policy="2",
        invocation=directory.name,
        directory_identity=directory_identity,
        project_root=str(root),
        feature=feature,
        argv=argv,
        runner_provenance=provenance,
        started_ns=started,
        finished_ns=finished,
        exit_code=code,
        before=before,
        after=after,
        raw_before=raw_before,
        raw_after=raw_after,
        report_adapter=adapter,
        report_sha256=None,
        stdout_sha256=digest(stdout.encode()),
        stderr_sha256=digest(stderr.encode()),
        acceptance_mapping=acceptance_mapping,
        verification_pending=verification_pending,
        gaps=gaps,
    )
    return _finish_capture(directory, capture, stdout, stderr)


def _finish_capture(
    directory: Path, capture: ExecutionCapture, stdout: str, stderr: str
) -> CaptureResult:
    """Publish captured facts and return the same process outcome to the driver."""
    scope = current_deadline()
    if capture.runner_provenance.get("runner") == "vitest" and not (scope and scope.timed_out):
        from .execution_vitest_provenance import current_vitest_provenance

        try:
            if capture.runner_provenance != current_vitest_provenance(capture.runner_provenance):
                capture.gaps.append("Vitest runtime or dependencies changed during invocation")
        except (OSError, ValueError) as exc:
            capture.gaps.append(f"Vitest provenance unavailable after invocation: {exc}")
    if scope is not None:
        capture.budget = scope.evidence()
        if scope.timed_out or capture.exit_code == 124:
            capture.gaps.append("Execution timed out; cannot certify acceptance")
    if capture.before != capture.after:
        capture.gaps.append("Execution inputs changed during invocation")
    _publish(directory, capture, stdout, stderr)
    return CaptureResult(
        exit_code=capture.exit_code,
        stdout=stdout,
        stderr=stderr,
        receipt_path=str(directory / "receipt.json"),
        budget=capture.budget,
        gaps=capture.gaps,
    )


def _invoke(
    argv: list[str],
    root: Path,
    directory: Path,
    feature: str,
    env: dict[str, str],
    timeout: float | None,
    required_report_path: str | None,
    gaps: list[str],
) -> tuple[int, str, str]:
    """Invoke the prepared runner and retain its exact process outcome."""
    proc_env = {
        **env,
        "PYTHONPYCACHEPREFIX": str(directory / "bytecode"),
        "LIVESPEC_EXECUTION_REPORT": str(directory / "runner-report"),
        "LIVESPEC_ASSERTION_TRACE": str(directory / "runner-assertions"),
        "LIVESPEC_EXECUTION_NONCE": directory.name,
        "LIVESPEC_EXECUTION_PROJECT": str(root),
        "LIVESPEC_EXECUTION_FEATURE": feature,
    }
    del timeout
    code, stdout, stderr = run_owned(argv, root, proc_env)
    if required_report_path and not (root / required_report_path).is_file():
        code = code or 1
        stderr += f"\nMissing coverage report at {root / required_report_path}"
        gaps.append("Declared coverage report is missing")
    return code, stdout, stderr


def _manifests(
    root: Path, feature: str, gaps: list[str], acceptance_mapping: str | None = None
) -> tuple[dict[str, str], dict[str, str]]:
    try:
        raw = source_manifest(root)
        if acceptance_mapping:
            raw.update(_acceptance_inputs(root, acceptance_mapping))
        return raw, source_manifest(root, feature)
    except (OSError, ValueError) as exc:
        # Unsupported scope does not prevent the user's command from running;
        # the explicit gap prevents this capture from certifying it.
        gaps.append(f"Execution input scope unavailable: {exc}")
        return {}, {}


# @spec FR-010: Bind governed runner inputs
#   — .specs/features/078-requirement-evidence-integrity/spec.md#fr-010
def _acceptance_inputs(root: Path, relative: str) -> dict[str, str]:
    """Bind governed raw bytes even when Git excludes their generated cache."""
    path = root / relative
    raw = read_regular(path, root)
    mapping = AcceptanceMapping.model_validate_json(raw)
    inputs = {path.relative_to(root).as_posix(): digest(raw)}
    if mapping.derivation == "review":
        review = root / mapping.review_receipt_path
        inputs[review.relative_to(root).as_posix()] = digest(read_regular(review, root))
    return inputs


def _publish(directory: Path, capture: ExecutionCapture, stdout: str, stderr: str) -> None:
    specs_fd, storage_fd = _open_storage(Path(capture.project_root))
    lock = directory_fd = -1
    try:
        lock = acquire_capture_lock(specs_fd)
        directory_fd = os.open(
            capture.invocation, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=storage_fd
        )
        opened = os.fstat(directory_fd)
        if (opened.st_dev, opened.st_ino) != capture.directory_identity:
            raise ValueError("Runner directory replaced before publication")
        try:
            report = read_from_directory(directory_fd, "runner-report")
            _write_new(directory_fd, "report", report)
            capture.report_sha256 = digest(report)
            published = os.stat("report", dir_fd=directory_fd, follow_symlinks=False)
            capture.report_identity = (published.st_dev, published.st_ino)
        except (OSError, ValueError) as exc:
            capture.gaps.append(f"Missing or unstable fresh report: {exc}")
        try:
            assertions = read_from_directory(directory_fd, "runner-assertions")
            _write_new(directory_fd, "assertions", assertions)
            capture.assertion_trace_sha256 = digest(assertions)
        except (OSError, ValueError) as exc:
            capture.gaps.append(f"Missing actual assertion execution trace: {exc}")
        if capture.runner_provenance.get("runner") == "vitest":
            try:
                inventory = read_from_directory(directory_fd, "runner-inventory")
                _write_new(directory_fd, "inventory", inventory)
                capture.vitest_inventory_sha256 = digest(inventory)
            except (OSError, ValueError) as exc:
                capture.gaps.append(f"Missing Vitest test inventory: {exc}")
        capture.gaps.extend(_runner_gaps(directory_fd))
        _write_new(directory_fd, "stdout", stdout.encode())
        _write_new(directory_fd, "stderr", stderr.encode())
        payload = capture.model_dump_json(indent=2).encode()
        _write_new(directory_fd, "capture.json", payload)
        _write_new(
            directory_fd,
            "receipt.json",
            json.dumps(
                {
                    "schema_version": "1",
                    "invocation": capture.invocation,
                    "capture_sha256": digest(payload),
                }
            ).encode(),
        )
    finally:
        if directory_fd >= 0:
            os.close(directory_fd)
        if lock >= 0:
            release_archive_lock(lock)
        os.close(storage_fd)
        os.close(specs_fd)


def _runner_gaps(directory_fd: int) -> list[str]:
    """Gaps the runner itself reported; their presence can only prevent certification."""
    try:
        reported = json.loads(read_from_directory(directory_fd, "runner-gaps"))
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as exc:
        return [f"Unreadable runner gaps: {exc}"]
    if not isinstance(reported, list):
        return ["Unreadable runner gaps: expected a list"]
    return [f"Runner: {gap}" for gap in cast("list[object]", reported)]
