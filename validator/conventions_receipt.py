# LiveSpec traceability anchors
# @spec(FR-004)

"""Conventions verification receipt oracle."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

from .conventions_ast.taxonomy import taxonomy_fields
from .conventions_gate import GateResult
from .conventions_gates import gates_path
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
    ast_mode: str | None = None
    ast_backend: dict[str, object] | None = None
    ast_catalogs_sha256: str | None = None
    ast_observations: tuple[dict[str, object], ...] = ()
    ast_would_fail_count: int | None = None


# @spec FR-012: v2 AST receipt fields
#   .specs/features/072-conventions-ast-rule-engine/spec.md#fr-012
def write_conventions_receipt(
    *,
    project_root: Path,
    feature_slug: str,
    run_id: str,
    result: GateResult,
    gates_path: Path,
) -> Path:
    """Write a conventions receipt and return its path."""
    ast_summary = result.ast_summary
    payload = _base_receipt_payload(feature_slug, run_id, result, gates_path)
    if ast_summary is not None:
        payload.update(_ast_receipt_fields(ast_summary))
    else:
        payload.update(_receipt_taxonomy_fields(project_root))
    payload["receipt_hash"] = receipt_payload_hash(payload)
    output_dir = project_root / ".specs" / "conventions" / "runs" / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = output_dir / "receipt.json"
    receipt_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    return receipt_path


def _receipt_taxonomy_fields(project_root: Path) -> dict[str, object]:
    fields = taxonomy_fields(project_root)
    return {
        key: fields[key]
        for key in (
            "advisory_rules",
            "unsupported_rules",
            "source_manifest",
            "rule_decision_manifest",
        )
        if key in fields
    }


def _base_receipt_payload(
    feature_slug: str,
    run_id: str,
    result: GateResult,
    gates_path: Path,
) -> dict[str, object]:
    return {
        "schema_version": "2" if result.ast_summary is not None else RECEIPT_SCHEMA_VERSION,
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


def verify_conventions_receipt(
    receipt_path: Path,
    *,
    project_root: Path,
    expected_feature_slug: str | None = None,
) -> ConventionsReceipt:
    """Verify a conventions receipt by checking hashes and verdict coherence."""
    receipt_abs = _resolve_within_project(project_root, receipt_path)
    payload = _read_receipt_payload(receipt_abs)
    if payload.get("oracle") != ORACLE_NAME:
        raise ConventionsReceiptError("oracle_mismatch")
    schema_version = _string_field(payload, "schema_version")
    if schema_version not in {RECEIPT_SCHEMA_VERSION, "2"}:
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
    ast_mode: str | None = None
    ast_backend: dict[str, object] | None = None
    ast_catalogs_sha256: str | None = None
    ast_observations: tuple[dict[str, object], ...] = ()
    ast_would_fail_count: int | None = None
    if schema_version == "2":
        ast_fields = _verified_v2_ast_fields(payload, violations)
        ast_mode = ast_fields.ast_mode
        ast_backend = ast_fields.ast_backend
        ast_catalogs_sha256 = ast_fields.ast_catalogs_sha256
        ast_observations = ast_fields.ast_observations
        ast_would_fail_count = ast_fields.ast_would_fail_count
    else:
        _reject_ast_fields_in_v1(payload, violations)
    _check_current_gates_hash(project_root, payload)
    if payload.get("receipt_hash") != receipt_payload_hash(payload):
        raise ConventionsReceiptError("receipt_hash_mismatch")
    return ConventionsReceipt(
        schema_version=schema_version,
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
        ast_mode=ast_mode,
        ast_backend=ast_backend,
        ast_catalogs_sha256=ast_catalogs_sha256,
        ast_observations=ast_observations,
        ast_would_fail_count=ast_would_fail_count,
    )


def _read_receipt_payload(receipt_abs: Path) -> dict[str, Any]:
    try:
        raw: object = json.loads(receipt_abs.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConventionsReceiptError(f"receipt_unreadable:{receipt_abs}") from exc
    if not isinstance(raw, dict):
        raise ConventionsReceiptError("receipt_root_must_be_object")
    return cast(dict[str, Any], raw)


@dataclass(frozen=True)
class _VerifiedAstFields:
    ast_mode: str
    ast_backend: dict[str, object]
    ast_catalogs_sha256: str
    ast_observations: tuple[dict[str, object], ...]
    ast_would_fail_count: int


def _ast_receipt_fields(ast_summary: dict[str, object]) -> dict[str, object]:
    fields: dict[str, object] = {
        "ast_mode": ast_summary["ast_mode"],
        "ast_backend": ast_summary["ast_backend"],
        "ast_catalogs_sha256": ast_summary["ast_catalogs_sha256"],
        "ast_observations": ast_summary["ast_observations"],
        "ast_would_fail_count": ast_summary["ast_would_fail_count"],
    }
    # Support-class taxonomy (advisory/unsupported) — declares catalogued-but-not-
    # blocking domains so the receipt cannot read as "fully enforced" (C009).
    for key in (
        "advisory_rules",
        "unsupported_rules",
        "source_manifest",
        "rule_decision_manifest",
    ):
        if key in ast_summary:
            fields[key] = ast_summary[key]
    return fields


def _verified_v2_ast_fields(
    payload: dict[str, Any],
    violations: list[object],
) -> _VerifiedAstFields:
    ast_mode = _validate_v2_ast_fields(payload, violations)
    return _VerifiedAstFields(
        ast_mode=ast_mode,
        ast_backend=cast(dict[str, object], payload["ast_backend"]),
        ast_catalogs_sha256=_string_field(payload, "ast_catalogs_sha256"),
        ast_observations=tuple(cast(list[dict[str, object]], payload["ast_observations"])),
        ast_would_fail_count=_int_field(payload, "ast_would_fail_count"),
    )


def _validate_v2_ast_fields(payload: dict[str, Any], violations: list[object]) -> str:
    ast_mode = _string_field(payload, "ast_mode")
    if ast_mode not in {"off", "observe", "enforce"}:
        raise ConventionsReceiptError("field_invalid:ast_mode")
    ast_backend = payload.get("ast_backend")
    if not isinstance(ast_backend, dict):
        raise ConventionsReceiptError("field_invalid:ast_backend")
    backend_status = ast_backend.get("status")
    if backend_status not in {"available", "unavailable", "error", "skipped"}:
        raise ConventionsReceiptError("field_invalid:ast_backend.status")
    catalogs_sha = _string_field(payload, "ast_catalogs_sha256")
    if len(catalogs_sha) != 64 or any(char not in "0123456789abcdef" for char in catalogs_sha):
        raise ConventionsReceiptError("field_invalid:ast_catalogs_sha256")
    observations = _list_field(payload, "ast_observations")
    if any(not isinstance(item, dict) for item in observations):
        raise ConventionsReceiptError("field_invalid:ast_observations")
    would_fail_count = _int_field(payload, "ast_would_fail_count")
    if would_fail_count < 0:
        raise ConventionsReceiptError("field_invalid:ast_would_fail_count")
    if ast_mode != "enforce" and any(_violation_source(item) == "ast" for item in violations):
        suffix = "observe" if ast_mode == "observe" else ast_mode
        raise ConventionsReceiptError(f"ast_violation_in_{suffix}")
    return ast_mode


def _reject_ast_fields_in_v1(payload: dict[str, Any], violations: list[object]) -> None:
    ast_keys = {
        "ast_mode",
        "ast_backend",
        "ast_catalogs_sha256",
        "ast_observations",
        "ast_would_fail_count",
    }
    present = sorted(key for key in ast_keys if key in payload)
    if present:
        raise ConventionsReceiptError(f"ast_fields_in_v1:{','.join(present)}")
    if any(_violation_source(item) == "ast" for item in violations):
        raise ConventionsReceiptError("ast_violation_in_v1")


def _violation_source(item: object) -> object:
    if isinstance(item, dict):
        return item.get("source")
    return None


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


def _check_current_gates_hash(project_root: Path, payload: dict[str, Any]) -> None:
    current_gates = gates_path(project_root)
    try:
        current_sha = sha256_file(current_gates)
    except OSError as exc:
        raise ConventionsReceiptError("gates_file_unreadable") from exc
    if _string_field(payload, "gates_sha256") != current_sha:
        raise ConventionsReceiptError("gates_sha256_mismatch")


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


def _int_field(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConventionsReceiptError(f"field_invalid:{key}")
    return value
