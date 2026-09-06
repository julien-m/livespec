# LiveSpec traceability anchors
# @spec(AC-006)

"""Supervisor↔Subagent return contracts.

Spec anchors (Chantier 2 / Feature 014 — see
``.specs/features/014-supervisor-contracts/spec.md``):

- @spec FR-001: PHASE_RESULT JSON schema.
- @spec FR-002: SHIP_RESULT JSON schema.
- @spec FR-003: Superpowers return contract schema.
- @spec FR-004: Regex-anchored parser for PHASE_RESULT.
- @spec FR-005: Regex-anchored parser for SHIP_RESULT.
- @spec FR-007: Pydantic-based validation integration.

This module defines the canonical typed contracts that subagents (specify,
plan, implement, test, ship, Superpowers) emit at the end of their output.
The supervisor (or ship orchestrator) parses these contracts to drive gates,
checkpoints, and merge decisions.

Anti-prompt-injection design:

1. Each contract is wrapped in a delimiter pair carrying a unique 8-character
   hex hash, e.g. ``⟪PHASE_RESULT_START_a3f1b8c2⟫`` ... ``⟪PHASE_RESULT_END_a3f1b8c2⟫``.
   The Unicode box-drawing characters are unlikely to appear in normal prose;
   the per-invocation hash defeats static parsing attempts.

2. Parsers scan only the **last 30 lines** of agent output, scanning from the
   bottom upward, and accept the **first matching pair** found. An attacker
   prompt that injects an early fake result block is ignored because the
   anchor selects the LAST occurrence.

3. The body between delimiters MUST be valid JSON conforming to the matching
   Pydantic model. Schema violations raise :class:`ContractValidationError`,
   which the caller surfaces as a canonical BLOCKED line.

Backward compatibility:

The legacy key-value format (``PHASE_RESULT: OK\\nFEATURE: ...``) is also
parsed when no delimiter pair is found, with a deprecation warning. Callers
should migrate to the JSON+delimiter format; both will be supported until at
least the next major LiveSpec version.
"""

from __future__ import annotations

import json
import re
import warnings
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from .identity import SLUG_REGEX

# ─── Delimiters ──────────────────────────────────────────────────────────────

# @spec FR-004: Unique delimiter pair — spec.md#fr-004
DELIMITER_HEX_REGEX = r"[0-9a-f]{8}"

PHASE_RESULT_START = re.compile(rf"^⟪PHASE_RESULT_START_({DELIMITER_HEX_REGEX})⟫\s*$")
PHASE_RESULT_END = re.compile(rf"^⟪PHASE_RESULT_END_({DELIMITER_HEX_REGEX})⟫\s*$")

SHIP_RESULT_START = re.compile(rf"^⟪SHIP_RESULT_START_({DELIMITER_HEX_REGEX})⟫\s*$")
SHIP_RESULT_END = re.compile(rf"^⟪SHIP_RESULT_END_({DELIMITER_HEX_REGEX})⟫\s*$")

SUPERPOWERS_START = re.compile(rf"^⟪SUPERPOWERS_RETURN_START_({DELIMITER_HEX_REGEX})⟫\s*$")
SUPERPOWERS_END = re.compile(rf"^⟪SUPERPOWERS_RETURN_END_({DELIMITER_HEX_REGEX})⟫\s*$")

# Maximum lines to scan from the end of agent output.
ANCHOR_WINDOW_LINES = 30

# ─── Errors ──────────────────────────────────────────────────────────────────


class ContractParseError(ValueError):
    """Raised when no contract block can be found in the agent output."""


class ContractValidationError(ValueError):
    """Raised when a contract block is found but fails schema validation."""


# ─── Pydantic schemas ────────────────────────────────────────────────────────


