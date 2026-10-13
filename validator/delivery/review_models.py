"""Delivery review report models and evidence files (feature 086 FR-005)."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from .lane import DeliveryInputError, LaneReason

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


def feature_dir(root: Path, feature: str) -> Path:
    from ..identity import SLUG_REGEX

    directory = root / ".specs" / "features" / feature
    if not SLUG_REGEX.fullmatch(feature) or not (directory / "spec.md").is_file():
        raise DeliveryInputError(f"unknown feature {feature!r}")
    return directory


def scope_path(root: Path, feature: str) -> Path:
    """Return the prepared scope location of a feature."""
    return feature_dir(root, feature) / ".reviews" / "delivery-scope.json"


def receipt_path(root: Path, feature: str) -> Path:
    """Return the delivery review receipt location of a feature."""
    return feature_dir(root, feature) / ".reviews" / "delivery.json"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Atomically publish evidence inside the feature directory, never through a link."""
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise DeliveryInputError(f"refusing to write through a link: {parent}")
        if (parent / ".specs").is_dir():
            break
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".delivery-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_json(path: Path) -> dict[str, Any] | None:
    """Read a JSON object without following a final link; anything else is None."""
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "r", encoding="utf-8") as stream:
            data = json.loads(stream.read())
    except (OSError, ValueError):
        return None
    return cast(dict[str, Any], data) if isinstance(data, dict) else None


def report_reasons(report: DeliveryReport, scope_files: dict[str, str]) -> list[LaneReason]:
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
