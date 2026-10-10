"""Canonical JSON helpers shared by goal compilation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import goal_contracts as _contracts

__all__ = ["_canonical_json", "_canonical_rules", "_stable_path"]


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _canonical_rules(rules: list[_contracts.Rule]) -> list[dict[str, Any]]:
    return [{"verb": rule.verb, "kind": rule.kind, "payload": rule.payload} for rule in rules]


def _stable_path(path: Path, *, project_root: Path, livespec_root: Path) -> str:
    for root in (project_root, livespec_root):
        try:
            return path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            continue
    return path.as_posix()
