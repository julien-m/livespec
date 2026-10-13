"""One independent review of the complete feature diff (feature 086 FR-004 to FR-006).

``prepare`` hashes every path of the feature diff, ``record`` accepts a reviewer
report only when it covers that exact scope, and ``verify`` checks that the latest
round of every kind required by the lane passed and that nothing changed since.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..bugfix.diff import (
    DiffUnavailableError,
    collect_diff,
    is_traceability_artifact,
    resolve_commit,
)
from .lane import DeliveryInputError, Lane, LaneReason

Kind = Literal["combined", "review", "audit"]
KINDS: tuple[Kind, ...] = ("combined", "review", "audit")
SCHEMA_VERSION = "1"
# Initial report plus two correction rounds (maintainer decision, feature 086).
MAX_BLOCKED_ROUNDS = 3
DELETED = "deleted"


class ReviewCheck(BaseModel):
    """One required check the implementing agent ran and gave to the reviewer."""

    model_config = ConfigDict(extra="forbid", strict=True)
    command: str = Field(min_length=1)
    exit_code: int


class ReviewFinding(BaseModel):
    """One reviewer finding with its evidence and proposed correction."""

    model_config = ConfigDict(extra="forbid", strict=True)
    severity: Literal["blocking", "warning", "info"]
    file: str = ""
    line: int | None = None
    rule: str = ""
    evidence: str = Field(min_length=1)
    correction: str = ""


class Reviewer(BaseModel):
    """Identity of the independent native reviewer."""

    model_config = ConfigDict(extra="forbid", strict=True)
    agent: str = Field(min_length=1)
    model: str = Field(min_length=1)
    effort: str = Field(min_length=1)


class DeliveryReport(BaseModel):
    """Actual reviewer output, recorded as returned."""

    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: str = SCHEMA_VERSION
    reviewer: Reviewer
    verdict: Literal["PASS", "BLOCKED"]
    reviewed_files: list[str]
    checks: list[ReviewCheck] = Field(default_factory=lambda: list[ReviewCheck]())
    findings: list[ReviewFinding] = Field(default_factory=lambda: list[ReviewFinding]())


@dataclass
class ReviewOutcome:
    """Result of record or verify; no reason means accepted or current."""

    feature: str
    reasons: list[LaneReason] = field(default_factory=lambda: list[LaneReason]())
    verdict: str = ""
    receipt_path: str = ""

    def to_json(self) -> dict[str, object]:
        """Return the JSON object printed by the CLI."""
        return {
            "feature": self.feature,
            "verdict": self.verdict,
            "receipt_path": self.receipt_path,
            "reasons": [{"code": r.code, "detail": r.detail} for r in self.reasons],
        }


def _feature_dir(root: Path, feature: str) -> Path:
    from ..identity import SLUG_REGEX

    directory = root / ".specs" / "features" / feature
    if not SLUG_REGEX.fullmatch(feature) or not (directory / "spec.md").is_file():
        raise DeliveryInputError(f"unknown feature {feature!r}")
    return directory


def scope_path(root: Path, feature: str) -> Path:
    """Return the prepared scope location of a feature."""
    return _feature_dir(root, feature) / ".reviews" / "delivery-scope.json"


def receipt_path(root: Path, feature: str) -> Path:
    """Return the delivery review receipt location of a feature."""
    return _feature_dir(root, feature) / ".reviews" / "delivery.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# @spec FR-004: Complete feature diff scope
#   — .specs/features/086-risk-proportional-delivery/spec.md#fr-004
def current_scope(root: Path, base_commit: str) -> dict[str, str]:
    """Hash every counted path of the feature diff against ``base_commit``.

    Raises:
        DiffUnavailableError: The diff cannot be computed.
    """
    files: dict[str, str] = {}
    for entry in collect_diff(root, base_commit):
        if is_traceability_artifact(entry.path):
            continue
        path = root / entry.path
        files[entry.path] = _sha256(path) if path.is_file() else DELETED
    return files


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    if path.is_symlink():
        raise DeliveryInputError(f"refusing to write through a link: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".delivery-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return cast(dict[str, Any], data) if isinstance(data, dict) else None


def prepare_scope(root: Path, feature: str, base: str, lane: Lane) -> tuple[dict[str, Any], str]:
    """Write and return the review scope; the second value is an error code or ''."""
    target = scope_path(root, feature)
    try:
        commit = resolve_commit(root, base)
        files = current_scope(root, commit)
    except DiffUnavailableError as exc:
        return {"feature": feature, "detail": str(exc)}, "diff_unavailable"
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
    _write_json(target, scope)
    return scope, ""


def load_report(path: Path) -> DeliveryReport:
    """Parse a reviewer report.

    Raises:
        DeliveryInputError: Unreadable or invalid report.
    """
    try:
        return DeliveryReport.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        raise DeliveryInputError(f"invalid review report {path}: {exc}") from exc


def _trailing_blocked(rounds: list[dict[str, Any]]) -> int:
    count = 0
    for item in reversed(rounds):
        if item.get("verdict") != "BLOCKED":
            break
        count += 1
    return count


def _report_reasons(report: DeliveryReport, scope_files: dict[str, str]) -> list[LaneReason]:
    reasons: list[LaneReason] = []
    missing = sorted(set(scope_files) - set(report.reviewed_files))
    if missing:
        reasons.append(LaneReason("scope_not_covered", ", ".join(missing)))
    if report.reviewer.effort.lower() != "high":
        reasons.append(LaneReason("reviewer_effort_not_high", report.reviewer.effort))
    blocking = [f for f in report.findings if f.severity == "blocking"]
    failed = [c.command for c in report.checks if c.exit_code != 0]
    if report.verdict == "PASS" and (blocking or failed):
        detail = f"{len(blocking)} blocking finding(s), failed checks: {failed}"
        reasons.append(LaneReason("verdict_inconsistent", detail))
    if report.verdict == "BLOCKED" and not blocking:
        reasons.append(LaneReason("verdict_inconsistent", "BLOCKED without a blocking finding"))
    return reasons


# @spec FR-005: Record a complete-scope report under the round cap
#   — .specs/features/086-risk-proportional-delivery/spec.md#fr-005
def record_report(root: Path, feature: str, kind: Kind, report_file: Path) -> ReviewOutcome:
    """Validate a report against the prepared scope and append it as a round."""
    outcome = ReviewOutcome(feature, receipt_path=str(receipt_path(root, feature)))
    report = load_report(report_file)
    outcome.verdict = report.verdict
    scope = _read_json(scope_path(root, feature))
    if scope is None or scope.get("feature") != feature:
        detail = "run `livespec delivery review prepare`"
        outcome.reasons.append(LaneReason("scope_missing", detail))
        return outcome
    prepared = cast(dict[str, str], scope.get("files") or {})
    try:
        now = current_scope(root, str(scope["base_commit"]))
    except DiffUnavailableError as exc:
        outcome.reasons.append(LaneReason("diff_unavailable", str(exc)))
        return outcome
    if now != prepared:
        changed = sorted(p for p in set(now) | set(prepared) if now.get(p) != prepared.get(p))
        outcome.reasons.append(LaneReason("scope_changed", ", ".join(changed)))
    outcome.reasons.extend(_report_reasons(report, prepared))
    receipt = _read_json(receipt_path(root, feature)) or {
        "schema_version": SCHEMA_VERSION,
        "feature": feature,
        "kinds": {},
    }
    kinds = cast(dict[str, dict[str, Any]], receipt.setdefault("kinds", {}))
    rounds = cast(list[dict[str, Any]], kinds.setdefault(kind, {"rounds": []})["rounds"])
    if _trailing_blocked(rounds) >= MAX_BLOCKED_ROUNDS:
        outcome.reasons.append(
            LaneReason(
                "round_cap_reached",
                f"{kind}: initial report and two corrections were BLOCKED; escalate to the "
                "maintainer instead of reviewing again",
            )
        )
    if outcome.reasons:
        return outcome
    raw = report_file.read_bytes()
    rounds.append(
        {
            "verdict": report.verdict,
            "base_commit": scope["base_commit"],
            "files": prepared,
            "report_sha256": hashlib.sha256(raw).hexdigest(),
            "report": json.loads(raw),
        }
    )
    _write_json(receipt_path(root, feature), receipt)
    if report.verdict == "BLOCKED":
        blocked = _trailing_blocked(rounds)
        outcome.reasons.append(
            LaneReason("review_blocked", f"{kind} round {blocked} of {MAX_BLOCKED_ROUNDS} BLOCKED")
        )
    return outcome


def required_kinds(lane: Lane, recorded: set[str]) -> list[str]:
    """Return the kinds whose latest round must pass for ``lane``.

    The full lane needs separate review and audit reports; the light lane accepts one
    combined report, or separate review and audit reports when both were recorded.
    """
    if lane == "full":
        return ["review", "audit"]
    if "combined" not in recorded and {"review", "audit"} <= recorded:
        return ["review", "audit"]
    return ["combined"]


# @spec FR-006: Current PASS for every required kind
#   — .specs/features/086-risk-proportional-delivery/spec.md#fr-006
def verify_review(
    root: Path, feature: str, lane: Lane, receipt: Path | None = None
) -> ReviewOutcome:
    """Check that every required kind passed and the diff is unchanged since."""
    path = receipt or receipt_path(root, feature)
    outcome = ReviewOutcome(feature, receipt_path=str(path))
    data = _read_json(path)
    if data is None or data.get("feature") != feature:
        outcome.reasons.append(LaneReason("no_receipt", str(path)))
        outcome.verdict = "MISSING"
        return outcome
    kinds = cast(dict[str, dict[str, Any]], data.get("kinds") or {})
    recorded = {k for k, v in kinds.items() if v.get("rounds")}
    for kind in required_kinds(lane, recorded):
        rounds = cast(list[dict[str, Any]], (kinds.get(kind) or {}).get("rounds") or [])
        if not rounds:
            outcome.reasons.append(LaneReason(f"kind_missing:{kind}", f"no {kind} report"))
            continue
        latest = rounds[-1]
        if latest.get("verdict") != "PASS":
            outcome.reasons.append(LaneReason(f"latest_round_blocked:{kind}", "latest is BLOCKED"))
            continue
        try:
            now = current_scope(root, str(latest.get("base_commit")))
        except DiffUnavailableError as exc:
            outcome.reasons.append(LaneReason("diff_unavailable", str(exc)))
            continue
        files = cast(dict[str, str], latest.get("files") or {})
        if now != files:
            changed = sorted(p for p in set(now) | set(files) if now.get(p) != files.get(p))
            outcome.reasons.append(LaneReason("scope_changed", f"{kind}: {', '.join(changed)}"))
    outcome.verdict = "BLOCKED" if outcome.reasons else "PASS"
    return outcome
