# LiveSpec traceability anchors
# @spec(FR-002)
# @spec(FR-003)
# @spec(FR-006)

"""Finalize receipt primitives: canonical hashing, write, and verification.

Private helper module for :mod:`validator.finalize` (kept separate to honor
the 300-line constitution cap — see plan.md Constitution Check deviation
note). The public API is re-exported from ``validator.finalize``; import
from there, not from here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

# Import, do not clone: the canonical-JSON hashing and file hashing primitives
# are shared with the visual evidence oracle (plan.md Step 2 mandate).
from .visual_evidence import VisualReceiptError, receipt_payload_hash, sha256_file

FINALIZE_ORACLE_NAME = "livespec-finalize-evidence"
FINALIZE_ORACLE_VERSION = "1"
FINALIZE_RECEIPT_SCHEMA_VERSION = "1"
MARKER_TEMPLATE = "<!-- finalize:{command}:{date}:{hash8} -->"

FinalizeOutcome = Literal["applied", "already_finalized", "verified", "BLOCKED"]
FinalizeVerdict = Literal["PASS", "FAIL", "BLOCKED"]

_ALLOWED_OUTCOMES: tuple[str, ...] = ("applied", "already_finalized", "verified", "BLOCKED")
_ALLOWED_VERDICTS: tuple[str, ...] = ("PASS", "FAIL", "BLOCKED")


class FinalizeError(Exception):
    """Base error for finalize apply/verify failures.

    Attributes:
        subtype: Canonical BLOCKED subtype (``policy_blocked`` /
            ``state_invalid``) used by the CLI boundary to render the
            anti-drift BLOCKED line.
    """

    def __init__(
        self,
        message: str,
        *,
        subtype: str = "state_invalid",
        receipt_path: Path | None = None,
    ) -> None:
        super().__init__(message)
        self.subtype = subtype
        # Receipt written before the failure (e.g. a BLOCKED partial-apply
        # receipt, Edge Case 5); None when the failure precedes any write.
        self.receipt_path = receipt_path


class FinalizeReceiptError(ValueError):
    """Raised when a finalize receipt is missing, malformed, or stale."""


@dataclass(frozen=True)
class FinalizeFileEntry:
    """One registry file recorded in a finalize receipt."""

    path: str
    sha256: str


@dataclass(frozen=True)
class FinalizeViolation:
    """One coherence/marker violation recorded in a finalize receipt."""

    rule_id: str
    message: str


@dataclass(frozen=True)
class FinalizeReceipt:
    """Verified finalize evidence receipt produced by the LiveSpec oracle."""

    schema_version: str
    oracle: str
    oracle_version: str
    feature_slug: str
    command: str
    outcome: FinalizeOutcome
    verdict: FinalizeVerdict
    files: tuple[FinalizeFileEntry, ...]
    violations: tuple[FinalizeViolation, ...]
    payload_hash: str
    created_at: str
    receipt_hash: str
    path: Path | None = None


def compute_payload_hash(payload: dict[str, object]) -> str:
    """Return the full sha256 of the canonical date-free apply payload.

    Delegates to :func:`validator.visual_evidence.receipt_payload_hash` so the
    canonical-JSON discipline (sorted keys, compact separators, UTF-8) is
    identical to the visual oracle (FR-003).
    """
    return receipt_payload_hash(payload)


def compute_hash8(payload: dict[str, object]) -> str:
    """Return the 8-hex marker identity derived from the canonical payload.

    The marker identity is ``<cmd>`` + ``<hash8>`` (FR-002); the marker's
    date segment is informational only.
    """
    return compute_payload_hash(payload)[:8]


def receipt_output_dir(project_root: Path, feature_slug: str, run_id: str) -> Path:
    """Return the receipt directory (same containment as visual evidence)."""
    return project_root / ".specs" / "features" / feature_slug / "run" / run_id / "finalize"


def write_receipt(
    *,
    project_root: Path,
    feature_slug: str,
    command: str,
    run_id: str,
    payload_hash: str,
    outcome: FinalizeOutcome,
    verdict: FinalizeVerdict,
    files: list[Path],
    violations: list[FinalizeViolation],
) -> Path:
    """Write a finalize receipt JSON and return its path.

    Args:
        project_root: Root used to normalize recorded file paths.
        feature_slug: Feature directory slug.
        command: Finalizing LiveSpec command (e.g. ``spec-specify``).
        run_id: Run identifier used for the receipt directory.
        payload_hash: Full sha256 of the canonical apply payload.
        outcome: ``applied`` / ``already_finalized`` / ``verified`` / ``BLOCKED``.
        verdict: ``PASS`` / ``FAIL`` / ``BLOCKED``.
        files: Registry files whose sha256 is recorded.
        violations: Violations recorded on FAIL verdicts.

    Returns:
        Path to the written ``receipt.json``.
    """
    payload: dict[str, object] = {
        "schema_version": FINALIZE_RECEIPT_SCHEMA_VERSION,
        "oracle": FINALIZE_ORACLE_NAME,
        "oracle_version": FINALIZE_ORACLE_VERSION,
        "feature_slug": feature_slug,
        "command": command,
        "outcome": outcome,
        "verdict": verdict,
        "files": [
            {"path": _project_relative(project_root, path), "sha256": _file_sha256(path)}
            for path in files
        ],
        "violations": [
            {"rule_id": violation.rule_id, "message": violation.message} for violation in violations
        ],
        "payload_hash": payload_hash,
        "created_at": datetime.now(UTC).isoformat(),
    }
    payload["receipt_hash"] = receipt_payload_hash(payload)
    output_dir = receipt_output_dir(project_root, feature_slug, run_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = output_dir / "receipt.json"
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    receipt_path.write_text(text, encoding="utf-8")
    return receipt_path


def verify_finalize_receipt(
    receipt_path: Path,
    *,
    project_root: Path,
    expected_feature_slug: str | None = None,
    expected_command: str | None = None,
) -> FinalizeReceipt:
    """Verify a finalize receipt by re-checking hashes and consistency.

    Clone of the ``verify_visual_receipt`` pattern (FR-006): containment
    check, JSON parse, oracle/schema match, expected feature/command match,
    on-disk sha256 re-verification of every recorded file, receipt-hash
    recomputation, and verdict consistency.

    Args:
        receipt_path: Path to the receipt JSON.
        project_root: Project root used for containment and path resolution.
        expected_feature_slug: When given, the receipt must match this slug.
        expected_command: When given, the receipt must match this command.

    Returns:
        A verified :class:`FinalizeReceipt`.

    Raises:
        FinalizeReceiptError: If the receipt is malformed, stale, outside the
            project, or not emitted by the finalize oracle.
    """
    receipt_abs = _resolve_within_project(project_root, receipt_path)
    try:
        raw: object = json.loads(receipt_abs.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FinalizeReceiptError(f"receipt_unreadable: {receipt_abs}") from exc
    if not isinstance(raw, dict):
        raise FinalizeReceiptError("receipt_root_must_be_object")
    payload = cast(dict[str, Any], raw)
    if payload.get("oracle") != FINALIZE_ORACLE_NAME:
        raise FinalizeReceiptError("oracle_mismatch")
    if payload.get("schema_version") != FINALIZE_RECEIPT_SCHEMA_VERSION:
        raise FinalizeReceiptError("schema_version_mismatch")
    feature_slug = _string_field(payload, "feature_slug")
    command = _string_field(payload, "command")
    if expected_feature_slug is not None and feature_slug != expected_feature_slug:
        raise FinalizeReceiptError("feature_slug_mismatch")
    if expected_command is not None and command != expected_command:
        raise FinalizeReceiptError("command_mismatch")
    outcome = _string_field(payload, "outcome")
    if outcome not in _ALLOWED_OUTCOMES:
        raise FinalizeReceiptError(f"outcome_invalid:{outcome}")
    verdict = _string_field(payload, "verdict")
    if verdict not in _ALLOWED_VERDICTS:
        raise FinalizeReceiptError(f"verdict_invalid:{verdict}")
    payload_hash = _string_field(payload, "payload_hash")
    if len(payload_hash) != 64:
        raise FinalizeReceiptError("payload_hash_invalid")
    files = _parse_files(payload)
    violations = _parse_violations(payload)
    for entry in files:
        file_abs = _resolve_within_project(project_root, Path(entry.path))
        if _file_sha256(file_abs) != entry.sha256:
            raise FinalizeReceiptError(f"file_sha256_mismatch:{entry.path}")
    expected_hash = str(payload.get("receipt_hash", ""))
    if expected_hash != receipt_payload_hash(payload):
        raise FinalizeReceiptError("receipt_hash_mismatch")
    _check_verdict_consistency(outcome, verdict, violations)
    return FinalizeReceipt(
        schema_version=str(payload["schema_version"]),
        oracle=str(payload["oracle"]),
        oracle_version=str(payload.get("oracle_version", "")),
        feature_slug=feature_slug,
        command=command,
        outcome=cast(FinalizeOutcome, outcome),
        verdict=cast(FinalizeVerdict, verdict),
        files=files,
        violations=violations,
        payload_hash=payload_hash,
        created_at=str(payload.get("created_at", "")),
        receipt_hash=expected_hash,
        path=receipt_abs,
    )


def _check_verdict_consistency(
    outcome: str,
    verdict: str,
    violations: tuple[FinalizeViolation, ...],
) -> None:
    # Business rule: the verdict must be derivable from the recorded state —
    # PASS forbids violations, FAIL requires them, BLOCKED pairs with the
    # BLOCKED outcome. Anything else is a forged or hand-edited receipt.
    if verdict == "PASS" and (violations or outcome == "BLOCKED"):
        raise FinalizeReceiptError("verdict_inconsistent")
    if verdict == "FAIL" and not violations:
        raise FinalizeReceiptError("verdict_inconsistent")
    if (verdict == "BLOCKED") != (outcome == "BLOCKED"):
        raise FinalizeReceiptError("verdict_inconsistent")


def _parse_files(payload: dict[str, Any]) -> tuple[FinalizeFileEntry, ...]:
    raw: object = payload.get("files")
    if not isinstance(raw, list) or not raw:
        raise FinalizeReceiptError("files_missing")
    entries: list[FinalizeFileEntry] = []
    for item in cast(list[object], raw):
        if not isinstance(item, dict):
            raise FinalizeReceiptError("file_entry_must_be_object")
        entry = cast(dict[str, Any], item)
        entries.append(
            FinalizeFileEntry(
                path=_string_field(entry, "path"),
                sha256=_string_field(entry, "sha256"),
            )
        )
    return tuple(entries)


def _parse_violations(payload: dict[str, Any]) -> tuple[FinalizeViolation, ...]:
    raw: object = payload.get("violations", [])
    if not isinstance(raw, list):
        raise FinalizeReceiptError("violations_must_be_list")
    violations: list[FinalizeViolation] = []
    for item in cast(list[object], raw):
        if not isinstance(item, dict):
            raise FinalizeReceiptError("violation_must_be_object")
        violation = cast(dict[str, Any], item)
        violations.append(
            FinalizeViolation(
                rule_id=_string_field(violation, "rule_id"),
                message=_string_field(violation, "message"),
            )
        )
    return tuple(violations)


def _string_field(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise FinalizeReceiptError(f"field_invalid:{key}")
    return value


def _file_sha256(path: Path) -> str:
    try:
        return sha256_file(path)
    except VisualReceiptError as exc:
        # Re-wrap: callers of the finalize oracle only catch finalize errors.
        raise FinalizeReceiptError(str(exc)) from exc


def _resolve_within_project(project_root: Path, path: Path) -> Path:
    root = project_root.resolve()
    resolved = path.resolve() if path.is_absolute() else (project_root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise FinalizeReceiptError(f"path_outside_project:{path}") from exc
    return resolved


def _project_relative(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError as exc:
        raise FinalizeReceiptError(f"path_outside_project:{path}") from exc
