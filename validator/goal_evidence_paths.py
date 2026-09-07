"""Confine bootstrap task evidence artifacts to the immutable project root."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from .goal_json import JsonObject, JsonValue, copy_json_object

_PATH_KEYS = frozenset(
    {
        "artifact",
        "artifact_path",
        "artifacts",
        "file",
        "files",
        "path",
        "paths",
        "penflow_artifact_path",
        "report_path",
        "run_artifact_path",
    }
)
_CONTROL_PATH_KEYS = frozenset(
    {
        "child_contract_file",
        "child_state_file",
        "contract_file",
        "state_file",
        "stderr_file",
        "stdout_file",
    }
)


class GoalEvidencePathError(Exception):
    """Report bootstrap evidence that is broken or outside its bound root."""


# @spec FR-004: Resolve proof from persisted root, FR-011: Confine evidence
#   — .specs/features/076-spec-init-goal-bootstrap/spec.md#fr-004
def confine_bootstrap_evidence(evidence: Mapping[str, JsonValue], project_root: Path) -> JsonObject:
    """Validate every project artifact path in a bootstrap evidence payload.

    Args:
        evidence: Parsed inline or external-file evidence object.
        project_root: Immutable canonical render-time root.

    Returns:
        A deep copy after every project path is proven contained.

    Raises:
        GoalEvidencePathError: If a project path is broken or escapes the root.
    """
    root = project_root.resolve(strict=True)
    isolated = copy_json_object(dict(evidence))
    if isolated is None:
        raise GoalEvidencePathError("evidence contains a non-JSON value")
    _walk_evidence(isolated, root)
    return isolated


def _walk_evidence(value: object, root: Path, key: str | None = None) -> None:
    if isinstance(value, dict):
        for nested_key, nested_value in value.items():
            if isinstance(nested_key, str):
                _walk_evidence(nested_value, root, nested_key)
        return
    if isinstance(value, list):
        for item in value:
            _walk_evidence(item, root, key)
        return
    if isinstance(value, str) and key is not None and _is_project_path_key(key):
        _require_contained_path(value, root)


def _is_project_path_key(key: str) -> bool:
    if key in _CONTROL_PATH_KEYS:
        return False
    return key in _PATH_KEYS or key.endswith("_artifact_path") or key.endswith("_receipt_path")


def _require_contained_path(path_value: str, root: Path) -> None:
    submitted = Path(path_value)
    candidate = submitted if submitted.is_absolute() else root / submitted
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise GoalEvidencePathError(f"evidence path is unreadable: {path_value}") from exc
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise GoalEvidencePathError(f"evidence path escapes project_root: {path_value}") from exc


__all__ = ["GoalEvidencePathError", "confine_bootstrap_evidence"]
