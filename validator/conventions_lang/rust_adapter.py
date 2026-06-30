# LiveSpec traceability anchors
# @spec(FR-003)

"""Rust conventions adapter using deterministic heuristics."""

from __future__ import annotations

import re
from pathlib import Path

from .base import FunctionSpan, ImportRef, SourceAnalysis, SuppressionRef


class RustAdapter:
    """Analyze Rust source for convention checks."""

    language = "rust"
    coverage = "partial"

    def analyze(self, path: Path, text: str) -> SourceAnalysis:
        """Analyze Rust source text."""
        return SourceAnalysis(
            language=self.language,
            coverage=self.coverage,
            functions=tuple(_function_spans(text)),
            imports=tuple(_imports(text)),
            suppressions=tuple(_suppression_refs(text)),
            token_usages=(),
        )


def _function_spans(text: str) -> list[FunctionSpan]:
    pattern = re.compile(r"\b(pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+([A-Za-z_]\w*)")
    lines = text.splitlines()
    spans: list[FunctionSpan] = []
    for index, line in enumerate(lines):
        match = pattern.search(line)
        if not match:
            continue
        spans.append(
            FunctionSpan(
                name=match.group(2),
                start_line=index + 1,
                end_line=_brace_end_line(lines, index),
                is_public=bool(match.group(1)),
                has_doc=index > 0 and lines[index - 1].lstrip().startswith("///"),
            )
        )
    return spans


def _imports(text: str) -> list[ImportRef]:
    refs: list[ImportRef] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped.startswith("use "):
            continue
        module = stripped[len("use ") :].rstrip(";").strip()
        if module:
            refs.append(ImportRef(module, line_number))
    return refs


def _suppression_refs(text: str) -> list[SuppressionRef]:
    return [
        SuppressionRef("allow", line_number)
        for line_number, line in enumerate(text.splitlines(), start=1)
        if "#[allow(" in line
    ]


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
