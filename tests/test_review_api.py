"""Tests for the review API module (automatic hook integration)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from validator.semantic.review_api import review_plan_auto, review_spec_auto

SAMPLE_SPEC = """---
title: Test Feature
status: Draft
---

# Spec: Test

## Functional Requirements

| ID | Description |
|---|---|
| FR-001 | Test requirement |

## Acceptance Criteria

| ID | Description |
|---|---|
| AC-001 | Test criterion |
"""

SAMPLE_PLAN = """---
spec_ref: spec.md
---

# Plan: Test

### Step 1
**File:** `src/test.py` (new)
**FR covered:** FR-001
"""


class TestReviewSpecAuto:
    """Tests for review_spec_auto() graceful degradation."""

    def test_returns_result_when_provider_available(self, tmp_path: Path):
        feature_dir = tmp_path / "features" / "001-test"
        feature_dir.mkdir(parents=True)
        (feature_dir / "spec.md").write_text(SAMPLE_SPEC)

        response = json.dumps({"findings": [], "confidence": 5})
        with (
            patch("validator.llm_provider.is_available", return_value=True),
            patch("validator.llm_provider.call_llm", return_value=response),
        ):
            result = review_spec_auto(feature_dir)

        assert result is not None
        assert result.confidence == 5

    def test_returns_none_when_no_provider(self, tmp_path: Path):
        feature_dir = tmp_path / "features" / "001-test"
        feature_dir.mkdir(parents=True)
        (feature_dir / "spec.md").write_text(SAMPLE_SPEC)

        with patch("validator.llm_provider.is_available", return_value=False):
            result = review_spec_auto(feature_dir)

        assert result is None

    def test_returns_none_when_spec_missing(self, tmp_path: Path):
        feature_dir = tmp_path / "features" / "001-test"
        feature_dir.mkdir(parents=True)
        # No spec.md

        with patch("validator.llm_provider.is_available", return_value=True):
            result = review_spec_auto(feature_dir)

        assert result is None

    def test_returns_none_on_llm_error(self, tmp_path: Path):
        feature_dir = tmp_path / "features" / "001-test"
        feature_dir.mkdir(parents=True)
        (feature_dir / "spec.md").write_text(SAMPLE_SPEC)

        with (
            patch("validator.llm_provider.is_available", return_value=True),
            patch(
                "validator.llm_provider.call_llm",
                side_effect=RuntimeError("LLM timeout"),
            ),
        ):
            result = review_spec_auto(feature_dir)

        assert result is None


class TestReviewPlanAuto:
    """Tests for review_plan_auto() graceful degradation."""

    def test_returns_result_when_provider_available(self, tmp_path: Path):
        specs_root = tmp_path / ".specs"
        feature_dir = specs_root / "features" / "001-test"
        feature_dir.mkdir(parents=True)
        (feature_dir / "spec.md").write_text(SAMPLE_SPEC)
        (feature_dir / "plan.md").write_text(SAMPLE_PLAN)

        response = json.dumps({"findings": [], "confidence": 4})
        with (
            patch("validator.llm_provider.is_available", return_value=True),
            patch("validator.llm_provider.call_llm", return_value=response),
        ):
            result = review_plan_auto(feature_dir)

        assert result is not None
        assert result.confidence == 4

    def test_returns_none_when_no_provider(self, tmp_path: Path):
        feature_dir = tmp_path / "features" / "001-test"
        feature_dir.mkdir(parents=True)

        with patch("validator.llm_provider.is_available", return_value=False):
            result = review_plan_auto(feature_dir)

        assert result is None

    def test_returns_none_when_spec_missing(self, tmp_path: Path):
        feature_dir = tmp_path / "features" / "001-test"
        feature_dir.mkdir(parents=True)
        (feature_dir / "plan.md").write_text(SAMPLE_PLAN)
        # No spec.md

        with patch("validator.llm_provider.is_available", return_value=True):
            result = review_plan_auto(feature_dir)

        assert result is None

    def test_returns_none_when_plan_missing(self, tmp_path: Path):
        feature_dir = tmp_path / "features" / "001-test"
        feature_dir.mkdir(parents=True)
        (feature_dir / "spec.md").write_text(SAMPLE_SPEC)
        # No plan.md

        with patch("validator.llm_provider.is_available", return_value=True):
            result = review_plan_auto(feature_dir)

        assert result is None

    def test_returns_none_on_llm_error(self, tmp_path: Path):
        specs_root = tmp_path / ".specs"
        feature_dir = specs_root / "features" / "001-test"
        feature_dir.mkdir(parents=True)
        (feature_dir / "spec.md").write_text(SAMPLE_SPEC)
        (feature_dir / "plan.md").write_text(SAMPLE_PLAN)

        with (
            patch("validator.llm_provider.is_available", return_value=True),
            patch(
                "validator.llm_provider.call_llm",
                side_effect=RuntimeError("LLM timeout"),
            ),
        ):
            result = review_plan_auto(feature_dir)

        assert result is None
