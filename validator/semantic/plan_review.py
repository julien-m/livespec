"""LLM-based plan substance review."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from validator.coherence.violation import Severity


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
    """Result of reviewing a plan against its spec.

    Attributes:
        findings: List of review findings.
        reviewer_model: Model ID used for the review.
        confidence: Self-reported reviewer confidence (1-5).
        complexity: Plan complexity metrics.
    """

    findings: list[ReviewFinding] = field(default_factory=list)
    reviewer_model: str = ""
    confidence: int = 0
    complexity: dict[str, int] = field(default_factory=dict)


_REVIEW_PROMPT = """\
You are an adversarial technical plan auditor. \
Your job is to find real problems, not validate.

Review this implementation plan against its specification. Focus on:
1. **Coverage gaps**: Which AC or FR from spec have NO corresponding \
   step in the plan?
2. **Tech inconsistencies**: Which tech choices contradict the configured \
   stack?
3. **Ordering issues**: Which steps depend on outputs of later steps?
4. **Missing steps**: What is obviously needed but not planned?
5. **Stack mismatches**: Does the plan use technologies not in the stack?
6. **Over-engineering**: What is planned but not required by any FR?

Be specific. Cite FR/AC IDs when possible. Do not praise the plan.

## Specification
{spec_content}

## Plan
{plan_content}

## Stack
{stack_content}

## Constitution
{constitution_content}

Return JSON with your findings and a confidence score (1-5) rating \
your thoroughness.
A score of 5 means you are very confident you caught all issues.
A score below 3 means you may have missed things."""

_REVIEW_SCHEMA: dict[str, Any] = {
    "name": "plan_review",
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
                    "required": ["category", "severity", "description", "suggestion"],
                },
            },
            "confidence": {"type": "integer"},
        },
        "required": ["findings", "confidence"],
    },
}


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
) -> PlanReviewResult:
    """Review a plan against its spec via LLM.

    Sends an adversarial review prompt to the configured LLM provider and
    returns structured findings.

    Args:
        spec_content: Raw markdown of the feature spec.
        plan_content: Raw markdown of the plan to review.
        stack_content: Raw markdown of the stack definition.
        constitution_content: Raw markdown of the constitution.
        model: Optional model ID override (e.g., "google/gemini-3.1-pro").

    Returns:
        Review result with findings, confidence, and complexity metrics.

    Raises:
        LLMProviderNotConfigured: If no LLM provider is available.
        json.JSONDecodeError: If the LLM response is not valid JSON.
    """
    from validator.llm_provider import call_llm

    prompt = _REVIEW_PROMPT.format(
        spec_content=spec_content[:8000],
        plan_content=plan_content[:8000],
        stack_content=(
            stack_content[:2000] if stack_content else "(not provided)"
        ),
        constitution_content=(
            constitution_content[:2000]
            if constitution_content
            else "(not provided)"
        ),
    )

    raw = call_llm(prompt, json_schema=_REVIEW_SCHEMA, model=model)
    data = json.loads(raw)

    severity_map = {
        "blocking": Severity.ERROR,
        "warning": Severity.WARNING,
        "info": Severity.INFO,
    }

    findings = [
        ReviewFinding(
            category=f.get("category", "general"),
            severity=severity_map.get(f.get("severity", "warning"), Severity.WARNING),
            description=f.get("description", ""),
            suggestion=f.get("suggestion", ""),
        )
        for f in data.get("findings", [])
    ]

    return PlanReviewResult(
        findings=findings,
        reviewer_model=model or "default",
        confidence=data.get("confidence", 0),
        complexity=compute_plan_complexity(plan_content),
    )
