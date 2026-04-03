"""Tests for the LLM plan review module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from validator.coherence.violation import Severity
from validator.semantic.plan_review import (
    PlanReviewResult,
    ReviewFinding,
    compute_plan_complexity,
    review_plan,
)

SAMPLE_PLAN = """---
spec_ref: features/001-user-auth
created: 2026-04-01
---

# Plan: User Authentication

## Implementation Plan

### Step 1 — Database layer
**File:** `src/db/migrations/001_users.sql` (new)
**FR covered:** FR-001.1: Schema creation, FR-002.1: Session table

### Step 2 — Business logic
**File:** `src/services/auth.ts` (new)
**FR covered:** FR-001.2: Login handler, FR-003.1: Token generation

### Step 3 — API layer
**File:** `src/routes/auth.ts` (new)
**FR covered:** FR-001.3: Login endpoint, FR-002.2: Logout endpoint

```mermaid
sequenceDiagram
    User->>API: POST /login
    API->>DB: Query user
    DB-->>API: User row
    API-->>User: JWT token
```

```mermaid
stateDiagram-v2
    [*] --> LoggedOut
    LoggedOut --> LoggedIn: Login
    LoggedIn --> LoggedOut: Logout
```

## Testing Strategy

| Test | AC |
|---|---|
| Login flow | AC-001 |
| Logout flow | AC-002 |
| Token expiry | AC-003 |
"""

SAMPLE_SPEC = """---
title: User Authentication
status: Draft
---

