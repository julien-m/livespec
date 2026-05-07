"""Documented exit codes for the unified `livespec` CLI surface.

These constants are the single source of truth for the exit codes documented
in :doc:`docs/cli-reference.md` (Feature 035, AC-011 / FR-007).
"""

# @spec FR-007: Structured exit codes — .specs/features/035-unified-cli-surface/spec.md#fr-007
# @spec AC-011: Documented codes — .specs/features/035-unified-cli-surface/spec.md#ac-011

from __future__ import annotations

#: Operation completed successfully.
EXIT_OK: int = 0
#: Required environment is missing — typically ``.specs/`` is absent or the
#: command was invoked outside a git working tree.
EXIT_MISSING_SPECS: int = 1
#: No driver matched the project — see ``livespec drivers`` for the list of
#: known stacks.
EXIT_NO_DRIVER: int = 2
#: A coverage threshold failed (used by ``livespec test`` and
#: ``livespec coverage``).
EXIT_COVERAGE_FAIL: int = 3
#: The active driver does not implement the requested capability — for
#: example, ``livespec mutation`` on a driver without a ``mutation`` block.
EXIT_CAPABILITY_UNSUPPORTED: int = 4
#: ``livespec preflight`` detected at least one critical missing tool.
EXIT_PREFLIGHT_FAIL: int = 5

__all__ = [
    "EXIT_CAPABILITY_UNSUPPORTED",
    "EXIT_COVERAGE_FAIL",
    "EXIT_MISSING_SPECS",
    "EXIT_NO_DRIVER",
    "EXIT_OK",
    "EXIT_PREFLIGHT_FAIL",
]
