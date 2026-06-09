---
created: 2026-04-14
feature: '005'
status: Complete
title: UI Behavioral Testing — Implementation
updated: 2026-06-08
---

# Implementation: 005 — UI Behavioral Testing

## Summary

Implemented behavioral UI testing as a Markdown command-system feature: the taxonomy is the source of truth, `$spec-specify` injects Behavioral AC, `$spec-implement` adds a behavioral TDD step, and `$spec-test` audits declared trait coverage. The latest taxonomy is v2.0.0 after Feature 005.2 expanded the initial 5 traits to 22 traits.

## Requirement Mapping
| Requirement | Implementation | Tests / Evidence | Status |
|---|---|---|---|
| FR-001 | `system/testing/ui-behavioral-taxonomy.md` | `system/testing/ui-behavioral-taxonomy.md`; `.specs/features/005-ui-behavioral-testing/checks/2026-04-14.md`; `.specs/features/005-ui-behavioral-testing/checks/crash-test-2026-04-17-extended.md` | Complete |
| FR-002 | `.agent-sync/skills/spec-specify/SKILL.md`; `validator/taxonomy.py` | `tests/test_taxonomy_detection.py`; `tests/test_specify_integration.py` | Complete |
| FR-003 | `.agent-sync/skills/spec-specify/SKILL.md`; `system/testing/ui-behavioral-taxonomy.md` | `tests/test_specify_integration.py`; `.specs/features/005-ui-behavioral-testing/checks/2026-04-14.md` | Complete |
| FR-004 | `.agent-sync/skills/spec-specify/SKILL.md` | `tests/test_specify_integration.py`; `.specs/features/005-ui-behavioral-testing/checks/2026-04-14.md` | Complete |
| FR-005 | `.agent-sync/skills/spec-implement/SKILL.md`; `system/testing/ui-behavioral-taxonomy.md` | `.specs/features/005-ui-behavioral-testing/checks/2026-04-14.md` | Complete |
| FR-006 | `.agent-sync/skills/spec-implement/SKILL.md`; `system/testing/ui-behavioral-taxonomy.md` | `.specs/features/005-ui-behavioral-testing/checks/2026-04-14.md`; `tests/test_taxonomy_detection.py` | Complete |
| FR-007 | `.agent-sync/skills/spec-test/SKILL.md`; `validator/taxonomy.py` | `tests/test_taxonomy_detection.py`; `.specs/features/005-ui-behavioral-testing/checks/2026-04-14.md` | Complete |
| FR-008 | `.agent-sync/skills/spec-test/SKILL.md`; `system/testing/ui-behavioral-taxonomy.md` | `.specs/features/005-ui-behavioral-testing/checks/2026-04-14.md`; `tests/test_taxonomy_detection.py` | Complete |
| FR-009 | `.specs/features/005-ui-behavioral-testing/checks/procedure.md` | `.specs/features/005-ui-behavioral-testing/checks/crash-test-2026-04-14.md`; `.specs/features/005-ui-behavioral-testing/checks/crash-test-2026-04-17-extended.md` | Complete |

## Acceptance Criteria Map

| AC | Evidence | Status |
|---|---|---|
| AC-001 | `system/testing/ui-behavioral-taxonomy.md`; `.specs/features/005-ui-behavioral-testing/checks/2026-04-14.md` | Complete |
| AC-002 | `system/testing/ui-behavioral-taxonomy.md`; `.specs/features/005-ui-behavioral-testing/checks/2026-04-14.md` | Complete |
| AC-003 | `.agent-sync/skills/spec-specify/SKILL.md`; `validator/taxonomy.py`; `tests/test_specify_integration.py` | Complete |
| AC-004 | `.agent-sync/skills/spec-specify/SKILL.md`; `tests/test_specify_integration.py` | Complete |
| AC-005 | `.agent-sync/skills/spec-specify/SKILL.md`; `tests/test_specify_integration.py` | Complete |
| AC-006 | `.agent-sync/skills/spec-implement/SKILL.md`; `.specs/features/005-ui-behavioral-testing/checks/2026-04-14.md` | Complete |
| AC-007 | `.agent-sync/skills/spec-implement/SKILL.md`; `system/testing/ui-behavioral-taxonomy.md`; `.specs/features/005-ui-behavioral-testing/checks/2026-04-14.md` | Complete |
| AC-008 | `.agent-sync/skills/spec-implement/SKILL.md`; `.specs/features/005-ui-behavioral-testing/checks/2026-04-14.md` | Complete |
| AC-009 | `.agent-sync/skills/spec-test/SKILL.md`; `tests/test_taxonomy_detection.py`; `.specs/features/005-ui-behavioral-testing/checks/2026-04-14.md` | Complete |
| AC-010 | `.agent-sync/skills/spec-test/SKILL.md`; `.specs/features/005-ui-behavioral-testing/checks/2026-04-14.md` | Complete |
| AC-011 | `.agent-sync/skills/spec-test/SKILL.md`; `.specs/features/005-ui-behavioral-testing/checks/2026-04-14.md` | Complete |
| AC-012 | `.specs/features/005-ui-behavioral-testing/checks/crash-test-2026-04-14.md`; `.specs/features/005-ui-behavioral-testing/checks/crash-test-2026-04-17-extended.md` | Complete |
| AC-013 | `.specs/features/005-ui-behavioral-testing/checks/crash-test-2026-04-14.md`; `.specs/features/005-ui-behavioral-testing/checks/crash-test-2026-04-17-extended.md` | Complete |

## Verification

Read [`checks/2026-04-14.md`](checks/2026-04-14.md) for the original verifier report. Read [`checks/crash-test-2026-04-17-extended.md`](checks/crash-test-2026-04-17-extended.md) for the v2.0.0 taxonomy crash test.

## Traceability Anchors

<!-- @spec(FR-001) -->
<!-- @spec(FR-002) -->
<!-- @spec(FR-003) -->
<!-- @spec(FR-004) -->
<!-- @spec(FR-005) -->
<!-- @spec(FR-006) -->
<!-- @spec(FR-007) -->
<!-- @spec(FR-008) -->
<!-- @spec(FR-009) -->
<!-- @spec(AC-001) -->
<!-- @spec(AC-002) -->
<!-- @spec(AC-003) -->
<!-- @spec(AC-004) -->
<!-- @spec(AC-005) -->
<!-- @spec(AC-006) -->
<!-- @spec(AC-007) -->
<!-- @spec(AC-008) -->
<!-- @spec(AC-009) -->
<!-- @spec(AC-010) -->
<!-- @spec(AC-011) -->
<!-- @spec(AC-012) -->
<!-- @spec(AC-013) -->
