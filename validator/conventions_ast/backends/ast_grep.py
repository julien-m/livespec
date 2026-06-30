# @spec FR-010: Backend absence mode behavior
#   .specs/features/072-conventions-ast-rule-engine/spec.md#fr-010

"""``ast-grep`` backend adapter for AST conventions."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, cast

from validator.conventions_ast.models import (
    AstBackendInfo,
    AstBackendResult,
    AstMatch,
    AstRule,
    AstSourceFile,
)


class AstGrepBackend:
    """Run ``sg`` as a detector backend with explicit args and timeouts."""

    def __init__(self, *, command: str = "sg", timeout_seconds: int = 10) -> None:
        self._command = command
        self._timeout_seconds = timeout_seconds

    def scan(
        self,
        *,
        rules: tuple[AstRule, ...],
        source_files: tuple[AstSourceFile, ...],
    ) -> AstBackendResult:
        """Scan source files with ast-grep and return normalized matches."""
        binary = shutil.which(self._command)
        if binary is None:
            return AstBackendResult(
                AstBackendInfo("ast-grep", self._command, "unavailable", message="sg not found"),
                (),
            )
        version_info = _version_info(binary, self._timeout_seconds)
        matches: list[AstMatch] = []
        for rule in rules:
            for source in source_files:
                if source.language != rule.language:
                    continue
                result = _scan_one(binary, self._timeout_seconds, rule, source)
                if result.info.status == "error":
                    return result
                matches.extend(result.matches)
        return AstBackendResult(version_info, tuple(matches))


def _version_info(binary: str, timeout_seconds: int) -> AstBackendInfo:
    try:
        completed = subprocess.run(
            [binary, "--version"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return AstBackendInfo("ast-grep", binary, "error", message=str(exc))
    version = completed.stdout.strip() or None
    return AstBackendInfo("ast-grep", binary, "available", version=version)


def _scan_one(
    binary: str,
    timeout_seconds: int,
    rule: AstRule,
    source: AstSourceFile,
) -> AstBackendResult:
    """Scan one source file with every pattern declared by the rule.

    A rule may carry multiple structural patterns (e.g. several syntactic forms
    of the same violation). All of them are evaluated; a match via any pattern
    counts. The first backend error short-circuits and is surfaced.
    """
    matches: list[AstMatch] = []
    for pattern in rule.patterns:
        result = _scan_one_pattern(binary, timeout_seconds, rule, source, pattern.value)
        if result.info.status == "error":
            return result
        matches.extend(result.matches)
    return AstBackendResult(AstBackendInfo("ast-grep", binary, "available"), tuple(matches))


def _scan_one_pattern(
    binary: str,
    timeout_seconds: int,
    rule: AstRule,
    source: AstSourceFile,
    pattern: str,
) -> AstBackendResult:
    try:
        # The backend contract is an executable plus explicit args; no shell
        # interpolation is used, so rule and path values cannot become command text.
        with tempfile.NamedTemporaryFile("w", suffix=".yml", encoding="utf-8") as rule_file:
            rule_file.write(pattern)
            rule_file.flush()
            completed = subprocess.run(
                [
                    binary,
                    "scan",
                    "--json",
                    "-r",
                    rule_file.name,
                    source.path.as_posix(),
                ],
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return AstBackendResult(
            AstBackendInfo("ast-grep", binary, "error", message=str(exc)),
            (),
        )
    if completed.returncode not in (0, 1):
        return AstBackendResult(
            AstBackendInfo("ast-grep", binary, "error", message=completed.stderr.strip()),
            (),
        )
    try:
        raw = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError as exc:
        return AstBackendResult(
            AstBackendInfo("ast-grep", binary, "error", message=f"malformed json: {exc}"),
            (),
        )
    return AstBackendResult(
        AstBackendInfo("ast-grep", binary, "available"),
        tuple(_matches_from_json(rule, source.path, raw)),
    )


def _matches_from_json(rule: AstRule, source_path: Path, raw: object) -> list[AstMatch]:
    if not isinstance(raw, list):
        return []
    matches: list[AstMatch] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        # ast-grep JSON is an untyped external boundary; shape-specific reads happen below.
        payload = cast(dict[str, Any], item)
        matches.append(
            AstMatch(
                rule_id=rule.id,
                path=source_path,
                line=_line_from_payload(payload),
                message=rule.title,
            )
        )
    return matches


def _line_from_payload(payload: dict[str, Any]) -> int:
    range_payload = payload.get("range")
    if isinstance(range_payload, dict):
        start = range_payload.get("start")
        if isinstance(start, dict) and isinstance(start.get("line"), int):
            return int(start["line"]) + 1
    if isinstance(payload.get("line"), int):
        return int(payload["line"])
    return 1
