# LLM Plan Review — Implementation Plan

## Steps

### Step 1: Extend SemanticConfig
**File:** `validator/semantic/config.py` (modify)
**What:** Add `review_reviewers: list[str]` and `review_confidence_threshold: float` fields to `SemanticConfig` dataclass.

### Step 2: Create plan_review.py
**File:** `validator/semantic/plan_review.py` (new)
**What:** Core module with:
- `ReviewFinding` dataclass (category, severity, description, suggestion)
- `PlanReviewResult` dataclass (findings, reviewer_model, confidence, complexity)
- `PlanComplexity` dataclass (fr_count, file_count, ac_count, diagram_count)
- `_REVIEW_PROMPT` template — adversarial review prompt
- `_REVIEW_SCHEMA` — JSON schema for structured output
- `review_plan(spec_content, plan_content, stack_content, constitution_content, model) -> PlanReviewResult`
- `compute_plan_complexity(plan_content) -> PlanComplexity`
- `log_review(result, plan_dir)` — saves JSON to `{plan_dir}/reviews/`

### Step 3: Add CLI flag
**File:** `validator/cli.py` (modify)
**What:** Add `--plan-review` option. When set:
1. Check LLM provider available
2. Load semantic config for reviewer models
3. Find features with spec.md + plan.md
4. Run `review_plan()` for each
5. Display findings
6. Exit 1 if any blocking findings

### Step 4: Update spec.plan command
**File:** `commands/plan.md` (modify)
**What:** Add `--review` flag to flags table and add review step between plan generation and "Present for Approval" (Step 10). Advisory only.

### Step 5: Write tests
**File:** `tests/test_plan_review.py` (new)
**What:** Tests for:
- `compute_plan_complexity()` with various plan content
- `review_plan()` with mocked LLM provider
- `log_review()` file creation
- `ReviewFinding` and `PlanReviewResult` construction
- Edge cases: empty plan, no AC, no FR

## Execution: Subagent-Driven

Steps 1-2 are independent and can be parallelized.
Step 3 depends on Step 2 (imports plan_review).
Step 4 is independent.
Step 5 depends on Steps 1-2.
