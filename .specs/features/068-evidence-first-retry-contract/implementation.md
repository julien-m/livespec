---
title: Evidence-First Retry Contract Implementation
feature: 068-evidence-first-retry-contract
---

<!-- @spec FR-001: Shared retry contract — .specs/features/068-evidence-first-retry-contract/spec.md#fr-001 -->
<!-- @spec FR-002: Command-local reminders — .specs/features/068-evidence-first-retry-contract/spec.md#fr-002 -->
<!-- @spec FR-003: Static regression coverage — .specs/features/068-evidence-first-retry-contract/spec.md#fr-003 -->
<!-- @spec FR-004: Preserve retry defaults — .specs/features/068-evidence-first-retry-contract/spec.md#fr-004 -->

# Implementation — Evidence-First Retry Contract

## Requirement Mapping

| Requirement | File(s) | Status | Last Verified |
|---|---|---|---|
| FR-001 | **Read** [`system/anti-drift-block.md`](../../../system/anti-drift-block.md). | Implemented | 2026-06-26 |
| FR-002 | **Read** [`.agent-sync/skills/spec-check/SKILL.md`](../../../.agent-sync/skills/spec-check/SKILL.md), [`.agent-sync/skills/spec-feature/SKILL.md`](../../../.agent-sync/skills/spec-feature/SKILL.md), [`.agent-sync/skills/spec-fix/SKILL.md`](../../../.agent-sync/skills/spec-fix/SKILL.md), [`.agent-sync/skills/spec-implement/SKILL.md`](../../../.agent-sync/skills/spec-implement/SKILL.md), [`.agent-sync/skills/spec-plan/SKILL.md`](../../../.agent-sync/skills/spec-plan/SKILL.md), and [`.agent-sync/skills/spec-test/SKILL.md`](../../../.agent-sync/skills/spec-test/SKILL.md). | Implemented | 2026-06-26 |
| FR-003 | **Read** [`tests/test_conventions_pipeline_docs.py`](../../../tests/test_conventions_pipeline_docs.py). | Implemented | 2026-06-26 |
| FR-004 | **Read** [`system/anti-drift-block.md`](../../../system/anti-drift-block.md). | Implemented | 2026-06-26 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001..AC-005 | **Read** [`tests/test_conventions_pipeline_docs.py`](../../../tests/test_conventions_pipeline_docs.py). | Passing |

## Files Created

| File | Type | Description |
|---|---|---|
| `.specs/features/068-evidence-first-retry-contract/spec.md` | Spec | Functional contract for evidence-first retries. |
| `.specs/features/068-evidence-first-retry-contract/plan.md` | Plan | Implementation and test plan. |
| `.specs/features/068-evidence-first-retry-contract/progress.md` | Progress | Execution checklist. |
| `.specs/features/068-evidence-first-retry-contract/implementation.md` | Mapping | Requirement and AC traceability. |
| `.specs/features/068-evidence-first-retry-contract/changelog.md` | Changelog | Feature history. |

## Files Modified

| File | Change | FR/AC Impacted |
|---|---|---|
| `system/anti-drift-block.md` | Added exact retry evidence fields and terminal/polling guidance. | FR-001, FR-004 |
| `.agent-sync/skills/spec-{check,feature,fix,implement,plan,test}/SKILL.md` | Added command-local `STEP 0.8` reminder. | FR-002 |
| `tests/test_conventions_pipeline_docs.py` | Added static regression coverage for the contract. | FR-003 |

## Known Gaps

None in the scoped command-contract implementation. A future runtime tracer could emit structured retry records automatically, but that is out of scope for this feature.
