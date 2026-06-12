# LiveSpec traceability anchors
# @spec(FR-004)

"""Conventions verification receipt oracle."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

from .conventions_gate import GateResult
from .visual_evidence import receipt_payload_hash, sha256_file

ORACLE_NAME = "livespec-conventions-gate"
ORACLE_VERSION = "1"
RECEIPT_SCHEMA_VERSION = "1"

ReceiptVerdict = Literal["PASS", "FAIL", "BLOCKED"]


class ConventionsReceiptError(ValueError):
    """Raised when a conventions receipt is invalid."""


@dataclass(frozen=True)
class ConventionsReceipt:
    """Verified conventions receipt payload."""

    schema_version: str
    oracle: str
    oracle_version: str
    feature_slug: str
    run_id: str
    verdict: ReceiptVerdict
    gates_sha256: str
    violations: tuple[dict[str, object], ...]
    blockers: tuple[dict[str, str], ...]
    receipt_hash: str
    path: Path


def write_conventions_receipt(
    *,
    project_root: Path,
    feature_slug: str,
    run_id: str,
    result: GateResult,
    gates_path: Path,
) -> Path:
    """Write a conventions receipt and return its path."""
    payload: dict[str, object] = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "oracle": ORACLE_NAME,
        "oracle_version": ORACLE_VERSION,
        "feature_slug": feature_slug,
        "run_id": run_id,
        "verdict": result.verdict.value,
        "gates_sha256": sha256_file(gates_path),
        "violations": [violation.to_dict() for violation in result.violations],
        "blockers": [blocker.to_dict() for blocker in result.blockers],
        "created_at": datetime.now(UTC).isoformat(),
    }
    payload["receipt_hash"] = receipt_payload_hash(payload)
    output_dir = project_root / ".specs" / "conventions" / "runs" / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = output_dir / "receipt.json"
    receipt_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    return receipt_path


def verify_conventions_receipt(
    receipt_path: Path,
    *,
    project_root: Path,
    expected_feature_slug: str | None = None,
) -> ConventionsReceipt:
    """Verify a conventions receipt by checking hashes and verdict coherence."""
    receipt_abs = _resolve_within_project(project_root, receipt_path)
    try:
        raw: object = json.loads(receipt_abs.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConventionsReceiptError(f"receipt_unreadable:{receipt_abs}") from exc
    if not isinstance(raw, dict):
        raise ConventionsReceiptError("receipt_root_must_be_object")
    payload = cast(dict[str, Any], raw)
    if payload.get("oracle") != ORACLE_NAME:
        raise ConventionsReceiptError("oracle_mismatch")
    if payload.get("schema_version") != RECEIPT_SCHEMA_VERSION:
        raise ConventionsReceiptError("schema_version_mismatch")
    feature_slug = _string_field(payload, "feature_slug")
    if expected_feature_slug is not None and feature_slug != expected_feature_slug:
        raise ConventionsReceiptError("feature_slug_mismatch")
    verdict = _string_field(payload, "verdict")
    if verdict not in ("PASS", "FAIL", "BLOCKED"):
        raise ConventionsReceiptError("verdict_invalid")
    violations = _list_field(payload, "violations")
    blockers = _list_field(payload, "blockers")
    _check_verdict_consistency(cast(ReceiptVerdict, verdict), violations, blockers)
    if payload.get("receipt_hash") != receipt_payload_hash(payload):
        raise ConventionsReceiptError("receipt_hash_mismatch")
    return ConventionsReceipt(
        schema_version=str(payload["schema_version"]),
        oracle=str(payload["oracle"]),
        oracle_version=str(payload.get("oracle_version", "")),
        feature_slug=feature_slug,
        run_id=_string_field(payload, "run_id"),
        verdict=cast(ReceiptVerdict, verdict),
        gates_sha256=_string_field(payload, "gates_sha256"),
        violations=tuple(cast(list[dict[str, object]], violations)),
        blockers=tuple(cast(list[dict[str, str]], blockers)),
        receipt_hash=_string_field(payload, "receipt_hash"),
        path=receipt_abs,
    )


def _check_verdict_consistency(
    verdict: ReceiptVerdict,
    violations: list[object],
    blockers: list[object],
) -> None:
    has_error = any(
        isinstance(item, dict) and item.get("severity") == "error" for item in violations
    )
    if verdict == "PASS" and (has_error or blockers):
        raise ConventionsReceiptError("verdict_inconsistent")
    if verdict == "FAIL" and not has_error:
        raise ConventionsReceiptError("verdict_inconsistent")
    if verdict == "BLOCKED" and not blockers:
        raise ConventionsReceiptError("verdict_inconsistent")


def _resolve_within_project(project_root: Path, path: Path) -> Path:
    root = project_root.resolve()
    resolved = path.resolve() if path.is_absolute() else (project_root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ConventionsReceiptError(f"path_outside_project:{path}") from exc
    return resolved


def _string_field(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ConventionsReceiptError(f"field_invalid:{key}")
    return value


def _list_field(payload: dict[str, Any], key: str) -> list[object]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ConventionsReceiptError(f"field_invalid:{key}")
    return value
