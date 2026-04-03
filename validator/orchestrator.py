"""Orchestrator for Layer 4 contradiction detection."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from .coherence.graph_builder import build_graph
from .semantic.contradictions import (
    Assertion,
    ContradictionResult,
    compare_assertions,
    extract_assertions,
    get_comparison_pairs,
)

logger = logging.getLogger(__name__)


@dataclass
class ContradictionEntry:
    """A single detected contradiction with its source assertions."""

    assertion_a: Assertion
    assertion_b: Assertion
    result: ContradictionResult


@dataclass
class ContradictionCheckResult:
    """Result of running contradiction detection across a spec tree."""

    pairs_count: int
    contradictions: list[ContradictionEntry] = field(default_factory=list)
    extraction_errors: list[str] = field(default_factory=list)
    comparison_errors: list[str] = field(default_factory=list)


def run_contradiction_check(
    specs_root: Path,
    confidence_threshold: float = 0.75,
) -> ContradictionCheckResult:
    """Run full contradiction detection on a spec tree.

    Extracts assertions from all relevant documents, then compares
    assertions with matching themes across document pairs.

    Args:
        specs_root: Root directory of the .specs/ tree.
        confidence_threshold: Minimum confidence to report a contradiction.

    Returns:
        Result containing detected contradictions and any extraction/comparison errors.
    """
    graph = build_graph(specs_root)
    pairs = get_comparison_pairs(graph)

    check_result = ContradictionCheckResult(pairs_count=len(pairs))

    all_assertions: dict[str, list[Assertion]] = {}
    for pair in pairs:
        for doc in pair:
            if doc not in all_assertions:
                doc_path = specs_root / doc
                if doc_path.exists():
                    content = doc_path.read_text()
                    try:
                        all_assertions[doc] = extract_assertions(content, doc)
                    except Exception as exc:  # Broad catch: LLM extraction can fail unpredictably
                        logger.warning("Failed to extract assertions from %s: %s", doc, exc)
                        check_result.extraction_errors.append(f"{doc}: {exc}")
                        all_assertions[doc] = []

    for doc_a, doc_b in pairs:
        for assertion_a in all_assertions.get(doc_a, []):
            for assertion_b in all_assertions.get(doc_b, []):
                if assertion_a.theme == assertion_b.theme:
                    try:
                        result = compare_assertions(assertion_a, assertion_b)
                        if result.contradicts and result.confidence >= confidence_threshold:
                            check_result.contradictions.append(
                                ContradictionEntry(
                                    assertion_a=assertion_a,
                                    assertion_b=assertion_b,
                                    result=result,
                                )
                            )
                    except Exception as exc:  # Broad catch: LLM comparison can fail unpredictably
                        logger.warning("Comparison failed for %s x %s: %s", doc_a, doc_b, exc)
                        check_result.comparison_errors.append(f"{doc_a} x {doc_b}: {exc}")

    return check_result
