"""Count spec and plan review correction rounds and report the cap (feature 088).

A round is one complete ingested review of a distinct normative state. The
initial review and at most two correction rounds may precede readiness; the
third consecutive not-ready round reports `round_cap_reached` so the run stops
for the maintainer instead of looping.
"""

# @spec FR-003: Review round ledger and cap
#   — .specs/features/088-capped-reviews/spec.md#fr-003

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Literal

from validator.semantic.review_contract import ReviewReceipt, carry_over

MAX_CORRECTION_ROUNDS = 2


def rounds_path(project_root: Path, feature: str, kind: Literal["spec", "plan"]) -> Path:
    return project_root / ".specs/features" / feature / ".reviews" / f"{kind}.rounds.json"


def record_round(
    project_root: Path, feature: str, kind: Literal["spec", "plan"], receipt: ReviewReceipt
) -> dict[str, object]:
    """Append a complete review to the ledger and return round, cap and carry-over."""
    path = rounds_path(project_root, feature, kind)
    rounds: list[dict[str, object]] = []
    if path.is_file() and not path.is_symlink():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8")).get("rounds", [])
            if isinstance(loaded, list):
                rounds = [item for item in loaded if isinstance(item, dict)]
        except (OSError, ValueError, AttributeError):
            rounds = []
    if receipt.complete:
        entry: dict[str, object] = {
            "context_hash": receipt.context_hash,
            "ready": receipt.ready,
        }
        if rounds and rounds[-1].get("context_hash") == receipt.context_hash:
            rounds[-1] = entry  # Re-ingesting the same state is not a new round.
        else:
            rounds.append(entry)
        _write(path, {"kind": kind, "rounds": rounds})
    previous = rounds[:-1] if receipt.complete else rounds
    blocked_before = 0
    for item in reversed(previous):
        if item.get("ready"):
            break
        blocked_before += 1
    round_number = blocked_before + 1
    return {
        "round": round_number,
        "max_correction_rounds": MAX_CORRECTION_ROUNDS,
        "round_cap_reached": not receipt.ready and round_number > MAX_CORRECTION_ROUNDS,
        "carry_over": carry_over(receipt) if receipt.complete else [],
    }


def _write(path: Path, payload: dict[str, object]) -> None:
    if path.is_symlink():
        raise ValueError("review_rounds_symlink")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".rounds-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
