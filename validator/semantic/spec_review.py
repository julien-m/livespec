"""LLM-based spec quality review."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from validator.coherence.violation import Severity
from validator.semantic.plan_review import ReviewFinding


# @spec FR-002: Build spec review prompt — .specs/features/001-auto-llm-review/spec.md#fr-002
@dataclass
class SpecReviewResult:
    """Result of reviewing a spec.md for quality.

    Attributes:
        findings: List of review findings.
        reviewer_model: Model ID used for the review.
        confidence: Self-reported reviewer confidence (1-5).
        spec_metrics: Spec complexity metrics.
    """

    findings: list[ReviewFinding] = field(default_factory=list)
    reviewer_model: str = ""
    confidence: int = 0
    spec_metrics: dict[str, int] = field(default_factory=dict)


_SPEC_REVIEW_PROMPT = """\
You are an adversarial spec quality auditor. \
Your job is to find real problems, not validate.

Review this feature specification for quality issues. Focus on:
1. **FR testability**: Are functional requirements concrete enough to \
   write a test? Flag vague verbs (e.g., "should handle", "manages") \
   with no measurable outcome.
2. **AC measurability**: Can each acceptance criterion be verified with \
   a pass/fail test? Flag criteria that are subjective or unmeasurable.
3. **Edge case coverage**: Are obvious edge cases missing? Consider \
   empty inputs, error states, concurrency, timeouts, and boundary values.
4. **Entity completeness**: Are all entities referenced in FRs defined \
   in the Key Entities section? Are entity fields sufficient for the FRs?

Be specific. Cite FR/AC IDs when possible. Do not praise the spec.

## Specification
{spec_content}

Return JSON with your findings and a confidence score (1-5) rating \
your thoroughness.
A score of 5 means you are very confident you caught all issues.
A score below 3 means you may have missed things."""

_SPEC_REVIEW_SCHEMA: dict[str, Any] = {
    "name": "spec_review",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"},
                        "severity": {
                            "type": "string",
                            "enum": ["blocking", "warning", "info"],
                        },
                        "description": {"type": "string"},
                        "suggestion": {"type": "string"},
                    },
                    "required": [
                        "category",
                        "severity",
                        "description",
                        "suggestion",
                    ],
                },
            },
            "confidence": {"type": "integer"},
        },
        "required": ["findings", "confidence"],
    },
}


# @spec FR-002: Build spec review prompt — .specs/features/001-auto-llm-review/spec.md#fr-002
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
) -> SpecReviewResult:
    """Review a spec via LLM for quality issues.

    Sends an adversarial review prompt to the configured LLM provider and
    returns structured findings.

    Args:
        spec_content: Raw markdown of the feature spec.
        model: Optional model ID override (e.g., "google/gemini-3.1-pro").

    Returns:
        Review result with findings, confidence, and spec metrics.

    Raises:
        LLMProviderNotConfigured: If no LLM provider is available.
        json.JSONDecodeError: If the LLM response is not valid JSON.
    """
    from validator.llm_provider import call_llm

    prompt = _SPEC_REVIEW_PROMPT.format(
        spec_content=spec_content[:8000],
    )

    raw = call_llm(prompt, json_schema=_SPEC_REVIEW_SCHEMA, model=model)
    data = json.loads(raw)

    severity_map = {
        "blocking": Severity.ERROR,
        "warning": Severity.WARNING,
        "info": Severity.INFO,
    }

    findings = [
        ReviewFinding(
            category=f.get("category", "general"),
            severity=severity_map.get(
                f.get("severity", "warning"), Severity.WARNING
            ),
            description=f.get("description", ""),
            suggestion=f.get("suggestion", ""),
        )
        for f in data.get("findings", [])
    ]

    return SpecReviewResult(
        findings=findings,
        reviewer_model=model or "default",
        confidence=data.get("confidence", 0),
        spec_metrics=compute_spec_metrics(spec_content),
    )
