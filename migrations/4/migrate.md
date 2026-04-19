---
version: 4
description: "Upgrade visual testing to v4 standards: maxDiffPixels threshold, Docker render pinning"
date: 2026-04-14
---

<!-- @spec FR-009: migration v4 manifest — .specs/features/003-visual-testing-fidelity/spec.md#fr-009 -->

# Migration v4: Visual Testing Fidelity

Upgrades visual testing infrastructure to v4 standards:
- Replaces `maxDiffPixelRatio` with `maxDiffPixels: 0` in Playwright config
- Generates `docker-compose.visual.yml` stub for render environment pinning
- Backs up any modified files before changes

After migration completes:
1. Review the updated `playwright.config.ts`
2. Run `spec.test --reset-baselines` to regenerate baselines with the new settings
3. Approve the new baselines with the human approval gate

## Idempotency Check

Before running any action, check if the project is already at v4:

```
IF .livespec-version file contains "4" or greater:
  REPORT: "Already at v4 — no changes needed"
  EXIT (no further actions)
```

## Actions

### BACKUP

Before modifying any file, create a `.bak` copy of the original:

```
FOR each file modified by subsequent actions:
  COPY <file> TO <file>.bak
  (backup created before ANY modification)
```

### REPLACE_CONFIG

Search for `maxDiffPixelRatio` in all `playwright.config.ts` / `playwright.config.js` files in the project root and `e2e/` or `tests/` directories.

For each file found:

```
FIND:    maxDiffPixelRatio: <any_value>
REPLACE: maxDiffPixels: 0
         // Zero tolerance — any pixel diff is a regression.
         // Per-test override: { maxDiffPixels: 10 } for screens with aa_tolerance: true.
LOG: "Updated playwright.config.ts: replaced maxDiffPixelRatio with maxDiffPixels: 0"
```

If no `maxDiffPixelRatio` found in any file:

```
LOG: "No maxDiffPixelRatio found — playwright config already uses correct threshold or no visual tests configured"
```

### FRONTEND CHECK (prerequisite for GENERATE_FILE)

Before creating `docker-compose.visual.yml`, check if the project has a web frontend layer:

Check for any of the following indicators:
- Directory exists: `frontend/tests/e2e/`, `frontend/`, or any of `src/app/routes`, `frontend/app/routes`, `app/routes`, `src/routes`, `src/pages`, `pages`
- File exists: `frontend/playwright.config.ts`, `playwright.config.ts`, `cypress.config.ts`
- Directory exists: `.specs/design/screens/` (Pencil mockups)
- File `package.json` exists AND contains one of these in `dependencies` or `devDependencies`: `react`, `vue`, `next`, `nuxt`, `svelte`, `@angular`, `astro`, `vite`, `webpack`, `remix`, `solid-js`, `qwik`

If NONE of the above are found:

```
LOG: "No web frontend detected — docker-compose.visual.yml skipped."
SKIP the GENERATE_FILE action entirely (proceed to SET_VERSION below).
```

If ANY indicator is found: proceed with GENERATE_FILE as documented below.

### GENERATE_FILE

Check if `docker-compose.visual.yml` exists in the project root.

**If absent:**

```
CREATE docker-compose.visual.yml:

# Run baseline capture with: docker compose run visual-tests
# This ensures identical pixel output across macOS and CI (Linux + Chrome).
# LiveSpec migration v4 — generated 2026-04-14
services:
  visual-tests:
    image: mcr.microsoft.com/playwright:v1.44.0-jammy
    volumes:
      - ./tests:/app/tests
      - ./.specs:/app/.specs
    command: npx playwright test tests/e2e/screens/
    working_dir: /app

LOG: "Generated docker-compose.visual.yml with Playwright Docker image"
```

**If already exists:**

```
LOG: "docker-compose.visual.yml already exists — skipping generation (too risky to overwrite user-customized config)"
```

Do NOT overwrite existing `docker-compose.visual.yml` — the user may have customized it.

### SET_VERSION 4

```
WRITE "4" to .livespec-version
LOG: "Updated .livespec-version to 4"
```

## Migration Report

After all actions complete, display:

```
Migration v4 complete.

Files modified:
  - playwright.config.ts (maxDiffPixelRatio → maxDiffPixels: 0)
  - playwright.config.ts.bak (original backup)
  - docker-compose.visual.yml (generated)
  - .livespec-version (set to 4)

Next steps:
  1. Review the updated playwright.config.ts
  2. Run spec.test --reset-baselines to regenerate baselines with the new settings
  3. Approve the new baselines with the human approval gate
```

If no files were modified (all already correct):

```
Migration v4 complete — no changes needed.
All visual testing settings already match v4 standards.
```

## Edge Cases

- **`docker-compose.visual.yml` exists with wrong Playwright version:** Skip generation, warn:
  ```
  Warning: docker-compose.visual.yml exists but may use an outdated Playwright image.
  Check the image version and update manually if needed.
  ```
- **`playwright.config.ts` has multiple `maxDiffPixelRatio` occurrences:** Replace all occurrences, log count.
- **No `playwright.config.ts` found:** Skip REPLACE_CONFIG, log: "No playwright config found — visual testing may not be set up yet. Run spec.test to initialize."
