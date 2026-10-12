"""Documented exit codes for the unified `livespec` CLI surface.

These constants are the single source of truth for the exit codes documented
in :doc:`docs/cli-reference.md` (Feature 035, AC-011 / FR-007).
"""

# @spec FR-007: Structured exit codes — .specs/features/035-unified-cli-surface/spec.md#fr-007
# @spec AC-011: Documented codes — .specs/features/035-unified-cli-surface/spec.md#ac-011

from __future__ import annotations

#: Operation completed successfully.
EXIT_OK: int = 0
#: The run itself failed: test suite failure, coverage or mutation threshold not
#: met, or an unexpected exception (constitution "general error").
EXIT_FAILURE: int = 1
#: Required environment is missing — ``.specs/`` is absent or the command was
#: invoked outside a git working tree. Every ``livespec`` command shares this
#: through ``require_specs_root``, so it stays at the general-error code 1.
EXIT_MISSING_SPECS: int = 1
#: Invalid arguments: Typer/Click usage errors or a ``--feature`` value that
#: matches zero or several feature directories.
EXIT_USAGE: int = 2
#: Missing configuration: no driver detected, lcov report not found, capability
#: absent (or without ``test_selection: append`` for ``--feature``), no selected
#: test, preflight manifest or critical tool missing, no resolvable base branch.
EXIT_CONFIG: int = 3
#: Interrupted by Ctrl+C (128 + SIGINT).
EXIT_INTERRUPTED: int = 130
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
    "EXIT_CONFIG",
    "EXIT_FAILURE",
    "EXIT_FINALIZE_BLOCKED",
    "EXIT_FINALIZE_VERIFY_FAIL",
    "EXIT_INTERRUPTED",
    "EXIT_MISSING_SPECS",
    "EXIT_OK",
    "EXIT_USAGE",
    "EXIT_VISUAL_GATE_BLOCKED",
    "EXIT_VISUAL_GATE_CLEANUP_DRIFT",
    "EXIT_VISUAL_GATE_FAIL",
]
