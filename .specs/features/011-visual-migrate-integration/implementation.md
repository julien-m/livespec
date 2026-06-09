---
feature: 011-visual-migrate-integration
title: Implementation — 011-visual-migrate-integration
---

# Implementation — 011-visual-migrate-integration

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| [FR-001: Unconditional invocation](spec.md#fr-001) | .agent-sync/skills/spec-migrate/SKILL.md | `@spec FR-001: Unconditional invocation after migration — spec.md#fr-001` | ✅ Implemented | 2026-04-17 |
| [FR-002: Silent no-prompt](spec.md#fr-002) | .agent-sync/skills/spec-migrate/SKILL.md | `@spec FR-002: Silent no-prompt — spec.md#fr-002` | ✅ Implemented | 2026-04-17 |
| [FR-003: Skip existing tests](spec.md#fr-003) | scripts/migrate-visual-tests.js (existing) | `@spec AC-030: Hard guard — never overwrite` | ✅ Implemented | 2026-04-17 |
| [FR-004: Skip non-UI features](spec.md#fr-004) | scripts/migrate-visual-tests.js (existing `hasUIKeywords`) | N/A (existing logic) | ✅ Implemented | 2026-04-17 |
| [FR-005: Create baseline dirs](spec.md#fr-005) | scripts/migrate-visual-tests.js | `@spec FR-005: Create baseline directories — spec.md#fr-005` | ✅ Implemented | 2026-04-17 |
| [FR-006: Structured sentinel](spec.md#fr-006) | scripts/migrate-visual-tests.js | `@spec FR-006: Emit structured sentinel — spec.md#fr-006` | ✅ Implemented | 2026-04-17 |
| [FR-007: Post-migration summary](spec.md#fr-007) | .agent-sync/skills/spec-migrate/SKILL.md | `@spec FR-007: Post-migration visual summary — spec.md#fr-007` | ✅ Implemented | 2026-04-17 |
| [FR-008: Script-missing guard](spec.md#fr-008) | .agent-sync/skills/spec-migrate/SKILL.md | `@spec FR-008: Script-missing guard — spec.md#fr-008` | ✅ Implemented | 2026-04-17 |
| [FR-009: Node-missing guard](spec.md#fr-009) | .agent-sync/skills/spec-migrate/SKILL.md | `@spec FR-009: Node-missing guard — spec.md#fr-009` | ✅ Implemented | 2026-04-17 |
| [FR-010: Non-fatal on failure](spec.md#fr-010) | .agent-sync/skills/spec-migrate/SKILL.md | `@spec FR-010: Non-fatal on failure — spec.md#fr-010` | ✅ Implemented | 2026-04-17 |
| [FR-011: Detect new features](spec.md#fr-011) | scripts/migrate-visual-tests.js (existing scan logic) | N/A (existing logic) | ✅ Implemented | 2026-04-17 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 | tests/integration/test_migrate_visual.py::test_generates_files_for_ui_features | ✅ |
| AC-002 | tests/integration/test_migrate_visual.py::test_generates_files_for_ui_features | ✅ |
| AC-003 | tests/integration/test_migrate_visual.py::test_creates_baseline_directories | ✅ |
| AC-004 | tests/integration/test_migrate_visual.py::test_skips_backend_only_features | ✅ |
| AC-005 | tests/integration/test_migrate_visual.py::test_preserves_existing_test_files | ✅ |
| AC-006 | tests/integration/test_migrate_visual.py::test_sentinel_line_format | ✅ |
| AC-007 | tests/integration/test_migrate_visual.py::test_sentinel_shows_zero_when_all_covered | ✅ |
| AC-008 | tests/integration/test_migrate_visual.py::test_idempotent_on_second_run | ✅ |
| AC-009 | tests/integration/test_migrate_visual.py::test_picks_up_new_feature_on_rerun | ✅ |
| AC-010 | tests/integration/test_migrate_visual.py::test_warning_when_script_missing | ✅ |
| AC-011 | .agent-sync/skills/spec-migrate/SKILL.md Step 4.5 guard (command-layer spec) — no automated test; PATH manipulation deferred | Documented |
| AC-012 | tests/integration/test_migrate_visual.py::test_nonzero_exit_on_missing_specs_dir | ✅ |

## Files Created

- `tests/integration/test_migrate_visual.py` — 11 integration tests (level_3a) for visual scaffolding
- `tests/integration/fixtures/migrate-visual/` — Controlled fixture project with 4 features (2 UI, 1 backend, 1 pre-existing tests)
- `.specs/features/011-visual-migrate-integration/progress.md` — Step checkpoints
- `.specs/features/011-visual-migrate-integration/implementation.md` — This file

## Files Modified

- `scripts/migrate-visual-tests.js` — Added structured sentinel line output (`VISUAL_SCAFFOLD_RESULT: files=N dirs=M routes=R`) and `dirsCreated` counter; added 5 analysis helpers (`analyzeExistingTests`, `detectFixturesFromDir`, `extractSelectorsFromExistingTests`, `extractWaitPatterns`, `extractCommonTestCases`) for smarter template generation; fixed 3 template quality issues (mockup reference, header selector, empty-state fixture detection)
- `.agent-sync/skills/spec-migrate/SKILL.md` — Removed early exit on "already up to date", added Step 4.5 (Visual Test Scaffolding) with 3 guards, added visual summary to Report, added 3 edge cases