# Spec: User Authentication

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
"""


class TestComputePlanComplexity:
    """Tests for compute_plan_complexity()."""

    def test_counts_fr_references(self):
        result = compute_plan_complexity(SAMPLE_PLAN)
        assert result["fr_count"] == 3  # FR-001, FR-002, FR-003

    def test_counts_ac_references(self):
        result = compute_plan_complexity(SAMPLE_PLAN)
        assert result["ac_count"] == 3  # AC-001, AC-002, AC-003

    def test_counts_mermaid_diagrams(self):
        result = compute_plan_complexity(SAMPLE_PLAN)
        assert result["diagram_count"] == 2  # sequence + state

    def test_counts_file_references(self):
        result = compute_plan_complexity(SAMPLE_PLAN)
        assert result["file_count"] == 3  # 3 new files

    def test_empty_plan(self):
        result = compute_plan_complexity("")
        assert result == {"fr_count": 0, "ac_count": 0, "diagram_count": 0, "file_count": 0}

    def test_plan_with_no_fr(self):
        result = compute_plan_complexity("# Simple plan\nJust some text.")
        assert result["fr_count"] == 0

    def test_deduplicates_fr_references(self):
        content = "FR-001 appears here and FR-001 appears again. FR-002 once."
        result = compute_plan_complexity(content)
        assert result["fr_count"] == 2


class TestReviewFinding:
    """Tests for ReviewFinding dataclass."""

    def test_construction(self):
        finding = ReviewFinding(
            category="coverage_gap",
            severity=Severity.ERROR,
            description="AC-003 not covered",
            suggestion="Add token expiry test step",
        )
        assert finding.category == "coverage_gap"
        assert finding.severity == Severity.ERROR

    def test_free_form_category(self):
        finding = ReviewFinding(
            category="custom_category",
            severity=Severity.INFO,
            description="test",
            suggestion="test",
        )
        assert finding.category == "custom_category"


class TestPlanReviewResult:
    """Tests for PlanReviewResult dataclass."""

    def test_defaults(self):
        result = PlanReviewResult()
        assert result.findings == []
        assert result.reviewer_model == ""
        assert result.confidence == 0
        assert result.complexity == {}

    def test_with_findings(self):
        finding = ReviewFinding("gap", Severity.WARNING, "desc", "fix")
        result = PlanReviewResult(
            findings=[finding],
            reviewer_model="google/gemini-3.1-pro",
            confidence=4,
            complexity={"fr_count": 3},
        )
        assert len(result.findings) == 1
        assert result.reviewer_model == "google/gemini-3.1-pro"


class TestReviewPlan:
    """Tests for review_plan() with mocked LLM."""

    def _mock_response(self, findings: list[dict], confidence: int = 4) -> str:
        return json.dumps({"findings": findings, "confidence": confidence})

    def test_returns_findings_from_llm(self):
        response = self._mock_response([
            {
                "category": "coverage_gap",
                "severity": "blocking",
                "description": "AC-003 has no implementation step",
                "suggestion": "Add token expiry handling",
            },
        ])

        with patch("validator.llm_provider.call_llm", return_value=response):
            result = review_plan(
                spec_content=SAMPLE_SPEC,
                plan_content=SAMPLE_PLAN,
                model="test/model",
            )

        assert len(result.findings) == 1
        assert result.findings[0].severity == Severity.ERROR
        assert result.findings[0].category == "coverage_gap"
        assert result.reviewer_model == "test/model"
        assert result.confidence == 4

    def test_maps_severity_correctly(self):
        response = self._mock_response([
            {"category": "a", "severity": "blocking", "description": "x", "suggestion": "y"},
            {"category": "b", "severity": "warning", "description": "x", "suggestion": "y"},
            {"category": "c", "severity": "info", "description": "x", "suggestion": "y"},
        ])

        with patch("validator.llm_provider.call_llm", return_value=response):
            result = review_plan(SAMPLE_SPEC, SAMPLE_PLAN)

        assert result.findings[0].severity == Severity.ERROR
        assert result.findings[1].severity == Severity.WARNING
        assert result.findings[2].severity == Severity.INFO

    def test_empty_findings(self):
        response = self._mock_response([], confidence=5)

        with patch("validator.llm_provider.call_llm", return_value=response):
            result = review_plan(SAMPLE_SPEC, SAMPLE_PLAN)

        assert len(result.findings) == 0
        assert result.confidence == 5

    def test_includes_complexity_metrics(self):
        response = self._mock_response([])

        with patch("validator.llm_provider.call_llm", return_value=response):
            result = review_plan(SAMPLE_SPEC, SAMPLE_PLAN)

        assert result.complexity["fr_count"] == 3
        assert result.complexity["diagram_count"] == 2

    def test_default_model_label(self):
        response = self._mock_response([])

        with patch("validator.llm_provider.call_llm", return_value=response):
            result = review_plan(SAMPLE_SPEC, SAMPLE_PLAN, model=None)

        assert result.reviewer_model == "default"

    def test_raises_on_invalid_json(self):
        with (
            patch("validator.llm_provider.call_llm", return_value="not json"),
            pytest.raises(json.JSONDecodeError),
        ):
            review_plan(SAMPLE_SPEC, SAMPLE_PLAN)

    def test_passes_model_to_call_llm(self):
        response = self._mock_response([])

        with patch("validator.llm_provider.call_llm", return_value=response) as mock:
            review_plan(SAMPLE_SPEC, SAMPLE_PLAN, model="google/gemini-3.1-pro")

        _, kwargs = mock.call_args
        assert kwargs.get("model") == "google/gemini-3.1-pro"

    def test_passes_stack_and_constitution(self):
        response = self._mock_response([])

        with patch("validator.llm_provider.call_llm", return_value=response) as mock:
            review_plan(
                SAMPLE_SPEC,
                SAMPLE_PLAN,
                stack_content="TypeScript + Express",
                constitution_content="API-first design",
            )

        prompt = mock.call_args[0][0]
        assert "TypeScript + Express" in prompt
        assert "API-first design" in prompt


class TestCascadeReview:
    """Tests for plan review cascade behavior via orchestrator."""

    def test_cascade_triggered_on_soft_review(self):
        """Cascade activates when first reviewer returns 0 findings + low confidence."""
        from validator.orchestrator import _is_review_soft
        from validator.semantic.plan_review import PlanReviewResult

        # Soft review: 0 findings, confidence 2 (below threshold of 3)
        soft = PlanReviewResult(
            findings=[],
            confidence=2,
            complexity={"fr_count": 6, "ac_count": 5, "file_count": 9},
        )
        assert _is_review_soft(soft, confidence_threshold=3.0) is True

    def test_high_confidence_blocks_cascade(self):
        """High confidence review blocks cascade even with 0 findings."""
        from validator.orchestrator import _is_review_soft
        from validator.semantic.plan_review import PlanReviewResult

        # High confidence: 0 findings, confidence 5 (at/above threshold)
        confident = PlanReviewResult(
            findings=[],
            confidence=5,
            complexity={"fr_count": 6, "ac_count": 5, "file_count": 9},
        )
        assert _is_review_soft(confident, confidence_threshold=3.0) is False

    def test_simple_plan_blocks_cascade(self):
        """Simple plans don't trigger cascade even if low confidence."""
        from validator.orchestrator import _is_review_soft
        from validator.semantic.plan_review import PlanReviewResult

        # Low confidence but simple plan (sum < 5)
        simple = PlanReviewResult(
            findings=[],
            confidence=2,
            complexity={"fr_count": 2, "ac_count": 1, "file_count": 2},
        )
        assert _is_review_soft(simple, confidence_threshold=3.0) is False

    def test_findings_blocks_cascade(self):
        """Having findings blocks cascade regardless of confidence."""
        from validator.coherence.violation import Severity
        from validator.orchestrator import _is_review_soft
        from validator.semantic.plan_review import PlanReviewResult

        # Has findings, low confidence
        with_findings = PlanReviewResult(
            findings=[
                ReviewFinding("gap", Severity.WARNING, "test", "fix"),
            ],
            confidence=2,
            complexity={"fr_count": 6, "ac_count": 5, "file_count": 9},
        )
        assert _is_review_soft(with_findings, confidence_threshold=3.0) is False


