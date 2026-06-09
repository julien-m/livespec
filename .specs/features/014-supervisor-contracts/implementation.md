---
created: 2026-05-06
feature: 014-supervisor-contracts
plan_ref: plan.md
spec_ref: spec.md
title: Supervisor↔Subagent Return Contracts
type: implementation
updated: 2026-05-06
---

# Implementation: Supervisor↔Subagent Return Contracts

> Reverse-engineered after-the-fact (PR #22 merged before `/spec.implement` was run on this feature). The mapping below was reconstructed by `/spec.fix` from `@spec FR-NNN` anchors discovered across the repository.

## Files Changed

| File | Action | Description |
|---|---|---|
| `validator/contracts.py` | Created | 373 LOC — Pydantic schemas + regex-anchored parsers for PHASE_RESULT, SHIP_RESULT, Superpowers return |
| `system/contracts/PHASE_RESULT.md` | Created | Schema, examples, parser behavior |
| `system/contracts/SHIP_RESULT.md` | Created | Schema, examples, parser behavior |
| `system/contracts/SUPERPOWERS_RETURN.md` | Created | Schema for Superpowers subagent returns |
| `system/contracts/ACTIVATION_CONTRACT.md` | Created | Reusable Activation Contract template (`test -d .specs` Step 1, flag re-validation, BLOCKED format) |
| `.agent-sync/agents/livespec-supervisor/prompt.md` | Modified | Activation Contract @import + return-contract validation gate |
| `.agent-sync/agents/livespec-implementer/prompt.md` | Modified | Activation Contract @import |
| `.agent-sync/agents/livespec-verifier/prompt.md` | Modified | Activation Contract @import |
| `.agent-sync/agents/livespec-documenter/prompt.md` | Modified | Activation Contract @import |
| `.agent-sync/skills/spec-feature/SKILL.md` | Modified | Wires PHASE_RESULT validation between phases |
| `.agent-sync/skills/spec-ship/SKILL.md` | Modified | SHIP_RESULT validation gate before destructive git ops |
| `tests/test_contracts.py` | Created | 276 LOC — 6 test classes (PhaseResultParser, PhaseResultLegacy, ShipResultParser, SuperpowersReturnParser, RoundTrip, SchemaModels) |

## Spec Anchor Mappings

| Source | Anchor | Location |
|---|---|---|
| @spec FR-001 | `spec.md#fr-001` | `validator/contracts.py:84` — `PHASE_RESULT` schema |
| @spec FR-002 | `spec.md#fr-002` | `validator/contracts.py:103` — `SHIP_RESULT` schema |
| @spec FR-003 | `spec.md#fr-003` | `validator/contracts.py:118` — Superpowers return schema |
| @spec FR-004 | `spec.md#fr-004` | `validator/contracts.py:55` — unique delimiter pair + last-30-line scan parser |
| @spec FR-005 | `spec.md#fr-005` | `validator/contracts.py` — `parse_ship_result()`; `system/contracts/SHIP_RESULT.md` |
| @spec FR-006 | `spec.md#fr-006` | `.agent-sync/agents/livespec-supervisor/prompt.md`, `livespec-documenter.md:11`, `livespec-implementer.md`, `livespec-verifier.md` (Activation Contract @import) |
| @spec FR-007 | `spec.md#fr-007` | `validator/contracts.py` — Pydantic `model_validate`; `.agent-sync/skills/spec-ship/SKILL.md` — validation gate |
| @spec FR-008 | `spec.md#fr-008` | `tests/test_contracts.py` — covers valid returns, malformed returns, multi-block output, injection attempts |
| @spec FR-009 | `spec.md#fr-009` | `.agent-sync/skills/spec-feature/SKILL.md`, `.agent-sync/skills/spec-ship/SKILL.md`, all 4 `.agent-sync/agents/livespec-*/prompt.md` updated to use new contracts |
| @spec FR-010 | `spec.md#fr-010` | `system/contracts/{PHASE_RESULT,SHIP_RESULT,SUPERPOWERS_RETURN,ACTIVATION_CONTRACT}.md` |

## AC Coverage

| AC | Status | Test |
|---|---|---|
| AC-001 | Covered | `tests/test_contracts.py::TestPhaseResultParser` (regex anchoring + last-30-line scan) |
| AC-002 | Covered | `tests/test_contracts.py::TestPhaseResultParser` (BLOCKED line format on parse error) |
| AC-003 | Covered | `tests/test_contracts.py::TestShipResultParser` (missing-status rejection); `.agent-sync/skills/spec-ship/SKILL.md` |
| AC-004 | Covered | All 4 `.agent-sync/agents/livespec-*/prompt.md` import `system/contracts/ACTIVATION_CONTRACT.md` (`test -d .specs` Step 1) |
| AC-005 | Covered | `tests/test_contracts.py::TestSuperpowersReturnParser`, `TestSchemaModels` |
| AC-006 | Covered | `validator/contracts.py` — Pydantic-based validation; `tests/test_contracts.py::TestRoundTrip` |
| AC-007 | Covered | `tests/test_contracts.py::TestPhaseResultParser` — multi-block extraction (only final result) |
| AC-008 | Covered | `system/contracts/ACTIVATION_CONTRACT.md` reused via @import in 4 agent files |
| AC-009 | Covered | `tests/test_contracts.py::TestPhaseResultParser` — injection-attempt cases (fake early + real late) |
| AC-010 | Covered | `system/contracts/{PHASE_RESULT,SHIP_RESULT,SUPERPOWERS_RETURN,ACTIVATION_CONTRACT}.md` exist |

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `.specs/features/014-supervisor-contracts/implementation.md` | @spec(FR-001) | ✅ Implemented | 2026-06-08 |
| FR-002 | `.specs/features/014-supervisor-contracts/implementation.md` | @spec(FR-002) | ✅ Implemented | 2026-06-08 |
| FR-003 | `.specs/features/014-supervisor-contracts/implementation.md` | @spec(FR-003) | ✅ Implemented | 2026-06-08 |
| FR-004 | `.specs/features/014-supervisor-contracts/implementation.md` | @spec(FR-004) | ✅ Implemented | 2026-06-08 |
| FR-005 | `.specs/features/014-supervisor-contracts/implementation.md` | @spec(FR-005) | ✅ Implemented | 2026-06-08 |
| FR-006 | `.specs/features/014-supervisor-contracts/implementation.md` | @spec(FR-006) | ✅ Implemented | 2026-06-08 |
| FR-007 | `.specs/features/014-supervisor-contracts/implementation.md` | @spec(FR-007) | ✅ Implemented | 2026-06-08 |
| FR-008 | `.specs/features/014-supervisor-contracts/implementation.md` | @spec(FR-008) | ✅ Implemented | 2026-06-08 |
| FR-009 | `.specs/features/014-supervisor-contracts/implementation.md` | @spec(FR-009) | ✅ Implemented | 2026-06-08 |
| FR-010 | `.specs/features/014-supervisor-contracts/implementation.md` | @spec(FR-010) | ✅ Implemented | 2026-06-08 |
