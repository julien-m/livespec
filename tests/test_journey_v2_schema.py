# LiveSpec traceability anchors
# @spec(AC-003)
# @spec(AC-004)
# @spec(AC-005)
# @spec(AC-018)
# @spec(AC-035)
# @spec(AC-036)
# @spec(AC-037)
# @spec(AC-039)
# @spec(AC-042)
# @spec(AC-043)

"""Tests for User Journeys v2 schema boundary models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from validator.journeys.schema import (
    CoverageRef,
    JourneySourceV2,
    JourneyStatus,
    PrivacyPolicy,
    RunPolicyValue,
    RunStage,
    VisualCheck,
    VisualCheckMode,
)


def _valid_source() -> dict[str, object]:
    return {
        "schema_version": 2,
        "id": "onboarding-first-project",
        "title": "Onboarding first project",
        "status": "active",
        "description": "New user creates a first project.",
        "covers": [
            {
                "feature": "001-onboarding",
                "kind": "ac",
                "ref": "AC-001",
                "reason": "Signup starts the journey.",
            },
            {
                "feature": "012-projects",
                "kind": "fr",
                "ref": "FR-003",
                "reason": "Project creation completes the journey.",
            },
        ],
        "run_policy": {
            "local": "impacted",
            "pre_push": "smoke",
            "ci": "always",
            "nightly": "always",
        },
        "targets": [
            {
                "surface": "web",
                "runner": "playwright",
                "device": "desktop",
                "viewport": {"width": 1280, "height": 720},
            }
        ],
        "preconditions": {"auth": "anonymous", "fixtures": ["long-project-name"]},
        "steps": [
            {"action": "open", "target": {"route": "/signup"}},
            {
                "action": "click",
                "target": {"semantic_id": "signup.submit"},
            },
        ],
        "visual_checks": [
            {
                "id": "success-card-padding",
                "mode": "native",
                "assertion": "min_margin",
                "target": {"semantic_id": "project.success_card"},
                "min_px": 16,
            }
        ],
        "privacy": {"llm_allowed": False, "retention": "none"},
    }


def test_v2_schema_accepts_cross_feature_journey_source() -> None:
    """FR-001: v2 source accepts global journeys with qualified coverage refs."""
    source = JourneySourceV2.model_validate(_valid_source())

    assert source.schema_version == 2
    assert source.status is JourneyStatus.ACTIVE
    assert [cover.feature for cover in source.covers] == [
        "001-onboarding",
        "012-projects",
    ]
    assert source.run_policy[RunStage.CI] is RunPolicyValue.ALWAYS
    assert source.visual_checks[0].mode is VisualCheckMode.NATIVE


def test_coverage_ref_rejects_unqualified_feature_or_requirement_kind() -> None:
    """AC-004: unqualified coverage refs are rejected at schema boundary."""
    with pytest.raises(ValidationError) as exc_info:
        CoverageRef.model_validate({"ref": "AC-001", "kind": "ac", "reason": "missing feature"})

    assert "feature" in str(exc_info.value)


def test_v2_schema_rejects_text_target_without_product_contract_marker() -> None:
    """FR-020: visible text targets must declare they are product contracts."""
    payload = _valid_source()
    payload["steps"] = [{"action": "click", "target": {"text": "Create project"}}]

    with pytest.raises(ValidationError) as exc_info:
        JourneySourceV2.model_validate(payload)

    assert "text targets require product_contract" in str(exc_info.value)


def test_privacy_policy_blocks_llm_visual_checks_without_opt_in() -> None:
    """FR-037: LLM visual checks require explicit privacy opt-in."""
    payload = _valid_source()
    payload["visual_checks"] = [
        {
            "id": "llm-layout",
            "mode": "llm",
            "assertion": "visual_contract",
            "target": {"semantic_id": "project.success_card"},
            "prompt": "The success card is centered with readable text.",
        }
    ]
    payload["privacy"] = {"llm_allowed": False, "retention": "none"}

    with pytest.raises(ValidationError) as exc_info:
        JourneySourceV2.model_validate(payload)

    assert "LLM visual checks require privacy.llm_allowed" in str(exc_info.value)


def test_visual_check_native_layout_fields_are_typed() -> None:
    """FR-034: native layout checks keep deterministic measurement fields typed."""
    check = VisualCheck.model_validate(
        {
            "id": "title-margin",
            "mode": "native",
            "assertion": "min_margin",
            "target": {"semantic_id": "screen.title"},
            "min_px": 24,
        }
    )
    privacy = PrivacyPolicy.model_validate({"llm_allowed": True, "retention": "local"})

    assert check.min_px == 24
    assert privacy.llm_allowed is True
