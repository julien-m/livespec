# LiveSpec traceability anchors
# @spec(FR-003)

"""TypeScript and React conventions adapter using deterministic heuristics."""

from __future__ import annotations

import re
from pathlib import Path

from .base import FunctionSpan, ImportRef, SourceAnalysis, SuppressionRef, TokenUsage


class TypeScriptAdapter:
    """Analyze TS/JS/React source with honest heuristic coverage."""

    language = "typescript"
    coverage = "full"

    def analyze(self, path: Path, text: str) -> SourceAnalysis:
        """Analyze TypeScript, JavaScript, or React source text."""
        return SourceAnalysis(
            language=self.language,
            coverage=self.coverage,
            functions=tuple(_function_spans(text)),
            imports=tuple(_imports(text)),
            suppressions=tuple(_suppression_refs(text)),
            token_usages=tuple(_token_usages(text)),
        )


def _function_spans(text: str) -> list[FunctionSpan]:
    pattern = re.compile(r"\b(export\s+)?(async\s+)?function\s+([A-Za-z_][\w]*)")
    lines = text.splitlines()
    spans: list[FunctionSpan] = []
    for index, line in enumerate(lines):
        match = pattern.search(line)
        if not match:
            continue
        end = _brace_end_line(lines, index)
        spans.append(
            FunctionSpan(
                name=match.group(3),
                start_line=index + 1,
                end_line=end,
                is_public=bool(match.group(1)),
                has_doc=_has_jsdoc(lines, index),
            )
        )
    return spans


def _imports(text: str) -> list[ImportRef]:
    pattern = re.compile(r"^\s*import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]", re.MULTILINE)
    return [
        ImportRef(match.group(1), text[: match.start()].count("\n") + 1)
        for match in pattern.finditer(text)
    ]


def _suppression_refs(text: str) -> list[SuppressionRef]:
    tokens = ("eslint-disable", "@ts-ignore", "@ts-expect-error")
    refs: list[SuppressionRef] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        refs.extend(SuppressionRef(token, line_number) for token in tokens if token in line)
    return refs


def _token_usages(text: str) -> list[TokenUsage]:
    pattern = re.compile(r"\b(padding|margin|spacing)\w*\s*[:=]\s*[{]?(\d+)\b", re.IGNORECASE)
    return [
        TokenUsage(match.group(1), int(match.group(2)), line_number)
        for line_number, line in enumerate(text.splitlines(), start=1)
        for match in pattern.finditer(line)
    ]


def _has_jsdoc(lines: list[str], index: int) -> bool:
    cursor = index - 1
    while cursor >= 0 and not lines[cursor].strip():
        cursor -= 1
    return (
        cursor >= 0
        and "*/" in lines[cursor]
        and any("/**" in lines[item] for item in range(max(0, cursor - 5), cursor + 1))
    )


def _brace_end_line(lines: list[str], start_index: int) -> int:
    depth = 0
    seen = False
    for index in range(start_index, len(lines)):
        depth += lines[index].count("{")
        depth -= lines[index].count("}")
        seen = seen or "{" in lines[index]
        if seen and depth <= 0:
            return index + 1
    return len(lines)
