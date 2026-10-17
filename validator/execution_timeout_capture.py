"""Unsuccessful evidence when managed preparation exhausts its command budget."""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .execution_capture import CaptureResult


def timeout_capture(
    argv: list[str],
    root: Path,
    feature: str,
    adapter: str,
    budget: dict[str, object],
    *,
    execution_cwd: Path | None = None,
) -> CaptureResult:
    """Publish a fresh, explicitly incomplete timeout; never reuse a prior report."""
    from .execution_capture import ExecutionCapture, _finish_capture, _run_directory
    from .execution_scope import digest
    from .execution_working_directory import resolve_execution_cwd

    root = root.resolve(strict=True)
    cwd = resolve_execution_cwd(root, execution_cwd)
    stat = cwd.stat()
    directory, identity = _run_directory(root)
    stderr = "TIMEOUT during managed preparation or evidence collection"
    capture = ExecutionCapture(
        invocation=directory.name,
        directory_identity=identity,
        project_root=str(root),
        execution_cwd=cwd.relative_to(root).as_posix(),
        execution_cwd_identity=(stat.st_dev, stat.st_ino),
        feature=feature,
        argv=argv,
        runner_provenance={},
        started_ns=time.time_ns(),
        finished_ns=time.time_ns(),
        exit_code=124,
        before={},
        after={},
        raw_before={},
        raw_after={},
        report_adapter=adapter,
        report_sha256=None,
        stdout_sha256=digest(b""),
        stderr_sha256=digest(stderr.encode()),
        gaps=["Command budget exceeded; preparation incomplete"],
        budget=budget,
    )
    return _finish_capture(directory, capture, "", stderr)