# @spec FR-001: PHASE_RESULT schema — spec.md#fr-001
class PhaseResult(BaseModel):
    """Canonical result returned by every specification pipeline phase agent.

    The schema is intentionally permissive on phase-specific fields (placed in
    ``extra``) so a single parser handles the pipeline's phase variants.
    """

    status: Literal["OK", "BLOCKED"]
    # @spec FR-006: preflight rides the same PHASE_RESULT contract
    #   — .specs/features/059-pipeline-verify-phase/spec.md#fr-006
    # @spec FR-001: analyze reuses spec-check with its actual pipeline identity
    # — .specs/features/070-analyze-gate/spec.md#fr-001
    phase: Literal["specify", "plan", "analyze", "preflight", "implement", "test"]
    feature_slug: str = Field(pattern=SLUG_REGEX.pattern)
    summary: str = Field(min_length=1, max_length=500)
    duration_ms: int = Field(ge=0)
    blocked_reason: str | None = None
    # @spec FR-006: RUN_ARTIFACT field, legacy-tolerant (None when absent)
    #   — .specs/features/059-pipeline-verify-phase/spec.md#fr-006
    # Path shape is enforced (file under .specs/.runs/): absolute OR relative
    # prefixes are both accepted because executors legitimately emit either
    # (the archive.run prove validator resolves both the same way).
    run_artifact: str | None = Field(default=None, pattern=r"^(.*/)?\.specs/\.runs/[^/]+\.json$")
    extra: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


# @spec FR-002: SHIP_RESULT schema — spec.md#fr-002
class ShipResult(BaseModel):
    """Canonical result returned at the end of /spec-feature when called by /spec-ship."""

    status: Literal["OK", "BLOCKED"]
    feature_slug: str = Field(pattern=SLUG_REGEX.pattern)
    branch: str = Field(min_length=1)
    files_changed_count: int = Field(ge=0)
    timestamp: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
    commit_hash: str | None = None
    error: str | None = None
    # @spec FR-008: SHIP_RESULT run_artifact gates merge/delete
    #   — .specs/features/059-pipeline-verify-phase/spec.md#fr-008
    # Same constrained shape as PhaseResult.run_artifact — this path gates
    # merge/branch-delete decisions, so arbitrary strings are rejected.
    run_artifact: str | None = Field(default=None, pattern=r"^(.*/)?\.specs/\.runs/[^/]+\.json$")

    model_config = {"extra": "forbid"}


# @spec FR-003: Superpowers return schema — spec.md#fr-003
class TestResults(BaseModel):
    """Test totals returned by Superpowers."""

    # Pytest collection guard — the class name starts with "Test" but it is a
    # Pydantic model, not a test class. Silence the PytestCollectionWarning.
    __test__ = False

    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    skipped: int = Field(ge=0)

    model_config = {"extra": "forbid"}


class FrAcMapping(BaseModel):
    """One FR/AC traceability entry from the implementer."""

    number: int = Field(ge=1)
    mapping: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


class SuperpowersReturn(BaseModel):
    """Canonical return contract from Superpowers (implementer/documenter/verifier)."""

    files: list[str] = Field(default_factory=list)
    fr_ac: list[FrAcMapping] = Field(default_factory=lambda: [])  # type: ignore[var-annotated]
    test_results: TestResults
    duration_ms: int = Field(ge=0)

    model_config = {"extra": "forbid"}


# ─── Parser core ─────────────────────────────────────────────────────────────


def _find_block_in_window(
    text: str,
    start_re: re.Pattern[str],
    end_re: re.Pattern[str],
) -> tuple[str, str] | None:
    """Scan the last ``ANCHOR_WINDOW_LINES`` lines for a matching START/END delimiter pair.

    Returns ``(hash, body_json)`` for the **last** complete pair, or ``None`` if no
    pair is found within the window.

    "Last" = highest line index of START whose hash matches a subsequent END.
    Scanning from the bottom up defeats prompt-injection of an earlier fake block.
    """
    lines = text.splitlines()
    window = lines[-ANCHOR_WINDOW_LINES:] if len(lines) > ANCHOR_WINDOW_LINES else lines

    # Index ENDs first (we walk bottom-up looking for the matching START).
    end_positions: dict[str, int] = {}
    for i, line in enumerate(window):
        match = end_re.match(line)
        if match:
            end_positions[match.group(1)] = i  # later ENDs overwrite — last END wins per hash

    if not end_positions:
        return None

    # Walk from the bottom up to find the latest START whose hash has a later END.
    for i in range(len(window) - 1, -1, -1):
        match = start_re.match(window[i])
        if not match:
            continue
        digest = match.group(1)
        end_idx = end_positions.get(digest)
        if end_idx is not None and end_idx > i:
            body = "\n".join(window[i + 1 : end_idx]).strip()
            return digest, body
    return None


