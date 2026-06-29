"""Deterministic fake AST backend for mode semantics tests."""

from __future__ import annotations

from validator.conventions_ast.models import (
    AstBackendInfo,
    AstBackendResult,
    AstMatch,
    AstRule,
    AstSourceFile,
)


class FakeAstBackend:
    """In-memory backend used by tests without requiring ``sg``."""

    def __init__(
        self,
        *,
        matches: list[AstMatch] | None = None,
        available: bool = True,
    ) -> None:
        self._matches = tuple(matches or [])
        self._available = available
        self.scan_calls = 0

    def scan(
        self,
        *,
        rules: tuple[AstRule, ...],
        source_files: tuple[AstSourceFile, ...],
    ) -> AstBackendResult:
        """Return configured matches and record scan calls."""
        self.scan_calls += 1
        if not self._available:
            return AstBackendResult(
                info=AstBackendInfo(
                    name="ast-grep",
                    command="sg",
                    status="unavailable",
                    message="fake backend unavailable",
                ),
                matches=(),
            )
        rule_ids = {rule.id for rule in rules}
        source_paths = {source.path for source in source_files}
        return AstBackendResult(
            info=AstBackendInfo(
                name="ast-grep",
                command="sg",
                status="available",
                version="fake-ast-grep 1.0",
            ),
            matches=tuple(
                match
                for match in self._matches
                if match.rule_id in rule_ids and match.path in source_paths
            ),
        )
