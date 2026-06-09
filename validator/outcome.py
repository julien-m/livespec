# LiveSpec traceability anchors
# @spec(FR-007)
# @spec(FR-012)

"""4-state outcome classifier for verify-output reports.

# @spec FR-012: outcome classifier
#   — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-012
"""

from __future__ import annotations

from typing import Literal

Outcome = Literal["success", "drift", "blocked", "error"]

OUTCOME_EXIT_CODES: dict[Outcome, int] = {
    "success": 0,
    "drift": 1,
    "error": 1,
    "blocked": 2,
}


def classify(
    *,
    artifact_exit_code: int | None,
    any_must_failed: bool,
    blocked_reason: str | None = None,
) -> Outcome:
    """Classify the verifier outcome.

    Args:
        artifact_exit_code: Exit code recorded by the wrapped command, or
            ``None`` if no artifact could be loaded.
        any_must_failed: True if at least one ``must`` (or ``must_not``) rule
            failed.
        blocked_reason: When set, forces the ``blocked`` outcome regardless
            of the other inputs.

    Returns:
        One of ``"success" | "drift" | "blocked" | "error"``.
    """
    if blocked_reason is not None or artifact_exit_code is None:
        return "blocked"
    if artifact_exit_code != 0:
        return "error"
    if any_must_failed:
        return "drift"
    return "success"


def exit_code_for(outcome: Outcome) -> int:
    """Return the CLI exit code for an outcome."""
    return OUTCOME_EXIT_CODES[outcome]


# Export the outcome vocabulary shared by verification and CLI rendering.
__all__ = ["OUTCOME_EXIT_CODES", "Outcome", "classify", "exit_code_for"]
