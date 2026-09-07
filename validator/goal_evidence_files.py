"""Goal evidence files responsibilities behind the public contract facade."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from . import goal_contracts as _contracts

__all__ = [
    "_any_evidence_path_exists",
    "_child_goal_artifact_exists",
    "_nonempty_str",
    "_path_exists",
    "_valid_child_goal_artifact",
]


def _nonempty_str(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _child_goal_artifact_exists(
    evidence: Mapping[str, object],
    keys: tuple[str, ...],
    suffix: str,
    artifact_kind: str,
) -> bool:
    expected_hash = evidence.get("child_goal_hash")
    if not isinstance(expected_hash, str) or not expected_hash.strip():
        return False
    for key in keys:
        value = evidence.get(key)
        values: list[object]
        if isinstance(value, str):
            values = [value]
        elif isinstance(value, list):
            values = cast(list[object], value)
        else:
            values = []
        for item in values:
            if isinstance(item, str) and _contracts._valid_child_goal_artifact(
                item, suffix, artifact_kind, expected_hash.strip()
            ):
                # One valid artifact path is enough to satisfy this evidence item.
                return True
    return False


def _valid_child_goal_artifact(
    path_value: str,
    suffix: str,
    artifact_kind: str,
    expected_hash: str,
) -> bool:
    path = Path(path_value)
    if not path.is_absolute() or not path.name.endswith(suffix):
        return False
    if path.parent.name != _contracts.CHILD_GOAL_ARTIFACT_ROOT_MARKER or not path.name.startswith(
        "goal-"
    ):
        return False
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        # Invalid or unreadable child goal artifacts cannot prove completion.
        return False
    if not isinstance(payload, dict) or payload.get("goal_hash") != expected_hash:
        return False
    if artifact_kind == "contract":
        return isinstance(payload.get("tasks"), list)
    if artifact_kind == "state":
        status = payload.get("status")
        return isinstance(status, str) and status.lower() in {"complete", "blocked"}
    return False


def _any_evidence_path_exists(
    evidence: dict[str, Any],
    keys: tuple[str, ...],
    project_root: Path | None,
) -> bool:
    for key in keys:
        value = evidence.get(key)
        if isinstance(value, str) and _contracts._path_exists(value, project_root):
            return True
        if isinstance(value, list):
            for item in cast(list[object], value):
                if isinstance(item, str) and _contracts._path_exists(item, project_root):
                    return True
    return False


def _path_exists(
    path_value: str,
    project_root: Path | None,
) -> bool:
    path = Path(path_value)
    if project_root is not None:
        root = project_root.resolve()
        resolved = path.resolve() if path.is_absolute() else (project_root / path).resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            return False
        return resolved.exists()
    return path.exists()