def _parse_legacy_kv_block(text: str, prefix: str) -> dict[str, str] | None:
    """Parse a legacy key-value PHASE_RESULT block (deprecated).

    Searches for a line ``PHASE_RESULT: <status>`` near the end of ``text`` and
    collects the lines that follow until a blank line is hit. Returns a
    dictionary of ``{key: value}`` or ``None`` if no block is found.
    """
    lines = text.splitlines()
    window = lines[-ANCHOR_WINDOW_LINES:] if len(lines) > ANCHOR_WINDOW_LINES else lines
    start_pattern = re.compile(rf"^{prefix}:\s*(OK|BLOCKED)\s*$")

    start_idx: int | None = None
    for i in range(len(window) - 1, -1, -1):
        if start_pattern.match(window[i]):
            start_idx = i
            break
    if start_idx is None:
        return None

    fields: dict[str, str] = {prefix: start_pattern.match(window[start_idx]).group(1)}  # type: ignore[union-attr]
    for line in window[start_idx + 1 :]:
        if not line.strip():
            break
        m = re.match(r"^([A-Z_][A-Z0-9_]*):\s*(.*)$", line)
        if m:
            fields[m.group(1)] = m.group(2).strip()
    return fields


# ─── Public parsers ──────────────────────────────────────────────────────────


def parse_phase_result(text: str) -> PhaseResult:
    """Extract and validate a PHASE_RESULT block from agent output.

    Args:
        text: Full agent stdout (or any string containing the agent output).

    Returns:
        A validated :class:`PhaseResult`.

    Raises:
        ContractParseError: No PHASE_RESULT block found in the last 30 lines.
        ContractValidationError: Block found but failed schema validation.
    """
    block = _find_block_in_window(text, PHASE_RESULT_START, PHASE_RESULT_END)
    if block is not None:
        _, body = block
        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ContractValidationError(f"PHASE_RESULT body is not valid JSON: {exc}") from exc
        try:
            return PhaseResult.model_validate(data)
        except ValidationError as exc:
            raise ContractValidationError(f"PHASE_RESULT schema validation failed: {exc}") from exc

    # Legacy fallback
    legacy = _parse_legacy_kv_block(text, "PHASE_RESULT")
    if legacy is None:
        raise ContractParseError(
            "no PHASE_RESULT block found (looked for delimiter pair "
            "and legacy key-value format in the last 30 lines)"
        )

    warnings.warn(
        "PHASE_RESULT parsed via legacy key-value format. "
        "Migrate to the delimiter+JSON format (see system/contracts/PHASE_RESULT.md).",
        DeprecationWarning,
        stacklevel=2,
    )
    converted = _legacy_to_phase_result(legacy)
    try:
        return PhaseResult.model_validate(converted)
    except ValidationError as exc:
        raise ContractValidationError(
            f"PHASE_RESULT (legacy format) failed schema validation: {exc}"
        ) from exc


def parse_ship_result(text: str) -> ShipResult:
    """Extract and validate a SHIP_RESULT block from agent output."""
    block = _find_block_in_window(text, SHIP_RESULT_START, SHIP_RESULT_END)
    if block is not None:
        _, body = block
        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ContractValidationError(f"SHIP_RESULT body is not valid JSON: {exc}") from exc
        try:
            return ShipResult.model_validate(data)
        except ValidationError as exc:
            raise ContractValidationError(f"SHIP_RESULT schema validation failed: {exc}") from exc

    legacy = _parse_legacy_kv_block(text, "SHIP_RESULT")
    if legacy is None:
        raise ContractParseError("no SHIP_RESULT block found in the last 30 lines")
    warnings.warn(
        "SHIP_RESULT parsed via legacy key-value format. "
        "Migrate to the delimiter+JSON format (see system/contracts/SHIP_RESULT.md).",
        DeprecationWarning,
        stacklevel=2,
    )
    try:
        return ShipResult.model_validate(_legacy_to_ship_result(legacy))
    except ValidationError as exc:
        raise ContractValidationError(
            f"SHIP_RESULT (legacy format) failed schema validation: {exc}"
        ) from exc


