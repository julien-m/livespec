# LiveSpec traceability anchors
# @spec(AC-005)
# @spec(AC-006)

"""Tests for validator/outcome.py.

# @spec FR-012 — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-012
"""

from __future__ import annotations

from validator.outcome import classify, exit_code_for


def test_success_all_must_pass_exit_0():
    assert classify(artifact_exit_code=0, any_must_failed=False) == "success"


def test_drift_must_failed_but_command_exited_0():
    assert classify(artifact_exit_code=0, any_must_failed=True) == "drift"


def test_error_when_artifact_nonzero_exit():
    assert classify(artifact_exit_code=1, any_must_failed=False) == "error"
    assert classify(artifact_exit_code=2, any_must_failed=True) == "error"


def test_blocked_when_no_artifact():
    assert classify(artifact_exit_code=None, any_must_failed=False) == "blocked"


def test_blocked_when_explicit_reason():
    assert (
        classify(
            artifact_exit_code=0,
            any_must_failed=False,
            blocked_reason="override malformed",
        )
        == "blocked"
    )


def test_exit_codes_per_state():
    assert exit_code_for("success") == 0
    assert exit_code_for("drift") == 1
    assert exit_code_for("error") == 1
    assert exit_code_for("blocked") == 2
