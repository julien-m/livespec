"""LLM-based plan substance review."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from validator.coherence.violation import Severity
from validator.semantic.review_context import PreparedReview, prepare_review_context
from validator.semantic.review_contract import ReviewReceipt
from validator.semantic.review_receipts import legacy_display_fields, run_prepared_review


@dataclass
class ReviewFinding:
    """A single finding from the plan review.

    Attributes:
        category: Free-form category (e.g., coverage_gap, tech_inconsistency).
        severity: Impact level (ERROR for blocking, WARNING, INFO).
        description: What the issue is.
        suggestion: How to fix it.
    """

    category: str
    severity: Severity
    description: str
    suggestion: str


@dataclass
class PlanReviewResult:
    """Advisory plan-review display fields alongside independent receipt evidence.

    Construction does not validate readiness. Empty findings are insufficient:
    consumers require complete evidence and a receipt verified as ready against
    the current context, model and policy before authorizing progression.

    Attributes:
        findings: Legacy display findings derived from the receipt; not exhaustive proof.
        reviewer_model: Receipt's resolved model identity, or empty when unresolved.
        confidence: Reviewer confidence from the receipt (1-5), or zero when unavailable.
        complexity: Counts of FR/AC references, paths and diagrams in supplied plan text;
            these display counts do not establish semantic coverage.
        complete: Receipt completeness copied by the producer; not its readiness verdict.
        receipt: In-memory grounded review and raw evidence, or None when absent;
            this field does not own a persisted cache path or perform freshness checks.
    """

    findings: list[ReviewFinding] = field(default_factory=list)
    reviewer_model: str = ""
    confidence: int = 0
    complexity: dict[str, int] = field(default_factory=dict)
    complete: bool = False
    receipt: ReviewReceipt | None = None


def compute_plan_complexity(plan_content: str) -> dict[str, int]:
    """Extract complexity metrics from plan markdown.

    Best-effort regex counting of FR references, file paths, AC references,
    and Mermaid diagram blocks.

    Args:
        plan_content: Raw markdown content of the plan.

    Returns:
        Dict with keys: fr_count, file_count, ac_count, diagram_count.
    """
    fr_refs = set(re.findall(r"FR-\d+", plan_content))
    ac_refs = set(re.findall(r"AC-\d+", plan_content))
    diagrams = len(re.findall(r"```mermaid", plan_content))
    # Count file paths: `path/to/file.ext` followed by (new) or (modified)
    file_lines = re.findall(
        r"`([^`]+\.\w+)`\s*\((?:new|modified|modify)\)", plan_content, re.IGNORECASE
    )
    return {
        "fr_count": len(fr_refs),
        "ac_count": len(ac_refs),
        "diagram_count": diagrams,
        "file_count": len(set(file_lines)),
    }


def review_plan(
    spec_content: str,
    plan_content: str,
    stack_content: str = "",
    constitution_content: str = "",
    model: str | None = None,
    *,
    prepared: PreparedReview | None = None,
    cache_path: Path | None = None,
) -> PlanReviewResult:
    """Review supplied context while retaining explicit incomplete advisory results.

    Args:
        spec_content: Complete specification text when prepared is omitted.
        plan_content: Complete plan text; also used for displayed complexity metrics.
        stack_content: Complete stack context when prepared is omitted.
        constitution_content: Complete constitution when prepared is omitted.
        model: Explicit provider model; None uses the prepared identity or provider default.
        prepared: Authoritative assembled context, superseding the supplied review texts.
        cache_path: Optional derived receipt path to read and atomically replace.

    Returns:
        Display findings, completeness, receipt, and its resolved model (empty if unknown).

    Raises:
        ValueError: Explicit model conflicts with context or response JSON is malformed.
        OSError: Cache publication fails.
        LLMProviderNotConfigured: A provider call is needed but no provider is configured.

    Side effects:
        May invoke the configured provider and read/write the cache. Provider exceptions
        propagate; incomplete evidence remains visible and does not certify readiness.
    """
    context = prepared or prepare_review_context(
        "supplied",
        {
            "spec": spec_content,
            "plan": plan_content,
            "stack": stack_content,
            "constitution": constitution_content,
        },
        kind="plan",
        model=model or "",
    )
    receipt = run_prepared_review(context, cache_path=cache_path, model=model)
    return _plan_result(plan_content, receipt)


def _plan_result(plan_content: str, receipt: ReviewReceipt) -> PlanReviewResult:
    """Render advisory fields without changing the validated receipt identity."""
    fields, confidence = legacy_display_fields(receipt)
    severity_map = {"blocking": Severity.ERROR, "warning": Severity.WARNING, "info": Severity.INFO}
    findings = [
        ReviewFinding(
            category=f.get("category", "general"),
            severity=severity_map.get(f.get("severity", "warning"), Severity.WARNING),
            description=f.get("description", ""),
            suggestion=f.get("suggestion", ""),
        )
        for f in fields
    ]
    return PlanReviewResult(
        findings=findings,
        reviewer_model=receipt.reviewer_model,
        confidence=confidence,
        complexity=compute_plan_complexity(plan_content),
        complete=receipt.complete,
        receipt=receipt,
    )
