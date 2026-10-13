---
created: 2026-10-10
feature: 081-lightweight-outcome-goals
title: 'Implementation Map: Lightweight Outcome-Based Goals'
type: implementation
updated: 2026-10-10
---

# Implementation — Lightweight Outcome-Based Goals

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `validator/goal_outcome.py`, `validator/goal_receipt_evidence.py`, `validator/goal_payload.py` | FR-001 | ✅ Implemented | 2026-10-10 |
| FR-002 | `validator/goal_tasks.py`, `validator/goal_payload.py`, `validator/goal_render.py`, `validator/evidence_policy.py` | FR-002 | ✅ Implemented | 2026-10-10 |
| FR-003 | `validator/goal_outcome.py`, `.agent-sync/skills/spec-feature/SKILL.md` | FR-003 | ✅ Implemented | 2026-10-10 |
| FR-004 | `system/anti-drift-block.md`, `.agent-sync/skills/spec-feature/SKILL.md` | FR-009 | ✅ Implemented | 2026-10-10 |
| FR-005 | `validator/goal_recompile.py`, `validator/goal_cli_actions.py`, `validator/goal_cli_inputs.py`, `validator/goal_compile.py`, `validator/goal_pairing.py` | FR-005 | ✅ Implemented | 2026-10-10 |
| FR-006 | `validator/goal_tasks.py`, `validator/goal_payload.py`, `validator/goal_generic_evidence.py`, `validator/goal_outcome.py` | FR-006 | ✅ Implemented | 2026-10-10 |
| FR-007 | `validator/goal_proof.py`, `validator/goal_render.py` | FR-007 | ✅ Implemented | 2026-10-10 |
| FR-008 | `validator/init_from_code.py`, `.agent-sync/skills/spec-init/SKILL.md` | FR-008 | ✅ Implemented | 2026-10-10 |
| FR-009 | `system/anti-drift-block.md`, `system/expectations.md`, `system/spec-system.md`, `.specs/spec-system.md`, `README.md` | FR-009 | ✅ Implemented | 2026-10-10 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 | tests/test_lightweight_goals.py::test_every_command_contract_keeps_only_receipt_backed_tasks | ✅ Implemented |
| AC-002 | tests/test_lightweight_goals.py::test_outcome_runs_the_real_stop_condition_and_rejects_invalid_specs | ✅ Implemented |
| AC-002 | tests/test_goal_outcome_runtime.py::test_stop_condition_rejects_consumer_validator_shadow | ✅ Implemented |
| AC-003 | tests/test_lightweight_goals.py::test_goal_requirement_targets_only_autonomous_long_runs | ✅ Implemented |
| AC-004 | tests/test_lightweight_goals.py::test_skills_never_block_on_native_goal_and_lock_only_autonomous_runs | ✅ Implemented |
| AC-005 | tests/test_lightweight_goals.py::test_drifted_contract_recompiles_in_place_and_keeps_valid_evidence | ✅ Implemented |
| AC-006 | tests/test_lightweight_goals.py::test_conventions_are_gated_once_per_feature_without_per_task_proofs | ✅ Implemented |
| AC-007 | tests/test_lightweight_goals.py::test_three_rejections_hand_back_a_blocked_report_and_later_proof_still_counts | ✅ Implemented |
| AC-008 | tests/test_lightweight_goals.py::test_completed_autonomous_init_is_not_failed_by_an_elapsed_deadline | ✅ Implemented |
| AC-009 | tests/test_lightweight_goals.py::test_runtime_goal_prompt_is_short_and_neutral | ✅ Implemented |

## Files Created/Modified

- Created `validator/goal_outcome.py` (scope, stop condition, outcome/conventions tasks), `validator/goal_recompile.py` (drift recompilation, state reuse), `validator/goal_canonical.py` (canonical JSON helpers kept from the deleted conventions module), `tests/test_lightweight_goals.py`, `tests/lightweight_goals_support.py` (saved-goal helpers extracted on integration to keep the test module within the repo file and function limits), `tests/goal_checklist_support.py`.
- Deleted `validator/goal_conventions.py`, `validator/init_goal_conventions.py`, `tests/test_init_goal_conventions.py` (per-task convention payload), child-goal proof helpers and obsolete per-row evidence rules.
- Modified goal compile/payload/tasks/proof/render/CLI modules, `validator/evidence_policy.py`, `validator/init_from_code.py`, 20 skills and their expectations `last_reviewed`, `system/anti-drift-block.md`, `system/expectations.md`, `system/spec-system.md`, `.specs/spec-system.md`, `README.md`, goal-related tests and `tests/conftest.py` (autouse stop-condition stub; `real_stop_condition` marker opts out).

## Bugfix Receipts

| Date | Requirement | Regression tests | RED receipt | GREEN receipt |
|---|---|---|---|---|
| 2026-10-12 | implementation | `tests/test_goal_outcome_runtime.py::test_stop_condition_rejects_consumer_validator_shadow[init-from-code]`, `tests/test_goal_outcome_runtime.py::test_stop_condition_rejects_consumer_validator_shadow[validate]` | `.specs/.execution/ecdd63efc0304b2db2865cf69ef8cddd/receipt.json` | `.specs/.execution/8cc6c57f4f854191baa743e989f7f3bf/receipt.json` |
