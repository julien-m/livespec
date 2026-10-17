"""Resolve one confined invocation directory without changing project authority."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .execution_capture import ExecutionCapture


def resolve_execution_cwd(root: Path, requested: Path | None) -> Path:
    """Require an existing directory beneath the canonical governing project root."""
    cwd = (root / requested if requested is not None else root).resolve(strict=True)
    if not cwd.is_relative_to(root) or not cwd.is_dir():
        raise ValueError("Execution cwd must be an existing directory confined to project root")
    return cwd


# @spec FR-003: Recheck immutable invocation cwd at consumption/archive
# — .specs/features/096-node-vitest-execution/spec.md#fr-003
def capture_execution_cwd(capture: ExecutionCapture) -> Path:
    """Verify capture-bound directory identity; old captures exclusively mean root."""
    root = Path(capture.project_root)
    if capture.execution_cwd is None:
        # Schema-1 captures predating explicit cwd always ran at the governing root.
        if (
            capture.execution_cwd_identity is not None
            or "execution_cwd" in capture.runner_provenance
        ):
            raise ValueError("Incomplete execution cwd identity")
        return root
    cwd = resolve_execution_cwd(root, Path(capture.execution_cwd))
    if cwd.relative_to(root).as_posix() != capture.execution_cwd:
        raise ValueError("Execution cwd must use its canonical relative identity")
    stat = cwd.stat()
    if capture.execution_cwd_identity != (stat.st_dev, stat.st_ino):
        raise ValueError("Execution cwd directory changed")
    if capture.runner_provenance.get("runner") == "vitest" and (
        capture.runner_provenance.get("execution_cwd") != str(cwd)
    ):
        raise ValueError("Execution cwd differs from trusted runner provenance")
    return cwd


def resolve_runner_cwd(root: Path, requested: Path | None, argv: list[str]) -> Path:
    """Reject non-root cwd for adapters whose preparation still assumes project root."""
    from .execution_vitest import is_vitest

    cwd = resolve_execution_cwd(root, requested)
    if cwd != root and not is_vitest(argv):
        raise ValueError("Non-root execution cwd is supported only for direct Vitest")
    return cwd
