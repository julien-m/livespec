# LiveSpec traceability anchors
# @spec(FR-002)

"""Linter JSON parsing for conventions verification."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal, cast

from .conventions_gates import GateCommand

LinterSeverity = Literal["warning", "error"]


@dataclass(frozen=True)
class LinterViolationPayload:
    """Normalized linter violation data."""

    rule_id: str
    path: str
    line: int
    severity: LinterSeverity
    message: str


def parse_linter_json(command: GateCommand, stdout: str) -> list[LinterViolationPayload]:
    """Parse supported linter JSON reporters into normalized violations."""
    if not stdout.strip():
        return []
    try:
        raw: object = json.loads(stdout)
    except json.JSONDecodeError:
        return []
    items = raw if isinstance(raw, list) else [raw]
    violations: list[LinterViolationPayload] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        payload = cast(dict[str, Any], item)
        messages = payload.get("messages")
        if isinstance(messages, list):
            violations.extend(_eslint_messages(command, _path_from(payload), messages))
        elif _is_ruff_payload(payload):
            violations.append(_ruff_violation(command, payload))
    return violations


def _eslint_messages(
    command: GateCommand,
    path: str,
    messages: list[object],
) -> list[LinterViolationPayload]:
    violations: list[LinterViolationPayload] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        payload = cast(dict[str, Any], message)
        severity = "error" if int(payload.get("severity", 2)) >= 2 else "warning"
        violations.append(
            LinterViolationPayload(
                rule_id=f"linter.{command.id}",
                path=path,
                line=int(payload.get("line", 1)),
                severity=cast(LinterSeverity, severity),
                message=str(payload.get("message", "linter violation")),
            )
        )
    return violations


def _ruff_violation(
    command: GateCommand,
    payload: dict[str, Any],
) -> LinterViolationPayload:
    location = payload.get("location")
    row = location.get("row") if isinstance(location, dict) else payload.get("line", 1)
    code = str(payload.get("code") or "").strip()
    message = str(payload.get("message") or "linter violation")
    return LinterViolationPayload(
        rule_id=f"linter.{command.id}",
        path=_path_from(payload),
        line=int(row or 1),
        severity="error",
        message=f"{code}: {message}" if code else message,
    )


def _is_ruff_payload(payload: dict[str, Any]) -> bool:
    return "filename" in payload and "location" in payload and "message" in payload


def _path_from(payload: dict[str, Any]) -> str:
    return str(payload.get("filePath") or payload.get("filename") or payload.get("path") or ".")
