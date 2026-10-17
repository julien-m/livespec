"""One independent review of the complete feature diff (feature 086 FR-004 to FR-006).

``prepare`` hashes every path of the feature diff, ``record`` accepts a reviewer
report only when it covers that exact scope, and ``verify`` re-validates the stored
report of the latest round of every kind required by the lane against the diff.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, cast

from pydantic import ValidationError

from ..bugfix.diff import DiffUnavailableError, resolve_commit
from .lane import DeliveryInputError, Lane, LaneReason
from .review_models import (
    KINDS,
    MAX_BLOCKED_ROUNDS,
    SCHEMA_VERSION,
    DeliveryReport,
    Kind,
    ReviewOutcome,
    read_json,
    receipt_path,
    report_reasons,
    scope_path,
    write_json,
)
from .review_scope import base_problem, current_scope
from .revision import read_revision

__all__ = [
    "KINDS",
    "Kind",
    "ReviewOutcome",
    "current_scope",
    "prepare_scope",
    "receipt_path",
    "record_report",
    "scope_path",
    "verify_review",
]


# @spec FR-003: Share root scope at every review stage
#   — .specs/features/097-root-feature-delivery-review/spec.md#fr-003
def prepare_scope(root: Path, feature: str, base: str, lane: Lane) -> tuple[dict[str, Any], str]:
    """Write and return the review scope; the second value is an error code or ''."""
    target = scope_path(root, feature)
    try:
        commit = resolve_commit(root, base)
        problem = base_problem(root, feature, commit)
        files = current_scope(root, commit, feature) if not problem else {}
    except DiffUnavailableError as exc:
        return {"feature": feature, "detail": str(exc)}, "diff_unavailable"
    if problem:
        return {"feature": feature, "detail": problem}, "base_not_feature_start"
    if not files:
        return {"feature": feature, "base_commit": commit}, "empty_scope"
    scope = {
        "schema_version": SCHEMA_VERSION,
        "feature": feature,
        "base": base,
        "base_commit": commit,
        "lane": lane,
        "files": files,
    }
    write_json(target, scope)
    return scope, ""


def _trailing_blocked(rounds: list[dict[str, Any]]) -> int:
    count = 0
    for item in reversed(rounds):
        if item.get("verdict") != "BLOCKED":
            break
        count += 1
    return count


def _changed(now: dict[str, str], files: dict[str, str]) -> str:
    return ", ".join(sorted(p for p in set(now) | set(files) if now.get(p) != files.get(p)))


def _kinds(receipt: dict[str, Any], feature: str) -> dict[str, Any] | None:
    """The kinds map of a well-formed receipt of ``feature``, else None."""
    kinds = receipt.get("kinds")
    if receipt.get("feature") != feature or not isinstance(kinds, dict):
        return None
    for value in cast(dict[str, Any], kinds).values():
        rounds = value.get("rounds") if isinstance(value, dict) else None
        if not isinstance(rounds, list) or not all(isinstance(r, dict) for r in rounds):
            return None
    return cast(dict[str, Any], kinds)


def _load_receipt(root: Path, feature: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Return the receipt and its kinds map, or None when malformed."""
    receipt = read_json(receipt_path(root, feature)) or {
        "schema_version": SCHEMA_VERSION,
        "feature": feature,
        "kinds": {},
    }
    kinds = _kinds(receipt, feature)
    return None if kinds is None else (receipt, kinds)


# @spec FR-005: Record a complete-scope report under the round cap
#   — .specs/features/086-risk-proportional-delivery/spec.md#fr-005
def record_report(root: Path, feature: str, kind: Kind, report_file: Path) -> ReviewOutcome:
    """Validate a report against the prepared scope and append it as a round."""
    outcome = ReviewOutcome(feature, receipt_path=str(receipt_path(root, feature)))
    try:
        raw = report_file.read_text(encoding="utf-8")  # Read once: validated bytes are stored.
        report = DeliveryReport.model_validate_json(raw)
    except (OSError, ValueError, ValidationError) as exc:
        raise DeliveryInputError(f"invalid review report {report_file}: {exc}") from exc
    outcome.verdict = report.verdict
    scope = read_json(scope_path(root, feature))
    files = scope.get("files") if scope else None
    if not scope or scope.get("feature") != feature or not isinstance(files, dict):
        outcome.reasons.append(
            LaneReason("scope_missing", "run `livespec delivery review prepare`")
        )
        return outcome
    prepared = cast(dict[str, str], files)
    try:
        problem = base_problem(root, feature, str(scope.get("base_commit")))
        now = current_scope(root, str(scope.get("base_commit")), feature) if not problem else {}
    except DiffUnavailableError as exc:
        outcome.reasons.append(LaneReason("diff_unavailable", str(exc)))
        return outcome
    if problem:
        outcome.reasons.append(LaneReason("base_not_feature_start", problem))
        return outcome
    if now != prepared:
        outcome.reasons.append(LaneReason("scope_changed", _changed(now, prepared)))
    outcome.reasons.extend(report_reasons(report, prepared))
    loaded = _load_receipt(root, feature)
    if loaded is None:
        outcome.reasons.append(LaneReason("receipt_invalid", outcome.receipt_path))
        return outcome
    receipt, kinds = loaded
    rounds = cast(list[dict[str, Any]], kinds.setdefault(kind, {"rounds": []})["rounds"])
    if _trailing_blocked(rounds) >= MAX_BLOCKED_ROUNDS:
        detail = f"{kind}: initial report and two corrections were BLOCKED; escalate"
        outcome.reasons.append(LaneReason("round_cap_reached", detail))
    if outcome.reasons:
        return outcome
    rounds.append(
        {
            "verdict": report.verdict,
            "base_commit": scope["base_commit"],
            "files": prepared,
            "report_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "report_raw": raw,
        }
    )
    write_json(receipt_path(root, feature), receipt)
    if report.verdict == "BLOCKED":
        detail = f"{kind} round {_trailing_blocked(rounds)} of {MAX_BLOCKED_ROUNDS} BLOCKED"
        outcome.reasons.append(LaneReason("review_blocked", detail))
    return outcome


