"""Tests for the LLM spec review module."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from validator.coherence.violation import Severity
from validator.semantic.plan_review import ReviewFinding
from validator.semantic.spec_review import (
    SpecReviewResult,
    compute_spec_metrics,
    review_spec,
)

SAMPLE_SPEC = """---
title: User Authentication
status: Draft
---

# Spec: User Authentication

### Story 1 -- User login
### Story 2 -- User logout

## Functional Requirements

| ID | Description | AC | Priority |
|---|---|---|---|
| FR-001 | User login with email/password | AC-001 | Must |
| FR-002 | User logout | AC-002 | Must |
| FR-003 | JWT token management | AC-003 | Must |

## Acceptance Criteria

| ID | Description |
|---|---|
| AC-001 | User can log in with valid credentials |
| AC-002 | User can log out and session is destroyed |
| AC-003 | Expired tokens are rejected |

## Edge Cases

- Empty email field submitted
- Password exceeds max length
- Concurrent login from two devices
"""


class TestComputeSpecMetrics:
    """Tests for compute_spec_metrics()."""

    def test_counts_fr_references(self):
        result = compute_spec_metrics(SAMPLE_SPEC)
        assert result["fr_count"] == 3

    def test_counts_ac_references(self):
        result = compute_spec_metrics(SAMPLE_SPEC)
        assert result["ac_count"] == 3

    def test_counts_stories(self):
        result = compute_spec_metrics(SAMPLE_SPEC)
        assert result["story_count"] == 2

    def test_counts_edge_cases(self):
        result = compute_spec_metrics(SAMPLE_SPEC)
        assert result["edge_case_count"] == 3

    def test_empty_spec(self):
        result = compute_spec_metrics("")
        assert result == {
            "fr_count": 0,
            "ac_count": 0,
            "story_count": 0,
            "edge_case_count": 0,
        }

    def test_spec_without_edge_cases(self):
        content = "# Spec\n\n## Functional Requirements\n\nFR-001, FR-002"
        result = compute_spec_metrics(content)
        assert result["edge_case_count"] == 0
        assert result["fr_count"] == 2

    def test_deduplicates_fr_references(self):
        content = "FR-001 and FR-001 again. FR-002 once."
        result = compute_spec_metrics(content)
        assert result["fr_count"] == 2


class TestSpecReviewResult:
    """Tests for SpecReviewResult dataclass."""

    def test_defaults(self):
        result = SpecReviewResult()
        assert result.findings == []
        assert result.reviewer_model == ""
        assert result.confidence == 0
        assert result.spec_metrics == {}

    def test_with_findings(self):
        finding = ReviewFinding("testability", Severity.WARNING, "desc", "fix")
        result = SpecReviewResult(
            findings=[finding],
            reviewer_model="google/gemini-3.1-pro",
            confidence=4,
            spec_metrics={"fr_count": 3},
        )
        assert len(result.findings) == 1
        assert result.reviewer_model == "google/gemini-3.1-pro"


class TestReviewSpec:
    """Tests for review_spec() with mocked LLM."""

    def _mock_response(
        self, findings: list[dict], confidence: int = 4
    ) -> str:
        return json.dumps({"findings": findings, "confidence": confidence})

    def test_returns_findings_from_llm(self):
        response = self._mock_response([
            {
                "category": "testability",
                "severity": "blocking",
                "description": "FR-002 uses vague verb 'manages'",
                "suggestion": "Replace with specific measurable outcome",
            },
        ])

        with patch("validator.llm_provider.call_llm", return_value=response):
            result = review_spec(
                spec_content=SAMPLE_SPEC,
                model="test/model",
            )

        assert len(result.findings) == 1
        assert result.findings[0].severity == Severity.ERROR
        assert result.findings[0].category == "testability"
        assert result.reviewer_model == "test/model"
        assert result.confidence == 4

    def test_maps_severity_correctly(self):
        response = self._mock_response([
            {"category": "a", "severity": "blocking", "description": "x", "suggestion": "y"},
            {"category": "b", "severity": "warning", "description": "x", "suggestion": "y"},
            {"category": "c", "severity": "info", "description": "x", "suggestion": "y"},
        ])

        with patch("validator.llm_provider.call_llm", return_value=response):
            result = review_spec(SAMPLE_SPEC)

        assert result.findings[0].severity == Severity.ERROR
        assert result.findings[1].severity == Severity.WARNING
        assert result.findings[2].severity == Severity.INFO

    def test_empty_findings(self):
        response = self._mock_response([], confidence=5)

        with patch("validator.llm_provider.call_llm", return_value=response):
            result = review_spec(SAMPLE_SPEC)

        assert len(result.findings) == 0
        assert result.confidence == 5

    def test_includes_spec_metrics(self):
        response = self._mock_response([])

        with patch("validator.llm_provider.call_llm", return_value=response):
            result = review_spec(SAMPLE_SPEC)

        assert result.spec_metrics["fr_count"] == 3
        assert result.spec_metrics["story_count"] == 2

    def test_default_model_label(self):
        response = self._mock_response([])

        with patch("validator.llm_provider.call_llm", return_value=response):
            result = review_spec(SAMPLE_SPEC, model=None)

        assert result.reviewer_model == "default"

    def test_raises_on_invalid_json(self):
        with (
            patch("validator.llm_provider.call_llm", return_value="not json"),
            pytest.raises(json.JSONDecodeError),
        ):
            review_spec(SAMPLE_SPEC)

    def test_passes_model_to_call_llm(self):
        response = self._mock_response([])

        with patch("validator.llm_provider.call_llm", return_value=response) as mock:
            review_spec(SAMPLE_SPEC, model="google/gemini-3.1-pro")

        _, kwargs = mock.call_args
        assert kwargs.get("model") == "google/gemini-3.1-pro"

    def test_truncates_long_spec(self):
        long_spec = "x" * 20000
        response = self._mock_response([])

        with patch("validator.llm_provider.call_llm", return_value=response) as mock:
            review_spec(long_spec)

        prompt = mock.call_args[0][0]
        # Prompt should contain truncated content (8000 chars max)
        assert len(prompt) < 20000