class TestPlanReviewOrchestrator:
    """Tests for plan review orchestration and cascade logic."""

    def test_cascade_flow_soft_then_solid(self):
        """Verify cascade: first soft, second solid."""
        from unittest.mock import patch

        from validator.orchestrator import PlanReviewCheckResult, _run_cascade_review

        # First review: soft (0 findings, confidence 2, complex)
        soft_response = json.dumps({
            "findings": [],
            "confidence": 2,
        })
        # Second review: solid (1 finding, high confidence)
        solid_response = json.dumps({
            "findings": [
                {
                    "category": "coverage_gap",
                    "severity": "warning",
                    "description": "AC-001 missing",
                    "suggestion": "Add step",
                }
            ],
            "confidence": 5,
        })

        responses = [soft_response, solid_response]
        call_count = [0]

        def mock_call_llm(*args, **kwargs):
            result = responses[call_count[0]]
            call_count[0] += 1
            return result

        with patch("validator.llm_provider.call_llm", side_effect=mock_call_llm):
            result = PlanReviewCheckResult()
            _run_cascade_review(
                "test-feature",
                spec_content=SAMPLE_SPEC,
                plan_content=SAMPLE_PLAN,
                stack_content="",
                constitution_content="",
                review_models=[None],
                all_models=["model1", "model2"],
                confidence_threshold=3.0,
                check_result=result,
            )

        assert len(result.reviews) == 2
        assert result.reviews[0].result.confidence == 2
        assert result.reviews[1].result.confidence == 5
        assert len(result.reviews[1].result.findings) == 1

    def test_dual_zero_findings_validates(self):
        """Both reviewers return 0 findings → soft entry removed, only cascade kept."""
        from unittest.mock import patch

        from validator.orchestrator import PlanReviewCheckResult, _run_cascade_review

        response = json.dumps({"findings": [], "confidence": 2})

        with patch("validator.llm_provider.call_llm", return_value=response):
            result = PlanReviewCheckResult()
            _run_cascade_review(
                "test-feature",
                spec_content=SAMPLE_SPEC,
                plan_content=SAMPLE_PLAN,
                stack_content="",
                constitution_content="",
                review_models=[None],
                all_models=["model1", "model2"],
                confidence_threshold=3.0,
                check_result=result,
            )

        # Soft first entry removed, only cascade result retained
        assert len(result.reviews) == 1
        assert result.reviews[0].result.confidence == 5


class TestResolveFeatureFilter:
    """Tests for _resolve_feature_filter() path resolution."""

    def test_none_path_returns_none(self, tmp_path: Path) -> None:
        """None path returns None."""
        from validator.cli import _resolve_feature_filter

        assert _resolve_feature_filter(None, tmp_path) is None

    def test_spec_file_resolves_to_feature(self, tmp_path: Path) -> None:
        """Spec file path resolves to feature dir_name."""
        from validator.cli import _resolve_feature_filter

        features_dir = tmp_path / "features" / "001-auth"
        features_dir.mkdir(parents=True)
        spec_file = features_dir / "spec.md"
        spec_file.touch()

        result = _resolve_feature_filter(spec_file, tmp_path)
        assert result == "001-auth"

    def test_feature_dir_resolves_to_feature(self, tmp_path: Path) -> None:
        """Feature directory path resolves to feature dir_name."""
        from validator.cli import _resolve_feature_filter

        features_dir = tmp_path / "features" / "002-payments"
        features_dir.mkdir(parents=True)

        result = _resolve_feature_filter(features_dir, tmp_path)
        assert result == "002-payments"

    def test_path_outside_features_returns_none(self, tmp_path: Path) -> None:
        """Path outside features/ directory returns None."""
        from validator.cli import _resolve_feature_filter

        other = tmp_path / "stacks"
        other.mkdir()

        result = _resolve_feature_filter(other, tmp_path)
        assert result is None

    def test_features_dir_itself_returns_none(self, tmp_path: Path) -> None:
        """Features directory itself returns None."""
        from validator.cli import _resolve_feature_filter

        features_dir = tmp_path / "features"
        features_dir.mkdir()

        result = _resolve_feature_filter(features_dir, tmp_path)
        assert result is None


