---
created: 2026-10-13
feature: 086-risk-proportional-delivery
title: 'Implementation Map: Risk-Proportional Delivery'
type: implementation
updated: 2026-10-13
---

# Implementation — Risk-Proportional Delivery

> Read [spec](spec.md) and [plan](plan.md). Non-UI feature (CLI, goal and skills); no visual baselines.

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| [FR-001: delivery command group](spec.md#fr-001) | `validator/cli_commands/delivery_cmd.py`, `validator/cli_commands/__init__.py` | `@spec FR-001: Delivery command group` | ✅ Implemented | 2026-10-13 |
| [FR-002: QE classification and lane](spec.md#fr-002) | `validator/delivery/lane.py` | `@spec FR-002: QE classification and lane rule` | ✅ Implemented | 2026-10-13 |
| [FR-003: spec review currency](spec.md#fr-003) | `validator/delivery/lane.py::spec_review_state` | `@spec FR-003: Reviewed classification only` | ✅ Implemented | 2026-10-13 |
| [FR-004: review scope](spec.md#fr-004) | `validator/delivery/review.py::prepare_scope`, `validator/bugfix/diff.py::resolve_commit` | `@spec FR-004: Complete feature diff scope` | ✅ Implemented | 2026-10-13 |
| [FR-005: record and round cap](spec.md#fr-005) | `validator/delivery/review.py::record_report` | `@spec FR-005: Record a complete-scope report under the round cap` | ✅ Implemented | 2026-10-13 |
| [FR-006: verify](spec.md#fr-006) | `validator/delivery/review.py::verify_review` | `@spec FR-006: Current PASS for every required kind` | ✅ Implemented | 2026-10-13 |
| [FR-007: goal integration](spec.md#fr-007) | `validator/goal_payload.py`, `goal_inventory.py`, `goal_contract_model.py`, `goal_tasks.py`, `goal_outcome.py`, `goal_generic_evidence.py` | `@spec FR-007: Delivery lane in the implement goal`, `@spec FR-007: One end-of-feature delivery review task`, `@spec FR-007: The goal re-verifies the delivery review receipt` | ✅ Implemented | 2026-10-13 |
| [FR-009: reviewer QE assessment](spec.md#fr-009) | `validator/semantic/review_contract.py::QeAssessment`, `validator/delivery/lane_review.py::apply_review`, spec-specify skill, `system/review-protocol.md`, `system/delivery-review.md` | `@spec FR-009: Contestable criticality`, `@spec FR-009: Native quality review instructions`, `@spec FR-009: Reviewed QE and contestable criticality`, `@spec FR-009: Reviewer QE assessment` | ✅ Implemented | 2026-10-13 |
| [FR-008: skills, hook, protocol](spec.md#fr-008) | `system/delivery-review.md`, `system/hooks/after-implement-step.md`, `system/hooks.md`, spec-implement, spec-feature and spec-ship skills, both spec-system copies | `@spec FR-008: Delivery lanes in the universal rules`, `@spec FR-008: End-of-feature delivery review protocol`, `@spec FR-008: Lane-driven step gate and one final review`, `@spec FR-008: No review per step`, `@spec FR-008: One delivery review of the complete diff` | ✅ Implemented | 2026-10-13 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001, AC-002 | `tests/test_delivery_lane.py` | ✅ Pass 2026-10-13 |
| AC-003 to AC-006 | `tests/test_delivery_review.py` | ✅ Pass 2026-10-13 |
| AC-007 | `tests/test_delivery_goal.py` | ✅ Pass 2026-10-13 |
| AC-008 | `tests/test_delivery_docs.py` | ✅ Pass 2026-10-13 |
| AC-009 | `tests/test_delivery_lane_review.py` | ✅ Pass 2026-10-13 |

## Files Created/Modified

| File | Change |
|---|---|
| `validator/delivery/lane.py` | QE parsing, lane rule with every reason, spec review currency. |
| `validator/delivery/review.py` | Report model, scope, record with round cap, verify. |
| `validator/cli_commands/delivery_cmd.py` | `livespec delivery lane` and `delivery review prepare/record/verify`. |
| `validator/goal_*.py` | `lane-light`/`lane-full` branches, `delivery.review` task and its evidence check. |
| `system/delivery-review.md` | End-of-feature review protocol (native agents, effort high, no audit skill or Codex). |
| `system/hooks/after-implement-step.md` | Checks only per step. |
| `.agent-sync/skills/spec-implement/SKILL.md` | STEP 0.95 lane, step gate without reviewers, Phase 6.8 delivery review. |
| `validator/delivery/lane_review.py` | Reviewed QE union and contested criticality. |
| `tests/delivery_support.py`, `tests/test_delivery_*.py` | Fixtures and 43 tests. |
