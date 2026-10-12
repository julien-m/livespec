# LiveSpec traceability anchors
# @spec(FR-003)

"""Parse cargo-mutants JSON output for the Rust mutation report."""

# @spec FR-003: cargo-mutants JSON parser exposing caught/missed/timeout/unviable
# — .specs/features/021-driver-rust/spec.md#fr-003
# FR-002 / AC-010 (Cargo.toml dependency parser) were removed on 2026-10-12: no
# production caller — `cargo test` runs proptest/quickcheck without detection.

from __future__ import annotations

import json
from typing import Any, cast

_MUTANT_OUTCOMES: tuple[str, ...] = ("caught", "missed", "timeout", "unviable")


def parse_cargo_mutants_json(stdout: str) -> dict[str, int]:
    """Extract mutation counts from ``cargo mutants --json`` output.

    ``cargo mutants --json`` may emit either a single JSON object summarising
    the run, or a stream of JSON objects (one per mutant). This parser handles
    both forms by:
      1. Trying ``json.loads`` on the full stdout (single-object case).
      2. Falling back to line-by-line parsing and aggregating per-mutant
         outcomes by counting the ``outcome`` (or ``status``) field.

    Args:
        stdout: Captured standard output from ``cargo mutants --json``.

    Returns:
        A dictionary with integer counts for ``caught``, ``missed``, ``timeout``
        and ``unviable``. Missing keys default to ``0``. Returns all-zero counts
        when the input cannot be parsed.
    """
    counts: dict[str, int] = {outcome: 0 for outcome in _MUTANT_OUTCOMES}
    text = stdout.strip()
    if not text:
        return counts

    # Form 1 — single JSON object summary (common shape).
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Older cargo-mutants versions may emit line-delimited objects instead of
        # one summary object, so a whole-stdout parse failure is not terminal.
        data = None

    if isinstance(data, dict):
        summary = cast(dict[str, Any], data)
        # Some cargo-mutants versions nest under "outcomes" or "summary".
        candidate = summary
        for nested_key in ("outcomes", "summary"):
            nested = summary.get(nested_key)
            if isinstance(nested, dict):
                candidate = cast(dict[str, Any], nested)
                break
        for outcome in _MUTANT_OUTCOMES:
            value = candidate.get(outcome)
            if isinstance(value, int):
                counts[outcome] = value
            elif isinstance(value, float):
                counts[outcome] = int(value)
        if any(counts[outcome] > 0 for outcome in _MUTANT_OUTCOMES):
            return counts

    # Form 2 — line-delimited JSON, one object per mutant.
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            # Ignore malformed lines so partial JSON streams still yield counts
            # from the valid cargo-mutants events that were emitted.
            continue
        if not isinstance(event, dict):
            continue
        event_dict = cast(dict[str, Any], event)
        outcome_value = event_dict.get("outcome")
        if not isinstance(outcome_value, str):
            outcome_value = event_dict.get("status")
        if isinstance(outcome_value, str):
            normalised = outcome_value.strip().lower()
            if normalised in counts:
                counts[normalised] += 1

    return counts
