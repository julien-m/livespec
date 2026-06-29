"""Protocol for AST convention detector backends."""

from __future__ import annotations

from typing import Protocol

from validator.conventions_ast.models import AstBackendResult, AstRule, AstSourceFile


class AstBackend(Protocol):
    """Backend adapter used by the AST conventions engine."""

    def scan(
        self,
        *,
        rules: tuple[AstRule, ...],
        source_files: tuple[AstSourceFile, ...],
    ) -> AstBackendResult:
        """Scan source files for rule matches."""
        raise NotImplementedError
