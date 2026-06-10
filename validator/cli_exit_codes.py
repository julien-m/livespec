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
#: ``livespec visual-gate validate`` detected a comparison drift, a broken
#: registry invariant (e.g. physical copy where a symlink is required), a
#: runtime capture stored under ``.specs/design/screens/``, or a Penflow /
#: design-alignment FAIL verdict.
EXIT_VISUAL_GATE_FAIL: int = 6
#: ``livespec visual-gate validate`` cannot decide because required artifacts,
#: comparison reports, or Penflow workspace pieces are missing. The feature
#: must NOT be marked done while this code is emitted.
EXIT_VISUAL_GATE_BLOCKED: int = 7
#: ``livespec visual-gate cleanup --dry-run`` found misplaced artifacts that
#: would be moved/archived on ``--apply``. Implementation-side guard for the
#: anti-false-positive E2E contract.
EXIT_VISUAL_GATE_CLEANUP_DRIFT: int = 8
#: ``livespec finalize apply`` was blocked: lock timeout (``policy_blocked``),
#: post-write hash mismatch, or partial apply (``state_invalid``). No DONE may
#: be claimed while this code is emitted (Feature 058, AC-004).
# @spec FR-008: Exit-code mapping for finalize failures
#   — .specs/features/058-deterministic-finalization/spec.md#fr-008
EXIT_FINALIZE_BLOCKED: int = 9
#: ``livespec finalize verify`` found coherence violations (R1/R4/R6) or a
#: missing finalize marker for the expected command (Feature 058, AC-006).
EXIT_FINALIZE_VERIFY_FAIL: int = 10

__all__ = [
    "EXIT_CAPABILITY_UNSUPPORTED",
    "EXIT_COVERAGE_FAIL",
    "EXIT_FINALIZE_BLOCKED",
    "EXIT_FINALIZE_VERIFY_FAIL",
    "EXIT_MISSING_SPECS",
    "EXIT_NO_DRIVER",
    "EXIT_OK",
    "EXIT_PREFLIGHT_FAIL",
    "EXIT_VISUAL_GATE_BLOCKED",
    "EXIT_VISUAL_GATE_CLEANUP_DRIFT",
    "EXIT_VISUAL_GATE_FAIL",
]
