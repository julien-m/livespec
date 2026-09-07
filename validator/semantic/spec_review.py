"""LLM-based spec quality review."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from validator.coherence.violation import Severity
from validator.semantic.plan_review import ReviewFinding
from validator.semantic.review_context import PreparedReview, prepare_review_context
from validator.semantic.review_contract import ReviewReceipt
from validator.semantic.review_receipts import legacy_display_fields, run_prepared_review


# @spec FR-002: Build spec review prompt — .specs/features/001-auto-llm-review/spec.md#fr-002
@dataclass
class SpecReviewResult:
    """Advisory spec-review display fields alongside independent receipt evidence.

    Construction does not validate readiness. Empty findings are insufficient:
    consumers require complete evidence and a receipt verified as ready against
    the current context, model and policy before authorizing progression.

    Attributes:
        findings: Legacy display findings derived from the receipt; not exhaustive proof.
        reviewer_model: Receipt's resolved model identity, or empty when unresolved.
        confidence: Reviewer confidence from the receipt (1-5), or zero when unavailable.
        spec_metrics: Counts of FR/AC references, stories and edge cases in supplied spec text;
            these display counts do not establish semantic coverage.
        complete: Receipt completeness copied by the producer; not its readiness verdict.
        receipt: In-memory grounded review and raw evidence, or None when absent;
            this field does not own a persisted cache path or perform freshness checks.
    """

    findings: list[ReviewFinding] = field(default_factory=list)
    reviewer_model: str = ""
    confidence: int = 0
    spec_metrics: dict[str, int] = field(default_factory=dict)
    complete: bool = False
    receipt: ReviewReceipt | None = None


def compute_spec_metrics(spec_content: str) -> dict[str, int]:
    """Extract quality metrics from spec markdown.

    Best-effort regex counting of FR references, AC references,
    story headings, and edge case items.

    Args:
        spec_content: Raw markdown content of the spec.

    Returns:
        Dict with keys: fr_count, ac_count, story_count, edge_case_count.
    """
    fr_refs = set(re.findall(r"FR-\d+", spec_content))
    ac_refs = set(re.findall(r"AC-\d+", spec_content))
    stories = len(re.findall(r"###\s+Story\s+\d+", spec_content))
    # Count edge case bullets (lines starting with - ** or - in Edge Cases section)
    edge_section = re.split(r"##\s+Edge\s+Cases", spec_content, flags=re.IGNORECASE)
    edge_case_count = 0
    if len(edge_section) > 1:
        # Count list items in the edge cases section (up to next ## heading)
        edge_text = re.split(r"\n##\s+", edge_section[1])[0]
        edge_case_count = len(re.findall(r"^-\s+", edge_text, re.MULTILINE))
    return {
        "fr_count": len(fr_refs),
        "ac_count": len(ac_refs),
        "story_count": stories,
        "edge_case_count": edge_case_count,
    }


# @spec FR-003: Send to LLM, FR-004: Parse ReviewFinding
# .specs/features/001-auto-llm-review/spec.md#fr-003
def review_spec(
    spec_content: str,
    model: str | None = None,
    *,
    prepared: PreparedReview | None = None,
    cache_path: Path | None = None,
) -> SpecReviewResult:
    """Review supplied context while retaining explicit incomplete advisory results.

    Args:
        spec_content: Complete specification text; also used for displayed metrics.
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
        "supplied", {"spec": spec_content}, kind="spec", model=model or ""
    )
    receipt = run_prepared_review(context, cache_path=cache_path, model=model)
    return _spec_result(spec_content, receipt)


def _spec_result(spec_content: str, receipt: ReviewReceipt) -> SpecReviewResult:
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
    return SpecReviewResult(
        findings=findings,
        reviewer_model=receipt.reviewer_model,
        confidence=confidence,
        spec_metrics=compute_spec_metrics(spec_content),
        complete=receipt.complete,
        receipt=receipt,
    )
