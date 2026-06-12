# LiveSpec traceability anchors
# @spec(FR-003)

"""Generic fallback conventions adapter."""

from __future__ import annotations

from pathlib import Path

from .base import SourceAnalysis


class GenericAdapter:
    """Partial-coverage fallback for unknown file types."""

    language = "generic"
    coverage = "partial"

    def analyze(self, path: Path, text: str) -> SourceAnalysis:
        """Return an honest partial analysis for unsupported files."""
        return SourceAnalysis(
            language=self.language,
            coverage=self.coverage,
            functions=(),
            imports=(),
            suppressions=(),
            token_usages=(),
        )
