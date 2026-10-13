---
created: 2026-10-13
feature: 088-capped-reviews
title: 'Implementation Map: Capped Reviews'
type: implementation
updated: 2026-10-13
---

# Implementation — Capped Reviews

> Read [spec](spec.md) and [plan](plan.md). Non-UI feature; no visual baselines.

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| [FR-001: blockers only and carry-over](spec.md#fr-001) | `validator/semantic/review_contract.py` (`conclusion_blocks`, `carry_over`, readiness) | `@spec FR-001: Non-critical ambiguity carries over` | ✅ Implemented | 2026-10-13 |
| [FR-002: technical scope](spec.md#fr-002) | `validator/semantic/review_contract.py` (`ScopeFinding.kind`, `scope_accepted`), `validator/semantic_analysis.py` | `@spec FR-002: Justified technical necessity is approved` | ✅ Implemented | 2026-10-13 |
| [FR-003: round ledger](spec.md#fr-003) | `validator/semantic/review_rounds.py`, `validator/cli_commands/review_io.py` | `@spec FR-003: Review round ledger and cap` | ✅ Implemented | 2026-10-13 |
| [FR-004: qualitative words](spec.md#fr-004) | `validator/clarify_gate.py` | `@spec FR-004: An isolated qualitative word does not block` | ✅ Implemented | 2026-10-13 |
| [FR-005: documentation](spec.md#fr-005) | `system/review-protocol.md`, spec-specify and spec-plan skills and expectations | — | ✅ Implemented | 2026-10-13 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 to AC-004 | `tests/test_capped_reviews.py` | ✅ Pass 2026-10-13 |
| AC-004 | `tests/test_clarify_*.py` (criticality assertions updated) | ✅ Pass 2026-10-13 |
