"""Domain exceptions for the LiveSpec validator."""

from __future__ import annotations


class SpecsRootNotFoundError(Exception):
    """Raised when the .specs/ directory cannot be found.

    Args:
        search_path: The path that was searched from.
    """

    def __init__(self, search_path: str) -> None:
        super().__init__(f".specs/ directory not found from {search_path}")
        self.search_path = search_path


class PlanReviewError(Exception):
    """Raised when an LLM plan review fails for a feature.

    Args:
        feature_name: The feature directory name.
        reason: Description of the failure.
    """

    def __init__(self, feature_name: str, reason: str) -> None:
        super().__init__(f"Plan review failed for {feature_name}: {reason}")
        self.feature_name = feature_name
        self.reason = reason


class AssertionExtractionError(Exception):
    """Raised when LLM assertion extraction fails for a document.

    Args:
        document: Source document path.
        reason: Description of the failure.
    """

    def __init__(self, document: str, reason: str) -> None:
        super().__init__(f"Assertion extraction failed for {document}: {reason}")
        self.document = document
        self.reason = reason


class ContradictionComparisonError(Exception):
    """Raised when LLM contradiction comparison fails.

    Args:
        doc_a: First document path.
        doc_b: Second document path.
        reason: Description of the failure.
    """

    def __init__(self, doc_a: str, doc_b: str, reason: str) -> None:
        super().__init__(f"Comparison failed for {doc_a} x {doc_b}: {reason}")
        self.doc_a = doc_a
        self.doc_b = doc_b
        self.reason = reason
