---
created: 2026-04-15
feature: '006'
status: Complete
title: Taxonomy Testing Infrastructure — Implementation
updated: 2026-06-08
---

# Implementation: 006 — Taxonomy Testing Infrastructure

## Summary

Implemented deterministic taxonomy parsing and testing in `validator/taxonomy.py`. The module loads `system/testing/ui-behavioral-taxonomy.md`, exposes `load_taxonomy()`, `detect_traits()`, and `deduplicate_tests()`, and uses `TaxonomyLoadError` for fail-fast taxonomy load failures. Feature 005.2 later expanded the taxonomy from 5 traits and 3 patterns to 22 traits and 6 patterns; the parser and tests now validate the expanded data.

## Requirement Mapping
| Requirement | Implementation | Tests / Evidence | Status |
|---|---|---|---|
| FR-001 | `validator/taxonomy.py`; `system/testing/ui-behavioral-taxonomy.md` | `tests/test_taxonomy_detection.py`; `.specs/features/006-taxonomy-testing-infra/checks/2026-04-15-test.md` | Complete |
| FR-002 | `validator/taxonomy.py` | `tests/test_taxonomy_detection.py`; `.specs/features/006-taxonomy-testing-infra/checks/2026-04-15-test.md` | Complete |
| FR-003 | `validator/taxonomy.py` | `tests/test_taxonomy_detection.py`; `tests/test_specify_integration.py`; `.specs/features/006-taxonomy-testing-infra/checks/2026-04-15-test.md` | Complete |
| FR-004 | `validator/taxonomy.py`; `system/testing/ui-behavioral-taxonomy.md` | `tests/test_taxonomy_detection.py`; `.specs/features/006-taxonomy-testing-infra/checks/2026-04-15-test.md` | Complete |
| FR-005 | `validator/taxonomy.py` | `tests/test_taxonomy_detection.py`; `.specs/features/006-taxonomy-testing-infra/checks/2026-04-15-test.md` | Complete |
| FR-006 | `validator/taxonomy.py`; `system/testing/ui-behavioral-taxonomy.md` | `tests/test_taxonomy_detection.py`; `.specs/features/006-taxonomy-testing-infra/checks/2026-04-15-test.md` | Complete |
| FR-007 | `validator/exceptions.py`; `validator/taxonomy.py` | `tests/test_taxonomy_detection.py`; `.specs/features/006-taxonomy-testing-infra/checks/2026-04-15-test.md` | Complete |
| FR-008 | `tests/test_taxonomy_detection.py` | `.specs/features/006-taxonomy-testing-infra/checks/2026-04-15-test.md`; `tests/test_specify_integration.py`; `tests/test_visual_states.py` | Complete |

## Acceptance Criteria Map

| AC | Evidence | Status |
|---|---|---|
| AC-001 | `validator/taxonomy.py`; `tests/test_taxonomy_detection.py` | Complete |
| AC-002 | `validator/taxonomy.py`; `system/testing/ui-behavioral-taxonomy.md`; `tests/test_taxonomy_detection.py` | Complete |
| AC-003 | `validator/exceptions.py`; `validator/taxonomy.py`; `tests/test_taxonomy_detection.py` | Complete |
| AC-004 | `validator/taxonomy.py`; `tests/test_taxonomy_detection.py` | Complete |
| AC-005 | `validator/taxonomy.py`; `tests/test_taxonomy_detection.py` | Complete |
| AC-006 | `validator/taxonomy.py`; `tests/test_taxonomy_detection.py` | Complete |
| AC-007 | `validator/taxonomy.py`; `tests/test_taxonomy_detection.py` | Complete |
| AC-008 | `validator/exceptions.py`; `validator/taxonomy.py`; `tests/test_taxonomy_detection.py` | Complete |
| AC-009 | `validator/taxonomy.py`; `tests/test_taxonomy_detection.py` | Complete |
| AC-010 | `validator/taxonomy.py`; `tests/test_taxonomy_detection.py` | Complete |
| AC-011 | `validator/taxonomy.py`; `tests/test_taxonomy_detection.py` | Complete |
| AC-012 | `tests/test_taxonomy_detection.py`; `.specs/features/006-taxonomy-testing-infra/checks/2026-04-15-test.md` | Complete |
| AC-013 | `tests/test_taxonomy_detection.py`; `.specs/features/006-taxonomy-testing-infra/checks/2026-04-15-test.md` | Complete |
| AC-014 | `validator/taxonomy.py`; `.specs/features/006-taxonomy-testing-infra/checks/2026-04-15-test.md` | Complete |
| AC-015 | `validator/taxonomy.py`; `.specs/features/006-taxonomy-testing-infra/checks/2026-04-15-test.md` | Complete |

## Verification

Read [`checks/2026-04-15-test.md`](checks/2026-04-15-test.md) for the original 15/15 AC verification report.

## Traceability Anchors

<!-- @spec(FR-001) -->
<!-- @spec(FR-002) -->
<!-- @spec(FR-003) -->
<!-- @spec(FR-004) -->
<!-- @spec(FR-005) -->
<!-- @spec(FR-006) -->
<!-- @spec(FR-007) -->
<!-- @spec(FR-008) -->
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
<!-- @spec(AC-014) -->
<!-- @spec(AC-015) -->
