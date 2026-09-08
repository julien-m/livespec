# @spec(AC-002)
# @spec(AC-005)

# LiveSpec traceability anchors
# @spec(AC-001)
# @spec(AC-003)
# @spec(AC-004)
# @spec(AC-006)
# @spec(AC-012)

"""Unit tests for the RunArtifact v2 data layer (``validator/run_artifacts.py``).

Covers the archive pipeline (hash gate, goal snapshot, transcripts, receipt
re-verification, outcome classification, atomic write) plus the documentation
truth-fix assertions from feature 039.1.
"""

# Explicit reexports preserve pytest node IDs and public fixture imports.
from tests._run_artifact_01 import (
    FROZEN_NOW,
    FROZEN_NOW_PLUS_MICROSECOND,
    GOAL_HASH,
    REPO_ROOT,
    TestArchiveHappyPath,
    TestArchiveOutcomes,
    TestArchiveTranscripts,
    _make_conventions_receipt,
    _make_finalize_receipt,
    _state_with_receipt,
    _write_conventions_gates,
    make_contract,
    make_state,
    project_root,
)
from tests._run_artifact_02 import (
    TestArchiveRunExclusion,
    TestArtifactHelpers,
    TestReceiptIntegrity,
    TestTruthFixes,
    _state_with_conventions_receipt,
    _task,
)

__all__ = [
    "FROZEN_NOW",
    "FROZEN_NOW_PLUS_MICROSECOND",
    "GOAL_HASH",
    "REPO_ROOT",
    "TestArchiveHappyPath",
    "TestArchiveOutcomes",
    "TestArchiveRunExclusion",
    "TestArchiveTranscripts",
    "TestArtifactHelpers",
    "TestReceiptIntegrity",
    "TestTruthFixes",
    "_make_conventions_receipt",
    "_make_finalize_receipt",
    "_state_with_conventions_receipt",
    "_state_with_receipt",
    "_task",
    "_write_conventions_gates",
    "make_contract",
    "make_state",
    "project_root",
]
