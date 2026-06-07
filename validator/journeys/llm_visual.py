"""LLM visual contract evaluator for User Journeys v2."""

# @spec FR-036, FR-037, FR-038, FR-039: LLM screenshots, strict JSON, privacy
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#fr-036

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class LlmVisualEvaluation:
    """Strict result returned by the LLM visual evaluator boundary."""

    passed: bool
    confidence: float
    criteria_passed: list[str] = field(default_factory=list)
    criteria_failed: list[str] = field(default_factory=list)
    explanation: str = ""
    blocking: bool = False
    reason: str = "ok"


def evaluate_llm_visual_contract(
    *,
    screenshot_path: str,
    prompt: str,
    provider: Callable[[str], str],
    blocking: bool = True,
) -> LlmVisualEvaluation:
    """Evaluate one screenshot contract using a provider returning strict JSON."""
    provider_prompt = (
        "Return strict JSON with keys pass, confidence, criteria_passed, "
        f"criteria_failed, explanation. Screenshot: {screenshot_path}. {prompt}"
    )
    response = provider(provider_prompt)
    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        return LlmVisualEvaluation(
            passed=False,
            confidence=0.0,
            blocking=True,
            reason="llm_visual_json_invalid",
        )
    if not isinstance(data, dict) or not isinstance(data.get("pass"), bool):
        return LlmVisualEvaluation(
            passed=False,
            confidence=0.0,
            blocking=True,
            reason="llm_visual_schema_invalid",
        )
    return LlmVisualEvaluation(
        passed=bool(data["pass"]),
        confidence=float(data.get("confidence", 0.0)),
        criteria_passed=_string_list(data.get("criteria_passed")),
        criteria_failed=_string_list(data.get("criteria_failed")),
        explanation=str(data.get("explanation", "")),
        blocking=blocking and not bool(data["pass"]),
    )


def _string_list(value: object) -> list[str]:
    """Return only string values from a provider JSON list."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


__all__ = ["LlmVisualEvaluation", "evaluate_llm_visual_contract"]
