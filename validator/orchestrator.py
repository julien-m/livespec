"""Orchestrator for Layer 4 semantic validation."""

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
from .semantic.plan_review import PlanReviewResult, review_plan

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


@dataclass
class PlanReviewEntry:
    """A single feature's plan review result.

    Attributes:
        feature_name: Directory name of the reviewed feature.
        result: The plan review result from the LLM.
    """

    feature_name: str
    result: PlanReviewResult


@dataclass
class PlanReviewCheckResult:
    """Result of running plan review across all features.

    Attributes:
        reviews: List of (feature_name, review_result) pairs.
        errors: List of error messages from failed reviews.
    """

    reviews: list[PlanReviewEntry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _is_review_soft(result: PlanReviewResult, confidence_threshold: float) -> bool:
    """Check if a review is suspiciously empty for its plan complexity.

    Args:
        result: The review result to evaluate.
        confidence_threshold: Confidence below which to consider soft.

    Returns:
        True if review looks soft (0 findings, low confidence, complex plan).
    """
    if result.findings:
        return False
    if result.confidence >= confidence_threshold:
        return False
    return sum(result.complexity.values()) > 5


def run_plan_review(
    specs_root: Path,
    models: list[str] | None = None,
    all_reviewers: bool = False,
    confidence_threshold: float = 3.0,
) -> PlanReviewCheckResult:
    """Run LLM plan review on all features with both spec.md and plan.md.

    When not in all_reviewers mode, cascades to the next configured reviewer
    if the first one returns a soft review (0 findings + low confidence on a
    complex plan). If two reviewers both return 0 findings, the plan is
    considered validated without warning.

    Args:
        specs_root: Root directory of the .specs/ tree.
        models: Reviewer model IDs. If None, uses provider default.
        all_reviewers: If True, run all models. If False, use first only.
        confidence_threshold: Confidence below which to consider a review soft.

    Returns:
        Result containing reviews per feature and any errors.
    """
    graph = build_graph(specs_root)
    check_result = PlanReviewCheckResult()

    # Read global context files
    constitution_path = specs_root / "constitution.md"
    stack_path = specs_root / "stacks" / "_default.md"
    constitution_content = (
        constitution_path.read_text() if constitution_path.exists() else ""
    )
    stack_content = (
        stack_path.read_text() if stack_path.exists() else ""
    )

    # Determine which models to use
    review_models: list[str | None] = [None]
    if models:
        review_models = list(models) if all_reviewers else [models[0]]

    for feature in graph.features:
        has_spec = feature.files.get("spec", False)
        has_plan = feature.files.get("plan", False)

        if not has_spec or not has_plan:
            continue

        spec_path = specs_root / "features" / feature.dir_name / "spec.md"
        plan_path = specs_root / "features" / feature.dir_name / "plan.md"

        spec_content = spec_path.read_text()
        plan_content = plan_path.read_text()

        if all_reviewers:
            # Run all reviewers independently
            for model in review_models:
                _run_single_review(
                    feature.dir_name, spec_content, plan_content,
                    stack_content, constitution_content, model,
                    check_result,
                )
        else:
            # Cascade: try first, if soft try next, stop when satisfied
            _run_cascade_review(
                feature.dir_name, spec_content, plan_content,
                stack_content, constitution_content,
                review_models if models else [None],
                models or [],
                confidence_threshold, check_result,
            )

    return check_result


def _run_single_review(
    feature_name: str,
    spec_content: str,
    plan_content: str,
    stack_content: str,
    constitution_content: str,
    model: str | None,
    check_result: PlanReviewCheckResult,
) -> PlanReviewResult | None:
    """Run a single review and append to results.

    Args:
        feature_name: Feature directory name.
        spec_content: Spec markdown content.
        plan_content: Plan markdown content.
        stack_content: Stack markdown content.
        constitution_content: Constitution markdown content.
        model: Model ID or None for provider default.
        check_result: Result accumulator to append to.

    Returns:
        The review result, or None if the review failed.
    """
    try:
        result = review_plan(
            spec_content=spec_content,
            plan_content=plan_content,
            stack_content=stack_content,
            constitution_content=constitution_content,
            model=model,
        )
        check_result.reviews.append(
            PlanReviewEntry(feature_name=feature_name, result=result)
        )
        return result
    except Exception as exc:  # Broad catch: LLM review can fail unpredictably
        logger.warning("Plan review failed for %s: %s", feature_name, exc)
        check_result.errors.append(f"{feature_name}: {exc}")
        return None


def _run_cascade_review(
    feature_name: str,
    spec_content: str,
    plan_content: str,
    stack_content: str,
    constitution_content: str,
    review_models: list[str | None],
    all_models: list[str],
    confidence_threshold: float,
    check_result: PlanReviewCheckResult,
) -> None:
    """Run reviews with cascade: if first is soft, try the next model.

    If the first reviewer returns a soft review (0 findings, low confidence,
    complex plan) and more models are configured, automatically try the next
    one. If two reviewers both return 0 findings, the plan is considered
    validated (no suspicion warning needed).

    Args:
        feature_name: Feature directory name.
        spec_content: Spec markdown content.
        plan_content: Plan markdown content.
        stack_content: Stack markdown content.
        constitution_content: Constitution markdown content.
        review_models: Models to use (first entry is the primary).
        all_models: Full list of configured models (for cascade).
        confidence_threshold: Confidence below which to consider soft.
        check_result: Result accumulator to append to.
    """
    result = _run_single_review(
        feature_name, spec_content, plan_content,
        stack_content, constitution_content,
        review_models[0], check_result,
    )

    if result is None:
        return

    # Cascade: if soft review and more models available, try next
    if _is_review_soft(result, confidence_threshold) and len(all_models) > 1:
        cascade_model = all_models[1]
        logger.info(
            "Soft review for %s from %s, cascading to %s",
            feature_name, result.reviewer_model, cascade_model,
        )
        cascade_result = _run_single_review(
            feature_name, spec_content, plan_content,
            stack_content, constitution_content,
            cascade_model, check_result,
        )

        # If second reviewer also finds nothing, mark confidence as validated
        # and remove the soft first review to avoid displaying warning
        if cascade_result and not cascade_result.findings:
            cascade_result.confidence = 5  # Both agree: high confidence
            # Remove the soft first review from results (keep only validated cascade)
            check_result.reviews = [
                e for e in check_result.reviews
                if e.feature_name != feature_name or e.result.confidence == 5
            ]
