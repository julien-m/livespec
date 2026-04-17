# Implementation — Behavioral TDD Audit (005.1)

## FR-to-File Mapping

| FR | Description | File | @spec Anchor |
|----|-------------|------|-------------|
| FR-011 | Crash test procedure document | `.specs/features/005-ui-behavioral-testing/checks/procedure.md` | `@spec FR-011: Crash test procedure doc` |
| FR-001 | Behavioral AC detection in /spec.implement | `tests/test_behavioral_tdd.py` | `@spec FR-001: Behavioral TDD detection` |
| FR-004 | Skip without Behavioral AC | `tests/test_behavioral_tdd.py` | `@spec FR-004: Skip without Behavioral AC` |
| FR-007 | Coverage matrix output | `tests/test_behavioral_tdd.py` | `@spec FR-007: Coverage matrix output` |
| FR-008 | All covered message | `tests/test_behavioral_tdd.py` | `@spec FR-008: All covered message` |
| FR-009 | Taxonomy ref in gaps | `tests/test_behavioral_tdd.py` | `@spec FR-009: Taxonomy ref in gaps` |

## AC Coverage

| AC | Status | Evidence |
|----|--------|----------|
| AC-001 | Verified | `test_implement_detects_behavioral_ac` passes |
| AC-004 | Verified | `test_implement_skips_without_behavioral_ac` passes |
| AC-007 | Verified | `test_test_behavioral_audit_coverage_matrix_structure` passes |
| AC-008 | Verified | `test_test_audit_all_covered_message` passes |
| AC-009 | Verified | `test_test_audit_missing_pattern_with_taxonomy_ref` passes |
| AC-011 | Verified | `procedure.md` exists with 4 required sections |

## Files Created

| File | Purpose | Lines |
|------|---------|-------|
| `.specs/features/005-ui-behavioral-testing/checks/procedure.md` | Crash test procedure document | 118 |
| `tests/test_behavioral_tdd.py` | 5 unit tests for behavioral TDD/audit | 209 |
