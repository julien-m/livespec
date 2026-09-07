"""Own subprocess invocations and publish immutable execution captures."""

from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from contextlib import suppress
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .execution_runner import prepare_runner
from .execution_scope import EXECUTION_SCOPE_POLICY, digest, read_from_directory, source_manifest
from .goal_archive_file import acquire_archive_lock, release_archive_lock


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
    gaps: list[str] = Field(default_factory=list)


class CaptureResult(BaseModel):
    """Invocation outcome and the published receipt location."""

    exit_code: int
    stdout: str
    stderr: str
    receipt_path: str
    gaps: list[str]


def _write_new(directory_fd: int, name: str, data: bytes) -> None:
    descriptor = os.open(
        name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd
    )
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
        os.fchmod(stream.fileno(), 0o400)


def _open_storage(root: Path) -> tuple[int, int]:
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    specs_fd = -1
    try:
        # Existing directories must still pass the descriptor no-follow checks.
        with suppress(FileExistsError):
            os.mkdir(".specs", mode=0o700, dir_fd=root_fd)
        specs_fd = os.open(".specs", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
        with suppress(FileExistsError):
            os.mkdir(".execution", mode=0o700, dir_fd=specs_fd)
        storage_fd = os.open(
            ".execution", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=specs_fd
        )
        return specs_fd, storage_fd
    except BaseException:
        if specs_fd >= 0:
            os.close(specs_fd)
        raise
    finally:
        os.close(root_fd)


def _run_directory(root: Path) -> tuple[Path, tuple[int, int]]:
    specs_fd, storage_fd = _open_storage(root)
    try:
        nonce = uuid.uuid4().hex
        os.mkdir(nonce, mode=0o700, dir_fd=storage_fd)
        created = os.stat(nonce, dir_fd=storage_fd, follow_symlinks=False)
        return root / ".specs/.execution" / nonce, (created.st_dev, created.st_ino)
    finally:
        os.close(storage_fd)
        os.close(specs_fd)


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
) -> CaptureResult:
    """Execute once with fresh report env; retain honest gaps on insufficient proof."""
    root = project_root.resolve(strict=True)
    directory, directory_identity = _run_directory(root)
    report = directory / "runner-report"
    argv, provenance = prepare_runner(argv, adapter, report)
    gaps: list[str] = []
    if not provenance:
        gaps.append("Unsupported runner: structured reports alone cannot certify execution")
    raw_before, before = _manifests(root, feature, gaps)
    started = time.time_ns()
    code, stdout, stderr = _invoke(
        argv, root, directory, feature, env, timeout, required_report_path, gaps
    )
    finished = time.time_ns()
    raw_after, after = _manifests(root, feature, gaps)
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
        gaps=gaps,
    )
    return _finish_capture(directory, capture, stdout, stderr)


def _finish_capture(
    directory: Path, capture: ExecutionCapture, stdout: str, stderr: str
) -> CaptureResult:
    """Publish captured facts and return the same process outcome to the driver."""
    if capture.before != capture.after:
        capture.gaps.append("Execution inputs changed during invocation")
    _publish(directory, capture, stdout, stderr)
    return CaptureResult(
        exit_code=capture.exit_code,
        stdout=stdout,
        stderr=stderr,
        receipt_path=str(directory / "receipt.json"),
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
    try:
        completed = subprocess.run(
            argv,
            cwd=root,
            env=proc_env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        code, stdout, stderr = completed.returncode, completed.stdout, completed.stderr
    except FileNotFoundError:
        code, stdout, stderr = 127, "", f"command not found: {argv[0]}"
    except subprocess.TimeoutExpired as exc:
        code, stdout, stderr = 124, _text(exc.stdout), _text(exc.stderr) + "\nExecution timed out"
    if required_report_path and not (root / required_report_path).is_file():
        code = code or 1
        stderr += f"\nMissing coverage report at {root / required_report_path}"
        gaps.append("Declared coverage report is missing")
    return code, stdout, stderr


def _manifests(root: Path, feature: str, gaps: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    try:
        return source_manifest(root), source_manifest(root, feature)
    except (OSError, ValueError) as exc:
        # Unsupported scope does not prevent the user's command from running;
        # the explicit gap prevents this capture from certifying it.
        gaps.append(f"Execution input scope unavailable: {exc}")
        return {}, {}


def _text(value: bytes | str | None) -> str:
    return value.decode(errors="replace") if isinstance(value, bytes) else value or ""


def _publish(directory: Path, capture: ExecutionCapture, stdout: str, stderr: str) -> None:
    specs_fd, storage_fd = _open_storage(Path(capture.project_root))
    lock = acquire_archive_lock(specs_fd)
    directory_fd = -1
    try:
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
        release_archive_lock(lock)
        os.close(storage_fd)
        os.close(specs_fd)
