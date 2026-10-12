# LiveSpec traceability anchors
# @spec(FR-037)
# @spec(FR-038)
# @spec(FR-039)

"""Verify agent-written receipts for compiled LLM visual contracts.

The agent (``$spec-journey``) examines each capture against its compiled
contract and writes ``.specs/journeys/<id>/visual-receipts/<check>.json``.
This module never calls a model: it checks receipt presence, strict schema,
contract and capture hashes, privacy constraints and the verdict.
"""

# @spec FR-037: Strict JSON verdict (pass/fail, criteria, explanation, confidence, boxes)
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#fr-037
# @spec FR-038: Advisory by default, blocking only when the check is blocking
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#fr-038
# @spec FR-039: llm_allowed, local_only and retention are enforced on receipts
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#fr-039

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .paths import journey_source_root, relative_to_project, visual_receipts_dir

_SHA256_RE = r"^[0-9a-f]{64}$"
Status = Literal["pass", "advisory_fail", "fail", "missing", "invalid", "stale", "disabled"]
_ERROR_STATUSES = frozenset({"fail", "missing", "invalid", "stale", "disabled"})


class BoundingBox(BaseModel):
    """Region of the capture the verdict refers to."""

    model_config = ConfigDict(extra="forbid")

    x: float = Field(ge=0)
    y: float = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    label: str | None = None


class Evaluator(BaseModel):
    """Who evaluated the capture and where the model ran."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    locality: Literal["local", "remote"]


class VisualReceipt(BaseModel):
    """Strict schema of one agent-written LLM visual evaluation receipt."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    journey_id: str = Field(min_length=1)
    check_id: str = Field(min_length=1)
    contract_sha256: str = Field(pattern=_SHA256_RE)
    capture_path: str = Field(min_length=1)
    capture_sha256: str = Field(pattern=_SHA256_RE)
    verdict: Literal["pass", "fail"]
    confidence: float = Field(ge=0, le=1)
    criteria_passed: list[str]
    criteria_failed: list[str]
    explanation: str = Field(min_length=1, max_length=500)
    bounding_boxes: list[BoundingBox] = Field(default_factory=lambda: cast(list[BoundingBox], []))
    evaluator: Evaluator
    evaluated_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")

    @model_validator(mode="after")
    def _verdict_matches_criteria(self) -> VisualReceipt:
        """A pass verdict cannot list failed criteria; a fail must name one."""
        if self.verdict == "pass" and self.criteria_failed:
            raise ValueError("verdict pass with non-empty criteria_failed")
        if self.verdict == "fail" and not self.criteria_failed:
            raise ValueError("verdict fail requires at least one criteria_failed entry")
        return self


@dataclass(frozen=True)
class VisualCheckOutcome:
    """Verification result for one compiled LLM visual contract."""

    journey_id: str
    check_id: str
    status: Status
    contract_path: str
    receipt_path: str
    message: str = ""


@dataclass
class VisualVerification:
    """All outcomes; ``error_count`` drives the CLI exit code."""

    outcomes: list[VisualCheckOutcome] = field(default_factory=lambda: [])

    @property
    def error_count(self) -> int:
        """Return the number of outcomes that must block."""
        return sum(1 for outcome in self.outcomes if outcome.status in _ERROR_STATUSES)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _contract_paths(project_root: Path, journey: str | None) -> list[Path]:
    root = journey_source_root(project_root)
    pattern = f"{journey or '*'}/compiled/visual-contracts/*.json"
    return sorted(path for path in root.glob(pattern) if path.is_file())


def _confined(project_root: Path, relative: str) -> Path | None:
    """Resolve a project-relative capture path, refusing escapes and absolute paths."""
    if Path(relative).is_absolute() or re.search(r"(^|/)\.\.(/|$)", relative):
        return None
    candidate = (project_root / relative).resolve()
    try:
        candidate.relative_to(project_root.resolve())
    except ValueError:
        return None
    return candidate


def _verify_one(project_root: Path, contract_path: Path) -> VisualCheckOutcome:
    try:
        loaded: object = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        loaded = None
    contract = cast(dict[str, Any], loaded) if isinstance(loaded, dict) else {}
    journey_id = str(contract.get("journey_id", contract_path.parents[2].name))
    check_id = str(contract.get("check_id", contract_path.stem))
    receipt_path = visual_receipts_dir(project_root, journey_id) / contract_path.name

    def outcome(status: Status, message: str = "") -> VisualCheckOutcome:
        return VisualCheckOutcome(
            journey_id,
            check_id,
            status,
            relative_to_project(project_root, contract_path),
            relative_to_project(project_root, receipt_path),
            message,
        )

    if not contract:
        return outcome("invalid", "compiled contract is not a JSON object; recompile the journey")
    privacy = cast(dict[str, Any], contract.get("privacy") or {})
    if not privacy.get("llm_allowed", False):
        return outcome("disabled", "privacy.llm_allowed is false; LLM evaluation is not allowed")
    if not receipt_path.is_file():
        return outcome("missing", "no receipt; evaluate the capture and write the receipt")
    try:
        receipt = VisualReceipt.model_validate_json(receipt_path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        return outcome("invalid", f"receipt schema: {exc}".splitlines()[0])
    if (receipt.journey_id, receipt.check_id) != (journey_id, check_id):
        return outcome("invalid", "receipt journey_id/check_id do not match the contract")
    if receipt.contract_sha256 != _sha256(contract_path):
        return outcome("stale", "contract changed since evaluation; re-evaluate")
    if privacy.get("local_only") and receipt.evaluator.locality != "local":
        return outcome("invalid", "privacy.local_only requires a local evaluator")
    capture = _confined(project_root, receipt.capture_path)
    if capture is None:
        return outcome("invalid", "capture_path must be project-relative and inside the project")
    if capture.is_file():
        if _sha256(capture) != receipt.capture_sha256:
            return outcome("stale", "capture changed since evaluation; re-evaluate")
    elif privacy.get("retention", "none") != "none":
        return outcome("invalid", f"capture missing: {receipt.capture_path}")
    if receipt.verdict == "pass":
        return outcome("pass")
    if contract.get("blocking"):
        return outcome("fail", "; ".join(receipt.criteria_failed))
    return outcome("advisory_fail", "; ".join(receipt.criteria_failed))


def verify_visual_receipts(project_root: Path, journey: str | None = None) -> VisualVerification:
    """Verify every compiled LLM visual contract (optionally for one journey).

    Args:
        project_root: Project root containing ``.specs/journeys``.
        journey: Restrict verification to one journey ID.

    Returns:
        One outcome per contract. Missing, invalid, stale, disabled and blocking
        failures count as errors; non-blocking failures are advisory.
    """
    verification = VisualVerification()
    for contract_path in _contract_paths(project_root, journey):
        verification.outcomes.append(_verify_one(project_root, contract_path))
    return verification


__all__ = [
    "VisualCheckOutcome",
    "VisualReceipt",
    "VisualVerification",
    "verify_visual_receipts",
]
