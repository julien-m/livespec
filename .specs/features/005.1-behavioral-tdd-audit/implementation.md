---
feature: 005.1-behavioral-tdd-audit
title: Implementation — Behavioral TDD Audit (005.1)
---

# Implementation — Behavioral TDD Audit (005.1)

## FR-to-File Mapping

| FR | Description | File | @spec Anchor |
|----|-------------|------|-------------|
| FR-011 | Crash test procedure document | `.specs/features/005-ui-behavioral-testing/checks/procedure.md` | `@spec FR-011: Crash test procedure doc` |
| FR-001 | Behavioral AC detection in /spec.implement | spec-implement SKILL.md, Behavioral AC detection and Step 0a | prompt contract (no executable code) |
| FR-004 | Skip without Behavioral AC | spec-implement SKILL.md, Step 0a skip rule | prompt contract (no executable code) |
| FR-007 | Coverage matrix output | spec-test SKILL.md, Behavioral Audit sub-phase 1.5 | prompt contract (no executable code) |
| FR-008 | All covered message | spec-test SKILL.md, Behavioral Audit sub-phase 1.5 | prompt contract (no executable code) |
| FR-009 | Taxonomy ref in gaps | spec-test SKILL.md, Behavioral Audit sub-phase 1.5 | prompt contract (no executable code) |

## AC Coverage

| AC | Status | Evidence |
|----|--------|----------|
| AC-001 | Documented | spec-implement SKILL.md prompt contract; no automated test (see note) |
| AC-004 | Documented | spec-implement SKILL.md prompt contract; no automated test (see note) |
| AC-007 | Documented | spec-test SKILL.md prompt contract; no automated test (see note) |
| AC-008 | Documented | spec-test SKILL.md prompt contract; no automated test (see note) |
| AC-009 | Documented | spec-test SKILL.md prompt contract; no automated test (see note) |
| AC-011 | Verified | `.specs/features/005-ui-behavioral-testing/checks/procedure.md` exists with 4 required sections |

> **Note (2026-10-12):** `tests/test_behavioral_tdd.py` was removed. Its helpers `_has_behavioral_ac_section` and `_build_audit_output` were defined in the test file itself and then asserted, so the five tests exercised no LiveSpec code. The behavior exists only as SKILL.md prompt instructions executed by agents; there is no executable implementation to test.

## Files Created

| File | Purpose | Lines |
|------|---------|-------|
| `.specs/features/005-ui-behavioral-testing/checks/procedure.md` | Crash test procedure document | 118 |

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `.specs/features/005.1-behavioral-tdd-audit/implementation.md` | @spec(FR-001) | ✅ Implemented | 2026-06-08 |
| FR-002 | `.specs/features/005.1-behavioral-tdd-audit/implementation.md` | @spec(FR-002) | ✅ Implemented | 2026-06-08 |
| FR-003 | `.specs/features/005.1-behavioral-tdd-audit/implementation.md` | @spec(FR-003) | ✅ Implemented | 2026-06-08 |
| FR-004 | `.specs/features/005.1-behavioral-tdd-audit/implementation.md` | @spec(FR-004) | ✅ Implemented | 2026-06-08 |
| FR-005 | `.specs/features/005.1-behavioral-tdd-audit/implementation.md` | @spec(FR-005) | ✅ Implemented | 2026-06-08 |
| FR-006 | `.specs/features/005.1-behavioral-tdd-audit/implementation.md` | @spec(FR-006) | ✅ Implemented | 2026-06-08 |
| FR-007 | `.specs/features/005.1-behavioral-tdd-audit/implementation.md` | @spec(FR-007) | ✅ Implemented | 2026-06-08 |
| FR-008 | `.specs/features/005.1-behavioral-tdd-audit/implementation.md` | @spec(FR-008) | ✅ Implemented | 2026-06-08 |
| FR-009 | `.specs/features/005.1-behavioral-tdd-audit/implementation.md` | @spec(FR-009) | ✅ Implemented | 2026-06-08 |
| FR-010 | `.specs/features/005.1-behavioral-tdd-audit/implementation.md` | @spec(FR-010) | ✅ Implemented | 2026-06-08 |
| FR-011 | `.specs/features/005.1-behavioral-tdd-audit/implementation.md` | @spec(FR-011) | ✅ Implemented | 2026-06-08 |
| FR-012 | `.specs/features/005.1-behavioral-tdd-audit/implementation.md` | @spec(FR-012) | ✅ Implemented | 2026-06-08 |
| FR-013 | `.specs/features/005.1-behavioral-tdd-audit/implementation.md` | @spec(FR-013) | ✅ Implemented | 2026-06-08 |
| FR-014 | `.specs/features/005.1-behavioral-tdd-audit/implementation.md` | @spec(FR-014) | ✅ Implemented | 2026-06-08 |
| FR-015 | `.specs/features/005.1-behavioral-tdd-audit/implementation.md` | @spec(FR-015) | ✅ Implemented | 2026-06-08 |
