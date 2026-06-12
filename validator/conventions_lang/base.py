# LiveSpec traceability anchors
# @spec(FR-003)

"""Shared types for conventions language adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class FunctionSpan:
    """One function-like declaration discovered in source code."""

    name: str
    start_line: int
    end_line: int
    is_public: bool
    has_doc: bool

    @property
    def line_count(self) -> int:
        """Return inclusive line count."""
        return self.end_line - self.start_line + 1


@dataclass(frozen=True)
class ImportRef:
    """One import relationship discovered in source code."""

    module: str
    line: int


@dataclass(frozen=True)
class SuppressionRef:
    """One inline linter/type-checker suppression directive."""

    token: str
    line: int


@dataclass(frozen=True)
class TokenUsage:
    """One numeric design token use."""

    property_name: str
    value: int
    line: int


@dataclass(frozen=True)
class SourceAnalysis:
    """Adapter output for one source file."""

    language: str
    coverage: str
    functions: tuple[FunctionSpan, ...]
    imports: tuple[ImportRef, ...]
    suppressions: tuple[SuppressionRef, ...]
    token_usages: tuple[TokenUsage, ...]


class LanguageAdapter(Protocol):
    """Protocol implemented by language adapters."""

    language: str
    coverage: str

    def analyze(self, path: Path, text: str) -> SourceAnalysis:
        """Analyze source text."""
        raise NotImplementedError