def _latest_pass(
    root: Path, feature: str, kinds: dict[str, Any], kind: str
) -> tuple[list[LaneReason], str]:
    """Re-validate the stored report of the latest round; return reasons and reviewer id."""
    rounds = cast(list[dict[str, Any]], (kinds.get(kind) or {}).get("rounds") or [])
    if not rounds:
        return [LaneReason(f"kind_missing:{kind}", f"no {kind} report")], ""
    latest = rounds[-1]
    raw = latest.get("report_raw")
    files = latest.get("files")
    try:
        report = DeliveryReport.model_validate_json(str(raw))
    except ValidationError:
        return [LaneReason(f"receipt_invalid:{kind}", "stored report is not a valid report")], ""
    sha = hashlib.sha256(str(raw).encode()).hexdigest()
    if sha != latest.get("report_sha256") or not isinstance(files, dict):
        return [LaneReason(f"receipt_invalid:{kind}", "stored report or scope altered")], ""
    scoped = cast(dict[str, str], files)
    if report.verdict != "PASS" or latest.get("verdict") != "PASS":
        return [LaneReason(f"latest_round_blocked:{kind}", "latest is BLOCKED")], ""
    if inconsistent := report_reasons(report, scoped):
        return [LaneReason(f"receipt_invalid:{kind}", r.code) for r in inconsistent], ""
    try:
        problem = base_problem(root, feature, str(latest.get("base_commit")))
        now = current_scope(root, str(latest.get("base_commit")), feature) if not problem else {}
    except DiffUnavailableError as exc:
        return [LaneReason("diff_unavailable", str(exc))], ""
    if problem:
        return [LaneReason("base_not_feature_start", f"{kind}: {problem}")], ""
    if now != scoped:
        return [LaneReason("scope_changed", f"{kind}: {_changed(now, scoped)}")], ""
    return [], f"{report.reviewer.agent}\0{sha}"


def _pair(root: Path, feature: str, kinds: dict[str, Any]) -> list[LaneReason]:
    review, first = _latest_pass(root, feature, kinds, "review")
    audit, second = _latest_pass(root, feature, kinds, "audit")
    reasons = review + audit
    if not reasons and set(first.split("\0")) & set(second.split("\0")):
        reasons.append(LaneReason("reviewers_not_independent", "same agent or same report"))
    return reasons


# @spec FR-006: Current PASS for every required kind
#   — .specs/features/086-risk-proportional-delivery/spec.md#fr-006
def verify_review(
    root: Path, feature: str, lane: Lane, receipt: Path | None = None
) -> ReviewOutcome:
    """Full lane: review and audit. Light lane: combined, or review and audit."""
    path = receipt or receipt_path(root, feature)
    outcome = ReviewOutcome(feature, receipt_path=str(path))
    data = read_json(path)
    try:
        revision = read_revision(root, feature)
    except ValueError as exc:
        revision = {"error": str(exc)}
    if revision is not None:
        code = "spec_revision_malformed" if "error" in revision else "spec_revision_open"
        detail = revision.get("error", "close the spec revision first")
        outcome.reasons.append(LaneReason(code, detail))
        outcome.verdict = "BLOCKED"
        return outcome
    kinds_map = _kinds(data, feature) if data else None
    if kinds_map is None:
        code = "receipt_invalid" if data else "no_receipt"
        outcome.reasons.append(LaneReason(code, str(path)))
        outcome.verdict = "BLOCKED" if data else "MISSING"
        return outcome
    if lane == "full":
        outcome.reasons = _pair(root, feature, kinds_map)
    else:
        combined = _latest_pass(root, feature, kinds_map, "combined")[0]
        pair = _pair(root, feature, kinds_map) if combined else []
        if combined and pair:
            pair_recorded = any(
                (kinds_map.get(kind) or {}).get("rounds") for kind in ("review", "audit")
            )
            combined_recorded = bool((kinds_map.get("combined") or {}).get("rounds"))
            outcome.reasons = combined if combined_recorded or not pair_recorded else pair
    outcome.verdict = "BLOCKED" if outcome.reasons else "PASS"
    return outcome
