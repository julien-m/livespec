# Multi-Surface Model — Implementation Plan

**Date:** 2026-04-22
**Design:** [2026-04-22-multi-surface-model-design.md](../specs/2026-04-22-multi-surface-model-design.md)

## Step 1: Create `scripts/lib/surface-resolver.js`

New shared module. Exports `resolveSurfaces()`.

**Logic:**
1. Check if `.specs/surfaces.yaml` exists
2. If yes: parse YAML (FATAL on parse error), validate (D6 rules), return array of surface objects
3. If no: run improved filesystem detection (legacy fallback), return single implicit surface

**Filesystem detection (fallback):**
1. Check `frontend/tests/e2e/` → `{id:'default', path:'.', testDir:'frontend/tests/e2e', runner:'playwright'}`
2. Scan `apps/*/` for web markers (package.json with web deps, routes dirs, playwright config)
3. If found: `{id: appDirName, path: 'apps/'+appDirName, testDir: 'apps/'+appDirName+'/tests/e2e', runner:'playwright'}`
4. Check `tests/e2e/` → `{id:'default', path:'.', testDir:'tests/e2e', runner:'playwright'}`
5. Fallback: `{id:'default', path:'.', testDir:'tests/visual', runner:'playwright'}`

**Validation (when config exists):**
- YAML parse error → throw with clear message
- Duplicate `id` → throw
- Duplicate `testDir` → throw
- `testDir` not under `path` → throw
- `path` doesn't exist → console.warn (continue)
- `runnerConfig` file doesn't exist → console.warn (continue)

**Exports:**
- `resolveSurfaces()` → `Surface[]`
- `getPlaywrightSurfaces()` → `Surface[]` (filters runner=playwright only)

**Files:** `scripts/lib/surface-resolver.js` (new)

## Step 2: Update `scripts/generate-e2e-tests.js`

Replace lines 19-78 (hardcoded detection) with:
```js
import { getPlaywrightSurfaces } from './lib/surface-resolver.js';
```

Wrap the main generation logic in a loop over `getPlaywrightSurfaces()`. For each surface:
- Set `TEST_DIR = surface.testDir`
- Set `FRONTEND_MODE` based on surface path
- Run `scanFeatures()` → `generateTests()` with that TEST_DIR

Keep `detectWebFrontend()` for the no-frontend early exit, but derive it from surfaces (if 0 playwright surfaces → no frontend).

**Files:** `scripts/generate-e2e-tests.js` (modify lines 19-78)

## Step 3: Update `scripts/migrate-visual-tests.js`

Same pattern as Step 2. Replace lines 22-78 with surface-resolver import.

Key changes:
- `TEST_DIR` → from surface.testDir
- `FRONTEND_MODE` → from surface config
- `PENCIL_MODE` → unchanged (mockup detection stays global)
- Loop over playwright surfaces for generation

**Files:** `scripts/migrate-visual-tests.js` (modify lines 22-78)

## Step 4: Create Migration 8

New `migrations/8/migrate.md`:
- Version bump to 8
- Script: `migrations/8/generate-surfaces.js`
  - Detect project surfaces from filesystem
  - Generate `.specs/surfaces.yaml` with detected surfaces
  - If only 1 surface detected at project root → still generate the file (makes config explicit)
  - Idempotent: skip if `surfaces.yaml` already exists

**Files:**
- `migrations/8/migrate.md` (new)
- `scripts/generate-surfaces.js` (new — migration script)

## Step 5: Update `commands/migrate.md`

Add new Step 4.4 before visual scaffolding:

**Step 4.4 — Surface Resolution**
1. Call surface-resolver (conceptually — the scripts handle this internally)
2. Log detected surfaces: `Surfaces: web (apps/web), mobile (manual), watch (unsupported)`
3. For non-playwright surfaces, log warning and skip

Update Steps 4.5 and 4.7 references to mention multi-surface iteration.

**Files:** `commands/migrate.md` (modify)

## Step 6: Update `commands/specify.md`

After Step 5 (Generate spec.md), add:

**Step 5.1 — Surface annotation**
1. If `.specs/surfaces.yaml` exists AND has >1 surface with runner=playwright:
   - List available surfaces
   - Add `- Surfaces: all` (or specific IDs) to spec.md header
2. If only 1 surface or no surfaces.yaml: skip (no annotation needed)

**Files:** `commands/specify.md` (modify)

## Step 7: Update `commands/check.md`

Add new mode `--surfaces`:

**`/spec.check --surfaces`**
1. Read `.specs/surfaces.yaml` (if absent → "No surfaces configured")
2. Scan filesystem for app directories with web markers
3. Compare: surfaces in config vs surfaces on disk
4. Report:
   - Surfaces in config but missing on disk → WARNING
   - App directories on disk not in config → WARNING (potential drift)
   - Validation errors (duplicate ids, testDir issues) → ERROR

**Files:** `commands/check.md` (modify)

## Step 8: Update `spec-system.md`

Document:
- `surfaces.yaml` schema and location
- Optional `Surfaces:` field in spec.md metadata
- `spec.check --surfaces` command

**Files:** `.specs/spec-system.md` (modify)

## Step 9: Update VERSION

Bump VERSION file to 8.

**Files:** `VERSION` (modify)

## Execution Order

Steps 1 → 2,3 (parallel) → 4 → 5,6,7,8 (parallel) → 9
