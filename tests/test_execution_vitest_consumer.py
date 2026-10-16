"""Reverify both real consumer observations without replacing or rerunning their tests."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from validator.execution_evidence import verify_execution_observation


def _original_unchanged(inputs_path: Path) -> bool:
    """Compare the original checkout bytes and read-only Git status with the baseline."""
    before = json.loads(inputs_path.read_text())
    original = Path(before["source"])
    unchanged = all(
        hashlib.sha256((original / name).read_bytes()).hexdigest() == expected
        for name, expected in before["inputs"].items()
    )
    # Read-only Git status also detects newly introduced consumer files.
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=original,
        capture_output=True,
        text=True,
        check=True,
        timeout=5,
    ).stdout
    return unchanged and status == before["original_git_status"]


@pytest.mark.acceptance
# @spec FR-006: Account for both complete unchanged consumer runs
# — .specs/features/096-node-vitest-execution/spec.md#fr-006
# @spec AC-006: Both unchanged consumer selections
# — .specs/features/096-node-vitest-execution/spec.md#ac-006
def test_both_real_consumer_observations_remain_fresh_and_complete() -> None:
    """Require two complete fresh observations and every original consumer input unchanged."""
    evidence_path = os.environ.get("LIVESPEC_VITEST_CONSUMER_EVIDENCE")
    if not evidence_path:
        pytest.skip("Set LIVESPEC_VITEST_CONSUMER_EVIDENCE to the actual two-run manifest")
    evidence = json.loads(Path(evidence_path).read_text())
    before = json.loads(Path(evidence["inputs_before"]).read_text())
    results = [
        verify_execution_observation(
            Path(run["receipt"]), Path(before["copy"]), evidence["feature"], "passed"
        )
        for run in evidence["runs"]
    ]
    captures = [
        json.loads((Path(run["receipt"]).parent / "capture.json").read_text())
        for run in evidence["runs"]
    ]
    assert (
        len(results) == 2
        and all(result.valid and result.certified_acs == [] for result in results)
        and [len(result.executed_tests) for result in results] == [46, 55]
        and all(
            test.status == "passed" and test.assertion_count and test.assertion_count > 0
            for result in results
            for test in result.executed_tests
        )
        and len({capture["invocation"] for capture in captures}) == 2
        and all(capture["before"] == capture["after"] for capture in captures)
        and _original_unchanged(Path(evidence["inputs_before"]))
    ), [result.gaps for result in results]