def parse_superpowers_return(text: str) -> SuperpowersReturn:
    """Extract and validate a Superpowers return block from agent output."""
    block = _find_block_in_window(text, SUPERPOWERS_START, SUPERPOWERS_END)
    if block is None:
        raise ContractParseError("no SUPERPOWERS_RETURN delimiter pair found in the last 30 lines")
    _, body = block
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ContractValidationError(f"Superpowers return body is not valid JSON: {exc}") from exc
    try:
        return SuperpowersReturn.model_validate(data)
    except ValidationError as exc:
        raise ContractValidationError(
            f"Superpowers return schema validation failed: {exc}"
        ) from exc


# ─── Legacy bridge ───────────────────────────────────────────────────────────


def _legacy_to_phase_result(fields: dict[str, str]) -> dict[str, Any]:
    """Convert a legacy key-value PHASE_RESULT block to the modern JSON shape."""
    phase_value = fields.get("PHASE", "implement").lower()
    # Legacy bridge for 059 RUN_ARTIFACT: pre-JSON agents emit the path as an
    # uppercase KV line; blank values normalize to None so the supervisor takes
    # the AC-010 latest-artifact fallback instead of verifying an empty path.
    run_artifact = fields.get("RUN_ARTIFACT", "").strip() or None
    return {
        "status": fields["PHASE_RESULT"],
        "phase": phase_value,
        "feature_slug": fields.get("FEATURE", ""),
        "summary": fields.get("SUMMARY", "(no summary in legacy block)"),
        "duration_ms": int(fields.get("DURATION_MS", "0") or 0),
        "blocked_reason": fields.get("BLOCKED_REASON") or None,
        "run_artifact": run_artifact,
        "extra": {
            k: v
            for k, v in fields.items()
            if k
            not in {
                "PHASE_RESULT",
                "PHASE",
                "FEATURE",
                "SUMMARY",
                "DURATION_MS",
                "BLOCKED_REASON",
                "RUN_ARTIFACT",
            }
        },
    }


def _legacy_to_ship_result(fields: dict[str, str]) -> dict[str, Any]:
    """Convert a legacy key-value SHIP_RESULT block to the modern JSON shape."""
    run_artifact = fields.get("RUN_ARTIFACT", "").strip() or None
    return {
        "status": fields["SHIP_RESULT"],
        "feature_slug": fields.get("FEATURE", ""),
        "branch": fields.get("BRANCH", ""),
        "files_changed_count": int(fields.get("FILES_CHANGED_COUNT", "0") or 0),
        "timestamp": fields.get("TIMESTAMP", ""),
        "commit_hash": fields.get("COMMIT_HASH") or None,
        "error": fields.get("ERROR") or None,
        "run_artifact": run_artifact,
    }


# ─── Helpers for emitters ────────────────────────────────────────────────────


def render_phase_result(result: PhaseResult, digest: str) -> str:
    """Serialise a PhaseResult as the canonical delimiter-wrapped block.

    Used by tests and by reference emitters in agent prompts.
    """
    body = result.model_dump_json(indent=2, exclude_none=False)
    return f"⟪PHASE_RESULT_START_{digest}⟫\n{body}\n⟪PHASE_RESULT_END_{digest}⟫"


def render_ship_result(result: ShipResult, digest: str) -> str:
    """Serialise a ShipResult as the canonical delimiter-wrapped block."""
    body = result.model_dump_json(indent=2, exclude_none=False)
    return f"⟪SHIP_RESULT_START_{digest}⟫\n{body}\n⟪SHIP_RESULT_END_{digest}⟫"


def render_superpowers_return(result: SuperpowersReturn, digest: str) -> str:
    """Serialise a SuperpowersReturn as the canonical delimiter-wrapped block."""
    body = result.model_dump_json(indent=2, exclude_none=False)
    return f"⟪SUPERPOWERS_RETURN_START_{digest}⟫\n{body}\n⟪SUPERPOWERS_RETURN_END_{digest}⟫"
