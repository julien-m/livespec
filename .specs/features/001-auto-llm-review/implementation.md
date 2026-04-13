---
type: implementation
feature: 001-auto-llm-review
created: 2026-04-13
updated: 2026-04-13
---

# Implementation Map: Auto LLM Review

## FR/AC to Source Mapping

| Requirement | Source File | @spec Anchor | Status | Date |
|---|---|---|---|---|
| [FR-001: CLI flag routing](spec.md#fr-001) | validator/cli.py | `@spec FR-001: CLI flag routing — .specs/features/001-auto-llm-review/spec.md#fr-001` | Implemented | 2026-04-13 |
| [FR-002: Spec review prompt](spec.md#fr-002) | validator/semantic/spec_review.py | `@spec FR-002: Build spec review prompt — .specs/features/001-auto-llm-review/spec.md#fr-002` | Implemented | 2026-04-13 |
| [FR-003: LLM call with schema](spec.md#fr-003) | validator/semantic/spec_review.py, validator/orchestrator.py | `@spec FR-003: Send to LLM, FR-004: Parse ReviewFinding` | Implemented | 2026-04-13 |
| [FR-004: Parse into ReviewFinding](spec.md#fr-004) | validator/semantic/spec_review.py | `@spec FR-003: Send to LLM, FR-004: Parse ReviewFinding` | Implemented | 2026-04-13 |
| [FR-005: Plan review CLI alias](spec.md#fr-005) | validator/cli.py | `@spec FR-005: Plan review CLI alias — .specs/features/001-auto-llm-review/spec.md#fr-005` | Implemented | 2026-04-13 |
| [FR-006: Plan review prompt](spec.md#fr-006) | validator/semantic/plan_review.py | (pre-existing) | Implemented | Pre-existing |
| [FR-007: Exit code logic](spec.md#fr-007) | validator/cli.py | `@spec FR-007: Exit code logic — .specs/features/001-auto-llm-review/spec.md#fr-007` | Implemented | 2026-04-13 |
| [FR-008: JSON output](spec.md#fr-008) | validator/cli.py | `@spec FR-008: JSON output — .specs/features/001-auto-llm-review/spec.md#fr-008` | Implemented | 2026-04-13 |
| [FR-009: Provider error](spec.md#fr-009) | validator/exceptions.py, validator/cli.py | `@spec FR-009: Domain exception for spec review` | Implemented | 2026-04-13 |
| [FR-010: Python API for hooks](spec.md#fr-010) | validator/semantic/review_api.py | `@spec FR-010: Python API, FR-011: Silent skip` | Implemented | 2026-04-13 |
| [FR-011: Silent skip logic](spec.md#fr-011) | validator/semantic/review_api.py | `@spec FR-010: Python API, FR-011: Silent skip` | Implemented | 2026-04-13 |

## AC Coverage

| AC | Satisfied By | Status |
|---|---|---|
| AC-001 | `--review-spec` flag in cli.py | Implemented |
| AC-002 | `_SPEC_REVIEW_PROMPT` in spec_review.py | Implemented |
| AC-003 | `--review-plan` alias in cli.py | Implemented |
| AC-004 | Pre-existing plan_review.py prompt | Implemented |
| AC-005 | Both reviews use `call_llm()` from llm_provider.py | Implemented |
| AC-006 | Default exit 0 in advisory mode | Implemented |
| AC-007 | `--strict` flag exits 1 on blocking findings | Implemented |
| AC-008 | ReviewFinding has category, severity, description, suggestion | Implemented |
| AC-009 | `--format json` outputs valid JSON | Implemented |
| AC-010 | Clear error message when no provider | Implemented |
| AC-011 | `review_spec_auto()` in review_api.py | Implemented |
| AC-012 | `review_plan_auto()` in review_api.py | Implemented |
| AC-013 | `--no-review` flag in cli.py | Implemented |
| AC-014 | Graceful degradation in review_api.py | Implemented |

## Files Created

| File | Purpose |
|---|---|
| validator/semantic/spec_review.py | Spec review core logic (prompt, schema, parsing) |
| validator/semantic/review_api.py | High-level API for hook integration |
| tests/test_spec_review.py | Unit tests for spec review module |
| tests/test_review_api.py | Unit tests for review API module |

## Files Modified

| File | Changes |
|---|---|
| validator/cli.py | Added --review-spec, --review-plan alias, --model, --no-review flags; shared display helpers |
| validator/orchestrator.py | Added SpecReviewEntry, SpecReviewCheckResult, run_spec_review() |
| validator/exceptions.py | Added SpecReviewError exception class |
| tests/test_cli.py | Added 5 CLI review tests |
