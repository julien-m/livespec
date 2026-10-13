"""One independent review of the complete feature diff (feature 086 FR-004 to FR-006).

``prepare`` hashes every path of the feature diff, ``record`` accepts a reviewer
report only when it covers that exact scope, and ``verify`` re-validates the stored
report of the latest round of every kind required by the lane against the diff.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, cast

from pydantic import ValidationError

from ..bugfix.diff import (
    DiffUnavailableError,
    _git,  # pyright: ignore[reportPrivateUsage]
    base_text,
    collect_diff,
    is_ancestor,
    is_traceability_artifact,
    resolve_commit,
)
from ..normative_identity import normative_hash
from .lane import DeliveryInputError, Lane, LaneReason
from .review_models import (
    DELETED,
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

_LIFECYCLE = ("spec.md", "plan.md")

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


def _lifecycle_document(relative: str) -> bool:
    parts = Path(relative).parts
    return len(parts) == 4 and parts[:2] == (".specs", "features") and parts[3] in _LIFECYCLE


def _lifecycle_only(root: Path, base_commit: str, relative: str) -> bool:
    """A spec or plan whose normative content equals the base is not a change."""
    path = root / relative
    if not _lifecycle_document(relative) or path.is_symlink() or not path.is_file():
        return False
    before = base_text(root, base_commit, relative)
    current = path.read_text(encoding="utf-8")
    return before is not None and normative_hash(before, lifecycle_document=True) == normative_hash(
        current, lifecycle_document=True
    )


def _identity(root: Path, relative: str) -> str:
    """Hash a path without following links; lifecycle-only spec/plan edits keep their hash."""
    path = root / relative
    if path.is_symlink():
        return "symlink:" + os.readlink(path)
    if not os.path.lexists(path):
        return DELETED
    if path.is_dir():
        return "directory"
    data = path.read_bytes()
    if _lifecycle_document(relative):
        return "normative:" + normative_hash(data.decode(), lifecycle_document=True)
    return hashlib.sha256(data).hexdigest()


# @spec FR-004: Complete feature diff scope
#   — .specs/features/086-risk-proportional-delivery/spec.md#fr-004
def current_scope(root: Path, base_commit: str) -> dict[str, str]:
    """Hash every counted path of the feature diff against ``base_commit``.

    Raises:
        DiffUnavailableError: The diff or one of its paths cannot be read.
    """
    try:
        return {
            entry.path: _identity(root, entry.path)
            for entry in collect_diff(root, base_commit)
            if not is_traceability_artifact(entry.path)
            and not _lifecycle_only(root, base_commit, entry.path)
        }
    except (OSError, ValueError) as exc:
        raise DiffUnavailableError(f"unreadable diff path: {exc}") from exc


def _base_problem(root: Path, feature: str, commit: str) -> str:
    """The base must precede the commit that created the feature spec, if committed."""
    if not is_ancestor(root, commit, "HEAD"):
        return f"{commit} is not an ancestor of HEAD"
    spec = f".specs/features/{feature}/spec.md"
    created = _git(root, "log", "--format=%H", "--diff-filter=A", "--", spec).decode().split()
    if not created:
        return ""
    first = created[-1]
    parents = _git(root, "rev-list", "--parents", "-n", "1", first).decode().split()[1:]
    if (parents and is_ancestor(root, commit, parents[0])) or commit == first:
        return ""
    return f"{commit} is newer than the commit before {spec} was created ({first[:12]})"


def prepare_scope(root: Path, feature: str, base: str, lane: Lane) -> tuple[dict[str, Any], str]:
    """Write and return the review scope; the second value is an error code or ''."""
    target = scope_path(root, feature)
    try:
        commit = resolve_commit(root, base)
        problem = _base_problem(root, feature, commit)
        files = current_scope(root, commit) if not problem else {}
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


def _load_receipt(root: Path, feature: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Return the receipt and its kinds map, or None when malformed."""
    receipt = read_json(receipt_path(root, feature)) or {
        "schema_version": SCHEMA_VERSION,
        "feature": feature,
        "kinds": {},
    }
    kinds = receipt.setdefault("kinds", {})
    if receipt.get("feature") != feature or not isinstance(kinds, dict):
        return None
    for value in cast(dict[str, Any], kinds).values():
        if not isinstance(value, dict) or not isinstance(value.get("rounds"), list):
            return None
    return receipt, cast(dict[str, Any], kinds)


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
        now = current_scope(root, str(scope.get("base_commit")))
    except DiffUnavailableError as exc:
        outcome.reasons.append(LaneReason("diff_unavailable", str(exc)))
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


def _latest_pass(root: Path, kinds: dict[str, Any], kind: str) -> tuple[list[LaneReason], str]:
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
        now = current_scope(root, str(latest.get("base_commit")))
    except DiffUnavailableError as exc:
        return [LaneReason("diff_unavailable", str(exc))], ""
    if now != scoped:
        return [LaneReason("scope_changed", f"{kind}: {_changed(now, scoped)}")], ""
    return [], f"{report.reviewer.agent}\0{sha}"


def _pair(root: Path, kinds: dict[str, Any]) -> list[LaneReason]:
    review, first = _latest_pass(root, kinds, "review")
    audit, second = _latest_pass(root, kinds, "audit")
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
    kinds = data.get("kinds") if data else None
    if not data or data.get("feature") != feature or not isinstance(kinds, dict):
        outcome.reasons.append(LaneReason("no_receipt", str(path)))
        outcome.verdict = "MISSING"
        return outcome
    kinds_map = cast(dict[str, Any], kinds)
    if lane == "full":
        outcome.reasons = _pair(root, kinds_map)
    else:
        combined = _latest_pass(root, kinds_map, "combined")[0]
        pair = _pair(root, kinds_map) if combined else []
        if combined and pair:
            pair_recorded = any(
                (kinds_map.get(kind) or {}).get("rounds") for kind in ("review", "audit")
            )
            combined_recorded = bool((kinds_map.get("combined") or {}).get("rounds"))
            outcome.reasons = combined if combined_recorded or not pair_recorded else pair
    outcome.verdict = "BLOCKED" if outcome.reasons else "PASS"
    return outcome
