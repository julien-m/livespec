---
feature: "009"
title: Visual State Baselines — Implementation
status: Complete
created: 2026-04-17
---

# Implementation: 009 — Visual State Baselines

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|-------------|---------|-------------|--------|---------------|
| FR-001 | `system/testing/ui-behavioral-taxonomy.md` | Visual states tables for all 5 traits | ✅ Implemented | 2026-04-17 |
| FR-002 | `validator/taxonomy.py` | `@spec FR-002` (VisualState dataclass + Trait field) | ✅ Implemented | 2026-04-17 |
| FR-003 | `commands/specify.md` | `@spec FR-003` (Visual state Gherkin injection) | ✅ Implemented | 2026-04-17 |
| FR-004 | `commands/test.md` | `@spec FR-004` (toHaveScreenshot generation) | ✅ Implemented | 2026-04-17 |
| FR-005 | `commands/test.md` | `@spec FR-005` (Baseline storage path) | ✅ Implemented | 2026-04-17 |
| FR-006 | `commands/test.md` | `@spec FR-006` (Metadata .meta.yml) | ✅ Implemented | 2026-04-17 |
| FR-007 | `commands/test.md` | `@spec FR-007` (--regenerate-missing scan) | ✅ Implemented | 2026-04-17 |
| FR-008 | `commands/test.md` | `@spec FR-008` (--regenerate-missing --confirm) | ✅ Implemented | 2026-04-17 |
| FR-009 | `commands/test.md` | `@spec FR-009` (--regenerate-missing --dry-run) | ✅ Implemented | 2026-04-17 |
| FR-010 | `commands/test.md` | `@spec FR-010` (Never overwrite existing tests) | ✅ Implemented | 2026-04-17 |
| FR-011 | `commands/test.md` | `@spec FR-011` (Taxonomy hash invalidation) | ✅ Implemented | 2026-04-17 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|----|-----------|--------|
| AC-001 | `tests/test_visual_states.py` | ✅ Implemented |
| AC-002 | N/A (command instruction — `commands/specify.md`) | ✅ Implemented |
| AC-003 | N/A (command instruction — `commands/test.md`) | ✅ Implemented |
| AC-004 | N/A (command instruction — `commands/test.md`) | ✅ Implemented |
| AC-005 | N/A (command instruction — `commands/test.md`) | ✅ Implemented |
| AC-006 | N/A (command instruction — `commands/test.md`) | ✅ Implemented |
| AC-007 | N/A (command instruction — `commands/test.md`) | ✅ Implemented |
| AC-008 | N/A (command instruction — `commands/test.md`) | ✅ Implemented |
| AC-009 | N/A (command instruction — `commands/test.md`) | ✅ Implemented |
| AC-010 | N/A (command instruction — `commands/test.md`) | ✅ Implemented |
| AC-011 | N/A (command instruction — `commands/test.md`) | ✅ Implemented |
| AC-012 | N/A (command instruction — `commands/test.md`) | ✅ Implemented |
| AC-013 | `tests/test_visual_states.py` | ✅ Implemented |
| AC-014 | `tests/test_visual_states.py` | ✅ Implemented |
| AC-015 | N/A (command instruction — `commands/test.md`) | ✅ Implemented |

## Files Created

- `tests/test_visual_states.py` — 14 unit tests for VisualState parsing, duplicate detection, taxonomy hash
- `.specs/features/009-visual-state-baselines/implementation.md` — this file
- `.specs/features/009-visual-state-baselines/progress.md` — step-by-step progress tracker

## Files Modified

- `validator/taxonomy.py` — Added `VisualState` dataclass (frozen), extended `Trait` with `visual_states` field, added `_parse_visual_states()`, `_extract_cell_codespans()`, `_cell_plain_text()`, `check_duplicate_screenshots()` functions, integrated visual state parsing into `_parse_traits()`
- `system/testing/ui-behavioral-taxonomy.md` — Added `**Visual states:**` tables for all 5 traits (16 total states), bumped version to v1.1.0
- `commands/specify.md` — Added Step 5.7 sub-step 4.5 for visual state assertion injection with EC-001 handling
- `commands/test.md` — Added Phase 3.6 for visual state test generation (toHaveScreenshot, baseline storage, metadata, staleness detection), added `--regenerate-missing` flag section with --confirm/--dry-run behavior
