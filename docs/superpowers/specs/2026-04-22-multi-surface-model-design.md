# Multi-Surface Model — Design Spec

**Date:** 2026-04-22
**Status:** Approved (Codex + Roundtable 3/4)
**Problem:** Migration v7 creates test directories at project root instead of inside the correct app directory in monorepo structures.

## Context

LiveSpec's migration generates Playwright tests (visual + E2E) via two scripts:
- `migrate-visual-tests.js` — visual regression tests
- `generate-e2e-tests.js` — E2E tests from Gherkin scenarios

Both hardcode test directory detection: `frontend/tests/e2e` → `tests/e2e` → `tests/visual`. This fails for monorepos with structures like `apps/web/`, `apps/mobile/`, etc.

A project can have **multiple UI surfaces** (web, iOS, Apple Watch), each with its own codebase and test directory.

## Design Decisions

### D1: Surface Definition

A **surface** = a distinct UI application/codebase within a project. Viewports (mobile/tablet/desktop) are variants within a surface, not separate surfaces.

### D2: Configuration File

New file `.specs/surfaces.yaml` — dedicated, machine-parsable. Separated from `_default.md` (editorial content) to avoid mixing topologies.

### D3: Schema

```yaml
# .specs/surfaces.yaml
surfaces:
  - id: web                                    # stable key, never changes
    name: Application Web                       # human label
    path: apps/web                              # app root directory
    testDir: apps/web/tests/e2e                 # where tests are generated
    runner: playwright                          # determines which generator applies
    runnerConfig: apps/web/playwright.config.ts # optional, runner-specific config
  - id: mobile
    name: App iOS
    path: apps/mobile
    testDir: apps/mobile/tests/e2e
    runner: manual                              # tests managed outside LiveSpec
  - id: watch
    name: Apple Watch
    path: apps/watch
    runner: unsupported                         # no test framework applicable
```

**Fields:**
- `id` — stable identifier, never changes (used in spec.md `Surfaces:` references)
- `name` — human-readable label, can change
- `path` — app root directory relative to project root
- `testDir` — where test files are generated (required for `runner: playwright` and `manual`)
- `runner` — `playwright` | `manual` | `unsupported`
  - `playwright`: LiveSpec generates tests
  - `manual`: tests exist but managed outside LiveSpec (warning on skip)
  - `unsupported`: no test framework applicable (warning on skip)
- `runnerConfig` — optional, runner-specific configuration path

### D4: Per-Feature Surface Annotation

Optional `Surfaces:` field in spec.md metadata header:

```markdown
- Surfaces: web, mobile
```

Default = all surfaces. When a feature targets a non-web surface and generation is skipped, emit explicit warning.

### D5: Detection Strategy (Strict Precedence)

- **Config present** (`.specs/surfaces.yaml` exists): config is authoritative. No filesystem merge. Validate at parse time.
- **Config absent**: filesystem detection (improved legacy fallback). No partial config + partial detection hybrid.

### D6: Validation at Parse Time

When reading `surfaces.yaml`:
1. YAML parse error → **FATAL** (no fallback to legacy)
2. Each `path` exists on disk → warning if absent
3. Each `testDir` is under `path` → error if inconsistent
4. No `id` collisions
5. No `testDir` collisions between surfaces
6. `runnerConfig` file exists if specified → warning if absent

Errors = migration stops. Warnings = migration continues with log.

### D7: Shared Module

New `scripts/lib/surface-resolver.js`:
- Reads and validates `.specs/surfaces.yaml`
- Falls back to improved filesystem detection when no config
- Exports `resolveSurfaces()` → array of surface objects
- Imported by both `generate-e2e-tests.js` and `migrate-visual-tests.js`

### D8: Backward Compatibility

- No `surfaces.yaml` = mode legacy (current filesystem detection, unchanged)
- `apps/*` scan only at init time (`spec.init --from-code`), never at runtime
- Zero behavior change for existing projects without `surfaces.yaml`

### D9: Migration 8

New migration that:
1. Detects project surfaces from filesystem structure
2. Generates `.specs/surfaces.yaml` with detected surfaces
3. Bumps version to 8

### D10: Anti-Drift

`spec.check --surfaces` command:
- Compares filesystem structure vs `surfaces.yaml`
- Reports new app directories not in config
- Reports configured surfaces with missing paths
- Suitable for CI/pre-commit

### D11: Feature Creation Integration

When `spec.specify` creates a new feature:
- If `surfaces.yaml` exists with multiple surfaces, prompt for which surfaces the feature targets
- Add `Surfaces:` field to spec.md if not targeting all surfaces

## Architecture

```
.specs/surfaces.yaml          ← source of truth (D2)
        ↓
scripts/lib/surface-resolver.js  ← shared reader/validator (D7)
        ↓
  ┌─────┴─────┐
  ↓           ↓
generate-    migrate-
e2e-tests.js visual-tests.js
  ↓           ↓
  └─────┬─────┘
        ↓
  Per-surface TEST_DIR
  (apps/web/tests/e2e, etc.)
```

## Out of Scope

- Native test generation (XCUITest, Espresso, Detox) — LiveSpec is Playwright-only
- Multi-runner support in a single surface
- `spec.init --from-code` surface auto-detection (follow-up, Decision 9 in roundtable)
