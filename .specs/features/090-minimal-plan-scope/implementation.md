---
created: 2026-10-15
feature: 090-minimal-plan-scope
title: 'Implementation Map: Minimal Plan Scope'
type: implementation
updated: 2026-10-15
---

# Implementation — Minimal Plan Scope

> Read [spec](spec.md) and [plan](plan.md). Non-UI feature; no visual baselines.

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| [FR-001: Native rule and plan review guidance](spec.md#fr-001) | `system/minimal-spec-scope.md` (new), `system/review-protocol.md`, `validator/semantic/review_batches.py` (`_PLAN_SCOPE_RULE`, plan prompts only), spec-plan skill, `system/spec-system.md`, `.specs/spec-system.md`, plan template | `@spec FR-001: Plan review flags untraced mechanisms — .specs/features/090-minimal-plan-scope/spec.md#fr-001` | ✅ Implemented | 2026-10-15 |
| [FR-002: Evidence classes, goal deferral and ship requirement](spec.md#fr-002) | `validator/plan_evidence.py` (new: steps and class validation), `validator/release_evidence.py` (new: proof rows, release items, goal context), `validator/rules/__init__.py`, `validator/goal_payload.py` (`pending_release_evidence`), `validator/progression_gate.py` (`ship`), `validator/cli_commands/operation_options.py`, `system/testing/execution-rules.md`, spec-implement and spec-ship skills | `@spec FR-002: Evidence class parsing and validation — .specs/features/090-minimal-plan-scope/spec.md#fr-002` | ✅ Implemented | 2026-10-15 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 | `tests/test_plan_evidence_class.py` (`test_plan_review_prompt_carries_minimal_scope_rule`, `test_untraced_cache_blocks_unless_justified_technical_necessity`, `test_native_rule_is_cited_by_the_review_protocol`) | ✅ Pass 2026-10-15 |
| AC-002 | `tests/test_plan_evidence_class.py` (step parsing and labels), `tests/test_release_evidence.py` (pending, announced, example and mismatched proofs, implement goal context, ship progression, fail-closed plans, unreadable map) | ✅ Pass 2026-10-15 |
| AC-003 | `tests/test_plan_evidence_class.py` (`test_invalid_evidence_classes_are_reported`, `test_validate_plan_rejects_unknown_class`, `test_long_whitespace_runs_stay_linear`) | ✅ Pass 2026-10-15 |

## Decisions

- The native rule is a LiveSpec system rule (`system/minimal-spec-scope.md`): `.conventions/` only lists ai-ressources sources, so it cannot carry a LiveSpec rule without a new source root.
- The plan review prompt gains the rule for `plan` reviews only, and `PROMPT_VERSION` stays `2`: it is part of every review identity, and a bump would make every current review stale (089) for an instruction that only narrows what the reviewer reports.
- `/spec-ship` requires release evidence through the existing `livespec validate <feature-dir> --progression ship` (the `complete` checks plus a recorded proof for each release step), not a new command.
- A step is identified by the number in its title (`Step 2.5` is `2.5`), so a recorded proof stays bound to its step when others are added; duplicate numbers on a classified step are rejected.
- A release proof is a row `| Step | Evidence | Proof |` under a heading exactly `## Release Evidence`: the row names the step number and the step's name, so a proof bound to another step is a mismatch the ship progression refuses. A cell that only announces a proof keeps the item pending; rows in code blocks, HTML comments or indented code are ignored.
- Every pattern is linear in the line length (round 2 of the delivery review measured a cubic heading pattern); a regression test bounds a 20,000-space heading.
- `ship` fails closed with `release_evidence_invalid` when the plan's evidence classes do not validate.
- The `--progression` help text of `validator/cli.py` is not updated: touching that file brings its existing size debt into the feature-scope conventions gate.
