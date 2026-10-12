"""Goal evidence files responsibilities behind the public contract facade."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from . import goal_contracts as _contracts

__all__ = [
    "_any_evidence_path_exists",
    "_path_exists",
]


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
