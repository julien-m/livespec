# LiveSpec traceability anchors
# @spec(AC-038)
# @spec(AC-039)
# @spec(AC-040)
# @spec(AC-041)
# @spec(AC-042)
# @spec(AC-043)

"""Tests for User Journeys v2 native and LLM visual checks."""

from __future__ import annotations

import json

from validator.journeys.llm_visual import evaluate_llm_visual_contract
from validator.journeys.visual_contracts import (
    ElementBounds,
    NativeVisualCheckResult,
    evaluate_native_visual_check,
)


def test_native_visual_check_detects_min_margin_failure() -> None:
    """FR-034: native visual checks fail when measured margins are too small."""
    result = evaluate_native_visual_check(
        assertion="min_margin",
        element=ElementBounds(x=4, y=20, width=100, height=40),
        parent=ElementBounds(x=0, y=0, width=300, height=120),
        min_px=16,
    )

    assert isinstance(result, NativeVisualCheckResult)
    assert result.passed is False
    assert result.measurements["left_margin"] == 4


def test_native_visual_check_detects_text_overflow() -> None:
    """FR-034: text-fit checks fail when text bounds exceed parent bounds."""
    result = evaluate_native_visual_check(
        assertion="text_fits",
        element=ElementBounds(x=0, y=0, width=340, height=40),
        parent=ElementBounds(x=0, y=0, width=300, height=40),
    )

    assert result.passed is False
    assert result.reason == "text_overflows_parent"


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
