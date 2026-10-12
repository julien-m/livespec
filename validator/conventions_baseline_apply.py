# @spec FR-005, FR-007: Repo baseline partition and receipt binding
#   .specs/features/082-conventions-gate-signal/spec.md#fr-005

"""Apply the versioned repo baseline to a conventions result and bind receipts to it."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import cast

from .conventions_baseline import (
    BASELINE_INVALID,
    BASELINE_RELATIVE_PATH,
    WRITE_BASELINE_HINT,
    BaselineEntry,
    BaselineError,
    BaselineKey,
    ConventionsBaseline,
    baseline_sha256,
    is_baselinable,
    load_baseline,
    severity_value,
)
from .conventions_gate_types import GateBlocker, GateResult, GateVerdict, GateViolation

BASELINE_MISMATCH = "baseline_sha256_mismatch"


def apply_repo_baseline(project_root: Path, result: GateResult) -> GateResult:
    """Apply the project baseline to a repo-scope result; no file means no change."""
    try:
        baseline = load_baseline(project_root)
    except BaselineError as exc:
        blocker = GateBlocker(BASELINE_INVALID, str(exc), WRITE_BASELINE_HINT)
        return replace(result, verdict=GateVerdict.BLOCKED, blockers=[*result.blockers, blocker])
    if baseline is None:
        return result
    return apply_baseline(result, baseline)


def apply_baseline(result: GateResult, baseline: ConventionsBaseline) -> GateResult:
    """Partition error violations into recorded debt and new violations.

    Strategy: group current baselinable errors by `(rule_id, path)` in line order; a
    violation is eligible when its `rule_ids` are a subset of the recorded ones; eligible
    violations first consume identical recorded messages, then fill the recorded count;
    the rest are new. Recorded occurrences left unmatched are counted as resolved.
    """
    groups: dict[BaselineKey, list[GateViolation]] = {}
    kept: list[GateViolation] = []
    for violation in result.violations:
        if is_baselinable(violation):
            groups.setdefault((violation.rule_id, violation.path), []).append(violation)
        else:
            kept.append(violation)
    debt: list[GateViolation] = []
    resolved = 0
    for key, entry in baseline.by_key().items():
        matched, new = _match_group(groups.pop(key, []), entry)
        debt.extend(matched)
        kept.extend(new)
        resolved += entry.count - len(matched)
    for items in groups.values():
        kept.extend(items)
    summary: dict[str, object] = {
        "path": BASELINE_RELATIVE_PATH.as_posix(),
        "sha256": baseline.sha256,
        "baselined_count": len(debt),
        "new_count": sum(1 for item in kept if is_baselinable(item)),
        "resolved_count": resolved,
    }
    return replace(
        result,
        verdict=_verdict(result.blockers, kept),
        violations=_sorted(kept),
        baselined_violations=_sorted(debt),
        baseline=summary,
    )


def baseline_receipt_fields(result: GateResult) -> dict[str, object]:
    """Return the additive receipt fields of a result evaluated against a baseline."""
    if result.baseline is None:
        return {}
    return {
        "baseline": result.baseline,
        "baselined_violations": [item.to_dict() for item in result.baselined_violations],
    }


def receipt_baseline_current(project_root: Path, payload: Mapping[str, object]) -> bool:
    """Return False when a receipt records a baseline other than the current file.

    Receipts without a recorded baseline (feature scope, legacy) are always current; a
    recorded baseline whose file changed or was deleted is not.
    """
    recorded = payload.get("baseline")
    if recorded is None:
        return True
    if not isinstance(recorded, dict):
        return False
    return cast(dict[str, object], recorded).get("sha256") == baseline_sha256(project_root)


def _match_group(
    items: list[GateViolation], entry: BaselineEntry
) -> tuple[list[GateViolation], list[GateViolation]]:
    allowed = set(entry.rule_ids)
    remaining = Counter(entry.messages)
    matched: list[GateViolation] = []
    pending: list[GateViolation] = []
    new: list[GateViolation] = []
    for item in sorted(items, key=lambda violation: violation.line):
        if not set(item.rule_ids) <= allowed:
            new.append(item)
        elif remaining[item.message] > 0:
            remaining[item.message] -= 1
            matched.append(item)
        else:
            pending.append(item)
    for item in pending:
        # Message drift (e.g. a longer function) stays debt while within the recorded count.
        if len(matched) < entry.count:
            matched.append(item)
        else:
            new.append(item)
    return matched, new


def _verdict(blockers: list[GateBlocker], violations: list[GateViolation]) -> GateVerdict:
    if blockers:
        return GateVerdict.BLOCKED
    if any(severity_value(item) == "error" for item in violations):
        return GateVerdict.FAIL
    return GateVerdict.PASS


def _sorted(violations: list[GateViolation]) -> list[GateViolation]:
    return sorted(violations, key=lambda item: (item.path, item.line, item.rule_id))