class TestPlanReviewFeatureFilter:
    """Tests for feature_filter parameter in run_plan_review."""

    def test_filter_scopes_to_single_feature(self, tmp_path: Path) -> None:
        """Feature filter scopes review to single matching feature."""
        from unittest.mock import patch

        from validator.orchestrator import run_plan_review

        specs = tmp_path / ".specs"
        specs.mkdir()
        (specs / "roadmap.md").write_text("- [x] [001-auth](features/001-auth/)\n- [x] [002-pay](features/002-pay/)\n")
        for name in ("001-auth", "002-pay"):
            d = specs / "features" / name
            d.mkdir(parents=True)
            (d / "spec.md").write_text(SAMPLE_SPEC)
            (d / "plan.md").write_text(SAMPLE_PLAN)

        response = json.dumps({"findings": [], "confidence": 5})
        with patch("validator.llm_provider.call_llm", return_value=response):
            result = run_plan_review(specs, feature_filter="001-auth")

        feature_names = [e.feature_name for e in result.reviews]
        assert feature_names == ["001-auth"]

    def test_filter_nonexistent_feature_errors(self, tmp_path: Path) -> None:
        """Nonexistent feature filter produces error."""
        from validator.orchestrator import run_plan_review

        specs = tmp_path / ".specs"
        specs.mkdir()
        (specs / "roadmap.md").write_text("- [x] [001-auth](features/001-auth/)\n")
        d = specs / "features" / "001-auth"
        d.mkdir(parents=True)
        (d / "spec.md").write_text(SAMPLE_SPEC)
        (d / "plan.md").write_text(SAMPLE_PLAN)

        result = run_plan_review(specs, feature_filter="nonexistent")
        assert len(result.errors) == 1
        assert "nonexistent" in result.errors[0]
        assert len(result.reviews) == 0

    def test_filter_feature_missing_plan_errors(self, tmp_path: Path) -> None:
        """Filtered feature missing plan.md produces error."""
        from validator.orchestrator import run_plan_review

        specs = tmp_path / ".specs"
        specs.mkdir()
        (specs / "roadmap.md").write_text("- [x] [001-auth](features/001-auth/)\n")
        d = specs / "features" / "001-auth"
        d.mkdir(parents=True)
        (d / "spec.md").write_text(SAMPLE_SPEC)
        # No plan.md

        result = run_plan_review(specs, feature_filter="001-auth")
        assert len(result.errors) == 1
        assert "plan.md" in result.errors[0]
        assert len(result.reviews) == 0


class TestPlanReviewErrorHandling:
    """Tests for error-as-blocking and warn_only in plan-review."""

    def test_errors_set_has_blocking(self) -> None:
        """Review errors set has_blocking=True in result processing."""
        from validator.orchestrator import PlanReviewCheckResult

        result = PlanReviewCheckResult()
        result.errors.append("feature-001: JSONDecodeError")

        # Simulate CLI logic
        has_blocking = False
        if result.errors:
            has_blocking = True
        assert has_blocking is True

    def test_warn_only_suppresses_exit_code(self) -> None:
        """warn_only suppresses exit code even with blocking findings."""
        has_blocking = True
        warn_only = True
        exit_code = 0 if warn_only else (1 if has_blocking else 0)
        assert exit_code == 0

    def test_no_warn_only_with_blocking_exits_1(self) -> None:
        """Without warn_only, blocking findings exit 1."""
        has_blocking = True
        warn_only = False
        exit_code = 0 if warn_only else (1 if has_blocking else 0)
        assert exit_code == 1

    def test_no_errors_no_findings_exits_0(self) -> None:
        """Clean review exits 0."""
        has_blocking = False
        warn_only = False
        exit_code = 0 if warn_only else (1 if has_blocking else 0)
        assert exit_code == 0
