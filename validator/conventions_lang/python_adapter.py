# LiveSpec traceability anchors
# @spec(FR-003)

"""Python conventions adapter based on stdlib AST."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from .base import FunctionSpan, ImportRef, SourceAnalysis, SuppressionRef, TokenUsage


class PythonAdapter:
    """Analyze Python source for deterministic convention checks."""

    language = "python"
    coverage = "full"

    def analyze(self, path: Path, text: str) -> SourceAnalysis:
        """Analyze Python source text."""
        functions = _functions_from_ast(text)
        imports = _imports_from_ast(text)
        return SourceAnalysis(
            language=self.language,
            coverage=self.coverage,
            functions=tuple(functions),
            imports=tuple(imports),
            suppressions=tuple(_suppression_refs(text, ("# noqa", "# type: ignore"))),
            token_usages=tuple(_token_usages(text)),
        )


def _functions_from_ast(text: str) -> list[FunctionSpan]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    lines = text.splitlines()
    spans: list[FunctionSpan] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end_line = getattr(node, "end_lineno", node.lineno)
            spans.append(
                FunctionSpan(
                    name=node.name,
                    start_line=node.lineno,
                    end_line=end_line,
                    is_public=not node.name.startswith("_"),
                    has_doc=ast.get_docstring(node) is not None
                    or _has_preceding_comment_doc(lines, node.lineno),
                )
            )
    return spans


def _imports_from_ast(text: str) -> list[ImportRef]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    refs: list[ImportRef] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            refs.extend(ImportRef(alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            refs.append(ImportRef(node.module, node.lineno))
    return refs


def _has_preceding_comment_doc(lines: list[str], line_number: int) -> bool:
    index = line_number - 2
    while index >= 0 and not lines[index].strip():
        index -= 1
    return index >= 0 and lines[index].lstrip().startswith("#")


def _suppression_refs(text: str, tokens: tuple[str, ...]) -> list[SuppressionRef]:
    refs: list[SuppressionRef] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        refs.extend(SuppressionRef(token, line_number) for token in tokens if token in line)
    return refs


def _token_usages(text: str) -> list[TokenUsage]:
    pattern = re.compile(r"\b(padding|margin|spacing)\w*\s*[:=]\s*(\d+)\b", re.IGNORECASE)
    return [
        TokenUsage(match.group(1), int(match.group(2)), line_number)
        for line_number, line in enumerate(text.splitlines(), start=1)
        for match in pattern.finditer(line)
    ]
