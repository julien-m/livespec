---
created: 2026-10-15
feature: 093-configured-review-identity
title: 'Implementation Map: Configured Review Identity'
type: implementation
updated: 2026-10-15
---

# Implementation — Configured Review Identity

> Read [spec](spec.md) and [plan](plan.md). Non-UI feature; no visual baselines.

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| [FR-001: One resolution of model and budget](spec.md#fr-001) | `validator/semantic/review_identity_config.py` (new: `resolve_review_identity`, `review_budget`, `configured_model`), `validator/semantic/review_files.py` (`current_review_model`, `prepare_feature_review` budget), `validator/goal_review_identity.py` + `validator/goal_cli_actions.py` + `validator/goal_recompile.py` (goal render), `validator/progression_gate.py` (progressions), `validator/delivery/lane.py` + `validator/cli_commands/delivery_cmd.py` + `validator/delivery/goal.py` (delivery lane), `validator/delivery/revision.py`, `system/review-protocol.md`, `system/delivery-review.md`, `README.md` | `@spec FR-001: One resolution of model and budget — .specs/features/093-configured-review-identity/spec.md#fr-001` | ✅ Implemented | 2026-10-15 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 | `tests/test_review_identity_config.py` (resolution order, `review_model_required`, out-of-bounds budgets explicit and configured, goal render `spec-plan` without `--model`, `validate --progression implement`, `delivery lane` exit 2 instead of the 086 full lane, `delivery revision open`), `tests/test_delivery_review.py`, `tests/test_delivery_goal.py`, `tests/test_goal_review_roundtrip.py` | ✅ Pass 2026-10-15 |

## Decisions

- The function lives in `validator/semantic/review_identity_config.py`, not in `review_files.py` as the plan named: `validator/semantic/review_identity.py` already fingerprints prepared review contexts, and `review_files.py` stays a source loader. `current_review_model` (non-raising, used by review preparation) reads the configured model through the same `configured_model`.
- Resolution order: `--model`, else `review_model`, else the first `review_reviewers` entry (the pre-existing configured fallback, documented in the README), else `review_model_required`. Only a string names a model, stripped of surrounding spaces; blank values and the runtime placeholders `default` and `unknown` name none, also inside `review_reviewers`.
- Budget: `--review-max-chars`, else `review_max_chars` (default 60000); an integer from 1000 to 200000 (the bounds of the execution-mapping review budget), else `review_max_chars_out_of_bounds`. A boolean, float or string is refused, never clamped or ignored.
- A configuration that cannot be read or parsed (invalid YAML, non-UTF-8 bytes, a directory) is `review_config_invalid`, even with `--model`: resolution always reads the configured budget. Before 093 an explicit `--model` let `delivery lane` and `goal render` ignore it; round 0 of the delivery review found the resulting traceback.
- `flag_budget` (`validator/goal_review_identity.py`) refuses a goal `--review-max-chars=` flag that is not ASCII digits before the goal payload parses it (an existing traceback on `²`); the implement-goal lane turns such a flag into an out-of-bounds full lane.
- The bounds 1000 and 200000 duplicate `validator/execution_mapping.py`: sharing them would touch that 349-line file and bring its size debt into the feature conventions gate.
- Exit codes: `goal render` exits 2 (`review_model_required` replaces `reviewer_model_unresolved`), `livespec delivery lane|review prepare|review verify` exit 2 (usage), a progression and `livespec delivery revision open|close` exit 1 (blocked, error code in the payload).
- `delivery review prepare|verify` evaluate the lane, so they require a resolved model like `delivery lane`; two 086 tests that omitted `--model` now pass it.
- The implement goal's internal lane (`runtime_context.delivery_lane`, 086 FR-007) keeps the full lane with reason `review_model_required` instead of raising: `goal render` compiles once without a model, then binds the resolved model or refuses a review-bearing goal.
- The goal does not bind the configured budget into its flags: feature 089 removed the budget from staleness, and an absent `--review-max-chars` already means the configured budget; resolution still refuses a configured budget out of bounds before the goal is saved.
- Removing or editing `.specs/semantic/config.yaml` changes the `semantic_config` dependency of prepared reviews, so existing reviews become stale: unchanged behavior.
