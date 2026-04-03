# Plan: Fix plan-review control-flow bugs

## Step 1 — Add feature_filter to orchestrator (orchestrator.py)

Add `feature_filter: str | None = None` parameter to `run_plan_review()`. Filter the feature loop. If filter is set but no feature matches, append error to `check_result.errors`.

**File:** `validator/orchestrator.py`
**Lines:** 140-211

## Step 2 — Fix CLI: resolve PATH, errors-as-blocking, warn_only (cli.py)

1. Add `_resolve_feature_filter()` helper after `_find_specs_root()`
2. Call it and pass result to `run_plan_review(feature_filter=...)`
3. After errors display loop (line 187-188): `if review_result.errors: has_blocking = True`
4. Replace exit line 196: `raise typer.Exit(0 if warn_only else (1 if has_blocking else 0))`

**File:** `validator/cli.py`
**Lines:** 18-196

## Step 3 — Add tests (test_plan_review.py)

Add test class `TestPlanReviewCLI` with:
- `test_errors_cause_exit_1` — mock review_plan to raise, verify exit 1
- `test_errors_with_warn_only_exit_0` — same but with warn_only, verify exit 0
- `test_blocking_with_warn_only_exit_0` — blocking finding + warn_only → exit 0
- `test_feature_filter_scopes_review` — verify only matching feature is reviewed
- `test_feature_filter_nonexistent_errors` — filter with no match → error appended
- `test_resolve_feature_filter_from_spec_path` — unit test for resolver
- `test_resolve_feature_filter_from_dir` — unit test for resolver
- `test_resolve_feature_filter_none` — no path → None

**File:** `tests/test_plan_review.py`

## Dependencies

Steps 1 and 2 are independent code changes but Step 2 depends on Step 1's new parameter.
Step 3 depends on both Steps 1 and 2.

Execute sequentially: Step 1 → Step 2 → Step 3 → verify all tests pass.
