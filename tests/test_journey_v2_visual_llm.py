# LiveSpec traceability anchors
# @spec(AC-039)
# @spec(AC-040)
# @spec(AC-041)
# @spec(AC-042)
# @spec(AC-043)

"""Tests for the User Journeys v2 LLM visual evaluator (not wired into `journey run`)."""

from __future__ import annotations

import json

from validator.journeys.llm_visual import evaluate_llm_visual_contract


def test_llm_visual_contract_accepts_strict_fake_provider_json() -> None:
    """FR-038: LLM evaluator consumes strict JSON from a fake provider."""

    def provider(_: str) -> str:
        return json.dumps(
            {
                "pass": True,
                "confidence": 0.91,
                "criteria_passed": ["centered"],
                "criteria_failed": [],
                "explanation": "The card is centered.",
            }
        )

    result = evaluate_llm_visual_contract(
        screenshot_path="runs/success.png",
        prompt="Verify the card is centered.",
        provider=provider,
    )

    assert result.passed is True
    assert result.confidence == 0.91


def test_llm_visual_contract_blocks_malformed_json() -> None:
    """FR-039: malformed provider responses are blocking evaluation failures."""
    result = evaluate_llm_visual_contract(
        screenshot_path="runs/success.png",
        prompt="Verify the card is centered.",
        provider=lambda _: "not json",
    )

    assert result.passed is False
    assert result.blocking is True
    assert result.reason == "llm_visual_json_invalid"
