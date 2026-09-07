"""Read explicit goal control-plane inputs without project discovery."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .goal_json import JsonObject, copy_json_object
from .goal_pairing import claims_spec_init, validate_goal_pair
from .specs_utils import find_specs_root

GoalOperation = Literal["prove", "archive"]

# Ten MiB bounds run artifacts while remaining above normal CLI transcripts.
MAX_TRANSCRIPT_BYTES = 10 * 1024 * 1024


class GoalInputError(Exception):
    """Report invalid explicit control input before root discovery or mutation.

    Args:
        message: Stable boundary failure owned by the raising parser.

    Side effects:
        None; construction never reads or mutates project state.
    """


@dataclass(frozen=True)
class ParsedGoalInputs:
    """Carry parsed pair data and the explicit mutable state path."""

    contract_path: Path
    state_path: Path
    contract: JsonObject
    state: JsonObject


@dataclass(frozen=True)
class ResolvedGoalInputs:
    """Carry validated pair data plus its authoritative project root."""

    state_path: Path
    contract: JsonObject
    state: JsonObject
    project_root: Path


# @spec FR-004: Require explicit prove pair, FR-005: Require archive pair
# @spec FR-012: Fail closed on malformed control files
#   — .specs/features/076-spec-init-goal-bootstrap/spec.md#fr-004
def read_goal_pair_inputs(
    contract_token: str | None,
    state_token: str | None,
    *,
    operation: GoalOperation,
) -> ParsedGoalInputs:
    """Read explicit contract and state JSON objects.

    Args:
        contract_token: Raw ``--contract`` option value.
        state_token: Raw ``--state`` option value.
        operation: Boundary name used in actionable diagnostics.

    Returns:
        Parsed control-plane pair with original file paths.

    Raises:
        GoalInputError: If either input is omitted, empty, unreadable, or malformed.
    """
    contract_path = _required_file(contract_token, "--contract", operation)
    state_path = _required_file(state_token, "--state", operation)
    contract = _read_json_object(contract_path, operation)
    state = _read_json_object(state_path, operation)
    return ParsedGoalInputs(contract_path, state_path, contract, state)


def resolve_goal_pair_inputs(
    contract_token: str | None,
    state_token: str | None,
    *,
    operation: GoalOperation,
    feature: str | None = None,
) -> ResolvedGoalInputs:
    """Validate a bootstrap pair or preserve strict non-init root discovery.

    Args:
        contract_token: Raw explicit contract path.
        state_token: Raw explicit state path.
        operation: Current proof or archive operation.
        feature: Optional archive feature assertion.

    Returns:
        Parsed pair and authoritative project root.

    Raises:
        GoalInputError: If either control file is missing, unreadable, or malformed.
        GoalPairError: If a claimed bootstrap pair fails identity validation.
        SpecsRootNotFoundError: If a non-bootstrap pair has no initialized root.
    """
    inputs = read_goal_pair_inputs(contract_token, state_token, operation=operation)
    if claims_spec_init(inputs.contract, inputs.state):
        pair = validate_goal_pair(
            inputs.contract,
            inputs.state,
            operation=operation,
            feature=feature,
        )
        return ResolvedGoalInputs(
            inputs.state_path,
            pair.contract,
            pair.state,
            pair.project_root,
        )
    return ResolvedGoalInputs(
        inputs.state_path,
        inputs.contract,
        inputs.state,
        find_specs_root().parent,
    )


def read_evidence_input(evidence_input: str) -> JsonObject:
    """Read inline evidence JSON or an explicit external JSON file.

    Args:
        evidence_input: Inline object JSON or readable file path.

    Returns:
        Parsed evidence object.

    Raises:
        GoalInputError: If evidence is unreadable, malformed, or not an object.
    """
    candidate = Path(evidence_input)
    if candidate.exists():
        return _read_json_object(candidate, "prove")
    try:
        parsed: object = json.loads(evidence_input)
    except json.JSONDecodeError as exc:
        raise GoalInputError(f"invalid --evidence JSON: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise GoalInputError("--evidence JSON root must be an object")
    evidence = copy_json_object(parsed)
    if evidence is None:
        raise GoalInputError("--evidence JSON contains a non-JSON value")
    return evidence


def read_transcript(path: Path | None, *, max_bytes: int = MAX_TRANSCRIPT_BYTES) -> str | None:
    """Read a size-bounded optional transcript file.

    Args:
        path: Explicit transcript path or None.

    Returns:
        Transcript text or None.

    Raises:
        ValueError: If the file exceeds the artifact size bound.
        OSError: If the path is unreadable.
    """
    if path is None:
        return None
    size = path.stat().st_size
    if size > max_bytes:
        raise ValueError(f"transcript file {path} is {size} bytes; max {max_bytes} bytes")
    return path.read_text(encoding="utf-8")


def _required_file(token: str | None, option: str, operation: GoalOperation) -> Path:
    if token is None:
        raise GoalInputError(f"{option} is required; rerender the goal before {operation}")
    if not token.strip():
        raise GoalInputError(f"{option} must not be empty; rerender the goal before {operation}")
    path = Path(token)
    try:
        if not path.is_file():
            raise GoalInputError(
                f"{option} is not a readable file: {path}; rerender the goal before {operation}"
            )
        with path.open("rb"):
            pass
    except OSError as exc:
        raise GoalInputError(
            f"{option} is not readable: {path}: {exc}; rerender the goal before {operation}"
        ) from exc
    return path


def _read_json_object(path: Path, operation: GoalOperation) -> JsonObject:
    try:
        parsed: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GoalInputError(
            f"invalid {operation} JSON file {path}: {exc}; rerender the goal before {operation}"
        ) from exc
    if not isinstance(parsed, dict):
        raise GoalInputError(
            f"invalid {operation} JSON file {path}: root must be an object; "
            f"rerender the goal before {operation}"
        )
    document = copy_json_object(parsed)
    if document is None:
        raise GoalInputError(
            f"invalid {operation} JSON file {path}: contains a non-JSON value; "
            f"rerender the goal before {operation}"
        )
    return document


__all__ = [
    "MAX_TRANSCRIPT_BYTES",
    "GoalInputError",
    "GoalOperation",
    "ParsedGoalInputs",
    "ResolvedGoalInputs",
    "read_evidence_input",
    "read_goal_pair_inputs",
    "read_transcript",
    "resolve_goal_pair_inputs",
]
