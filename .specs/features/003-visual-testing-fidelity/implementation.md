---
type: implementation
feature: 003-visual-testing-fidelity
created: 2026-04-14
updated: 2026-04-14
---

# Implementation Map: Visual Testing Fidelity

## FR/AC to Source Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| [FR-001: Component-level snapshots](spec.md#fr-001) | `.claude/commands/spec.test.md` (Phase 4.5.1) | `<!-- @spec FR-001: component-level snapshots ... -->` (file header) | ✅ Implemented | 2026-04-14 |
| [FR-002: Reset-baselines workflow](spec.md#fr-002) | `.claude/commands/spec.test.md` (Phase 4.5.2) | same file header anchor | ✅ Implemented | 2026-04-14 |
| [FR-003: docker-compose.visual.yml generation](spec.md#fr-003) | `.claude/commands/spec.test.md` (Phase 4.5.2) | same file header anchor | ✅ Implemented | 2026-04-14 |
| [FR-004: Human approval gate](spec.md#fr-004) | `.claude/commands/spec.test.md` (Phase 4.5.3) | same file header anchor | ✅ Implemented | 2026-04-14 |
| [FR-005: --auto mode blocking](spec.md#fr-005) | `.claude/commands/spec.test.md` (Phase 4.5.3 Step C) | same file header anchor | ✅ Implemented | 2026-04-14 |
| [FR-006: maxDiffPixels threshold](spec.md#fr-006) | `.claude/commands/spec.test.md` (Visual Thresholds section) | `<!-- @spec FR-006: maxDiffPixels threshold -->` in generated config snippet | ✅ Implemented | 2026-04-14 |
| [FR-007: spec.check maxDiffPixels](spec.md#fr-007) | `.claude/commands/spec.check.md` (Step 8) | `<!-- @spec FR-007: maxDiffPixels for regression ... -->` | ✅ Implemented | 2026-04-14 |
| [FR-008: Stack presets Visual Testing section](spec.md#fr-008) | `stacks/presets/web-static.md`, `stacks/presets/web-realtime.md` | `<!-- @spec FR-008: visual testing section in web presets ... -->` | ✅ Implemented | 2026-04-14 |
| [FR-009: Migration v4 manifest](spec.md#fr-009) | `migrations/4/migrate.md` | `<!-- @spec FR-009: migration v4 manifest ... -->` | ✅ Implemented | 2026-04-14 |
| [FR-010: Screens table format](spec.md#fr-010) | `.specs/spec-system.md` (When working with DESIGN mockups) | `<!-- @spec FR-010: Screens table format with selector and aa_tolerance ... -->` | ✅ Implemented | 2026-04-14 |

## Acceptance Criteria Mapping

| AC | Description | File/Evidence | Status |
|---|---|---|---|
| AC-001 | spec.test generates `docker-compose.visual.yml` on first run | spec.test.md Phase 4.5.2 docker-compose section | ✅ Implemented |
| AC-002 | spec.test warns when baselines captured outside Docker | spec.test.md Phase 4.5.2 docker baseline warning | ✅ Implemented |
| AC-003 | spec.test generates `page.locator(selector).toHaveScreenshot()` when selector defined | spec.test.md Phase 4.5.1 Generation Rules | ✅ Implemented |
| AC-004 | spec.test adds `// Full-page screenshot` comment when no selector | spec.test.md Phase 4.5.1 Generation Rules (no selector fallback) | ✅ Implemented |
| AC-005 | Generated playwright.config.ts contains `maxDiffPixels: 0`, never `maxDiffPixelRatio` | spec.test.md Visual Thresholds, spec.check.md Step 8, web presets | ✅ Implemented |
| AC-006 | `aa_tolerance: true` entries generate `{ maxDiffPixels: 10 }` option | spec.test.md Phase 4.5.1 aa_tolerance section, Visual Thresholds | ✅ Implemented |
| AC-007 | `--reset-baselines` deletes existing baselines before capturing | spec.test.md Phase 4.5.2 --reset-baselines behavior | ✅ Implemented |
| AC-008 | `spec.test` without `--reset-baselines` never modifies existing baselines | spec.test.md Phase 4.5.2 Default behavior | ✅ Implemented |
| AC-009 | `--update-snapshots` never passed to Playwright | spec.test.md Phase 4.5.2 CRITICAL note + flags table | ✅ Implemented |
| AC-010 | spec.test always shows approval prompt after baseline capture, waits for `y` | spec.test.md Phase 4.5.3 Step B | ✅ Implemented |
| AC-011 | spec.test in `--auto` mode exits SHIP_RESULT: BLOCKED if diff > 5% | spec.test.md Phase 4.5.3 Step C | ✅ Implemented |
| AC-012 | Migration v4 replaces `maxDiffPixelRatio` with `maxDiffPixels: 0` and backs up | migrations/4/migrate.md REPLACE_CONFIG + BACKUP actions | ✅ Implemented |
| AC-013 | Migration v4 generates `docker-compose.visual.yml` if absent | migrations/4/migrate.md GENERATE_FILE action | ✅ Implemented |
| AC-014 | Migration v4 is idempotent | migrations/4/migrate.md Idempotency Check | ✅ Implemented |

## Files Created/Modified

| File | Action | Description |
|---|---|---|
| `.claude/commands/spec.test.md` | Modified | Phase 4.5 complete rewrite: component-level snapshots, --reset-baselines, approval gate, maxDiffPixels, docker-compose generation |
| `.claude/commands/spec.check.md` | Modified | Step 8: maxDiffPixels:0 threshold for regression detection |
| `stacks/presets/web-static.md` | Modified | Added ## Visual Testing section |
| `stacks/presets/web-realtime.md` | Modified | Added ## Visual Testing section |
| `migrations/4/migrate.md` | Created | Migration v4 manifest: BACKUP + REPLACE_CONFIG + GENERATE_FILE + SET_VERSION |
| `.specs/spec-system.md` | Modified | Extended Screens table format with selector/aa_tolerance columns |
| `.specs/features/003-visual-testing-fidelity/plan.md` | Created | Technical implementation plan |
| `.specs/features/003-visual-testing-fidelity/progress.md` | Created | Step-by-step implementation checkpoints |
