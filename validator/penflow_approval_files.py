"""Bounded immutable files for consumer-owned Penflow review approvals."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .locks import write_with_hash_check

JsonObject = dict[str, Any]  # External versioned JSON, checked at model boundaries.
ARCHIVE = Path(".specs/penflow-approvals")
BASELINE = Path(".specs/penflow-requirements.json")


class PenflowApprovalError(ValueError):
    """The approved source selection cannot be established from current inputs."""


def digest(raw: bytes) -> str:
    """Return the SHA256 identity of the exact supplied bytes."""
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value: object) -> bytes:
    """Serialize deterministic JSON identities without non-finite values."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode()


def bounded(root: Path, path: str | Path) -> Path:
    """Resolve one explicit project-contained path; never search neighboring roots."""
    candidate = Path(path)
    resolved = (candidate if candidate.is_absolute() else root / candidate).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise PenflowApprovalError(f"approval_path_outside_project: {path}")
    return resolved


def file_ref(root: Path, path: Path) -> JsonObject:
    """Bind a project-contained file to its current raw bytes."""
    resolved = bounded(root, path)
    return {
        "path": str(resolved.relative_to(root.resolve())),
        "sha256": digest(resolved.read_bytes()),
    }


def read_ref(root: Path, reference: JsonObject) -> bytes:
    """Read exact referenced bytes and reject stale, absent or foreign files."""
    path = bounded(root, reference["path"])
    raw = path.read_bytes()
    if digest(raw) != reference["sha256"]:
        raise PenflowApprovalError(f"approval_reference_stale: {reference['path']}")
    return raw


def archive_bytes(root: Path, raw: bytes, *, prefix: str, suffix: str = ".json") -> JsonObject:
    """Persist immutable content-addressed bytes while the caller holds the project lock."""
    path = bounded(root, ARCHIVE / f"{prefix}-{digest(raw)}{suffix}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != raw:
            raise PenflowApprovalError(f"immutable_approval_archive_changed: {path}")
    else:
        write_with_hash_check(path, raw.decode("utf-8"))
    return file_ref(root, path)


def archive_json(root: Path, value: object, *, prefix: str) -> JsonObject:
    """Archive canonical JSON without replacing any previous approval."""
    return archive_bytes(root, json_bytes(value), prefix=prefix)


def load_object(raw: bytes) -> JsonObject:
    """Decode a versioned object, rejecting duplicate fields and nonfinite values."""

    def pairs(items: list[tuple[str, Any]]) -> JsonObject:
        result: JsonObject = {}
        for key, value in items:
            if key in result:
                raise PenflowApprovalError(f"duplicate_json_key: {key}")
            result[key] = value
        return result

    def invalid(value: str) -> None:
        raise PenflowApprovalError(f"nonfinite_json: {value}")

    def finite_float(value: str) -> float:
        parsed = float(value)
        if not math.isfinite(parsed):
            raise PenflowApprovalError(f"nonfinite_json: {value}")
        return parsed

    value = json.loads(
        raw, object_pairs_hook=pairs, parse_constant=invalid, parse_float=finite_float
    )
    if not isinstance(value, dict):
        raise PenflowApprovalError("approval_json_object_required")
    return value
