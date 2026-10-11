"""Domain errors of ``livespec runtime``; the CLI maps every one of them to exit 1."""

from __future__ import annotations


# @spec FR-001: Runtime error family — .specs/features/083-pinned-runtime-isolation/spec.md#fr-001
class LiveSpecRuntimeError(Exception):
    """Base error for ``livespec runtime`` failures mapped to exit 1 by the CLI.

    Args:
        message: Actionable single-paragraph reason, including a recovery hint.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class RuntimeSourceError(LiveSpecRuntimeError):
    """Raised when an install source, ref or committed tree is refused."""


class RuntimeSnapshotError(LiveSpecRuntimeError):
    """Raised when a runtime snapshot is missing, corrupted or unverifiable."""


class RuntimeLockError(LiveSpecRuntimeError):
    """Raised when ``.specs/livespec.lock`` is absent where required or invalid."""


class RuntimeSelectionError(LiveSpecRuntimeError):
    """Raised when pin, upgrade or dev cannot select the requested runtime."""


class RuntimeDefectError(LiveSpecRuntimeError):
    """Raised when a defect report was kept but its pipeline phase update failed.

    Args:
        message: Failure reason naming the phase update.
        report_path: Path of the report that was written before the failure.
    """

    def __init__(self, message: str, report_path: str) -> None:
        super().__init__(message)
        self.report_path = report_path
