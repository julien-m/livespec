# Changelog — Feature 010: Visual Testing Complete

## 2026-05-04 — Fix: Monorepo path resolution — MOCKUP_DIR + detectRoutesDir surface-aware

- **Type:** Bug Fix
- **Spec modified:** No
- **Code modified:** `scripts/migrate-visual-tests.js` (both `generateE2ETemplate` and `generateLegacyTemplate` test templates; `detectRoutesDir()` helper)
- **Gaps closed:**
  - Generated test templates resolved `MOCKUP_DIR` via `process.cwd()`, which broke when Playwright was launched from a sub-app (e.g. `apps/web/` in a monorepo) — the scaffold then looked for `apps/web/.specs/design/screens/` instead of `<repo-root>/.specs/design/screens/`. Templates now derive `REPO_ROOT` from `import.meta.url` and walk parent directories until a `.specs/` folder is found, so the test works regardless of CWD or nesting depth.
  - `detectRoutesDir()` only scanned the repo-root `ROUTES_DIRS` array and ignored surface-aware paths from `.specs/surfaces.yaml` — meaning monorepo layouts like `apps/web/app/routes` were invisible. It now consults `SURFACES[*].routesDir` (resolved by `scripts/lib/surface-resolver.js`) before falling back to the legacy scan.
- **Verification:** `node --check` passes; 33/33 `tests/integration/test_migrate_visual.py` pass; source contains 4 `findRepoRoot` occurrences (2 templates × declaration + invocation), 0 functional `process.cwd()` calls in template literals.
- **Remaining:** None
- **Author:** spec.fix

---

## 2026-04-18 — Fix: Generated test template upgraded — exhaustive tests + Playwright API corrected

- **Type:** Bug Fix
- **Spec modified:** No
- **Code modified:** `scripts/migrate-visual-tests.js` (`generateE2ETemplate`, sentinel `dirs` counter), 14 generated spec files in downstream project (`claude-pilot/frontend/tests/e2e/001-*` through `014-*`)
- **Gaps closed:**
  - Playwright API bug: replaced invalid `page.toMatchSnapshot(filePath)` (jest/vitest API) with correct Playwright screenshot assertions via `expect(page).toHaveScreenshot(...)`
  - Tests are now exhaustive: 4 state-based tests per feature (full page with data, empty state, header/navigation, mobile view) instead of 2 generic tests
  - Empty state tests use `beforeEach` + targeted API endpoint overrides (LIFO pattern) instead of broad route rewrites
  - `fixtures.ts` detection: imports `mockAuthenticatedAPIs` / `mockEmptyDashboardAPIs` when `fixtures.ts` exists
  - Bad route inference fixed: 003 (`/api/workers/kill-all` → `/dashboard`), 006 (`/api/costs/by-project` → `/costs`), 007 (`/api/drift/configs` → `/drift`)
  - Sentinel `dirs` counter fixed: was always `dirs=0`; now correctly counts legacy baseline directories created
  - `@visual` tag added to all `test.describe` blocks for selective test runs
- **Remaining:** None
- **Author:** spec.fix

---

## 2026-04-18 — Fix: Migration tool architecture corrected (frontend/Pencil mode)

- **Type:** Bug Fix
- **Spec modified:** No
- **Code modified:** `scripts/migrate-visual-tests.js`
- **Artifacts removed:** `playwright.visual.config.ts` (generated artifact)
- **Gaps closed:** Migration tool now targets correct locations when run against real projects
- **Remaining:** None
- **Author:** spec.fix
- **Details:**
  - **Adaptive detection** — runtime detection of `frontend/tests/e2e/`, `frontend/playwright.config.ts`, `.specs/design/screens/`
  - **Frontend/Pencil mode** (when `frontend/tests/e2e/` exists): generates E2E tests in `frontend/tests/e2e/`, looks for Pencil mockups in `.specs/design/screens/current-*.png`, updates `frontend/playwright.config.ts`
  - **Legacy mode** (fallback): unchanged behavior (`tests/visual/` + `playwright.visual.config.ts` + `baselines/mockups/`)
  - `inferMockupFilename()` — searches `.specs/design/screens/` for `current-NN-*{slug}*-{viewport}.png`
  - New E2E template — mockup path logged as a design reference, `console.warn` + fallback to auto baseline when mockup missing (AC-005), and stable `toHaveScreenshot(...)` snapshot names for generated coverage
  - `cleanupOldMigration()` — removes `playwright.visual.config.ts` when switching to frontend mode
  - 205/205 meta-tests still pass

---

## 2026-04-17 — Fix: 4 migration tool gaps closed (functional)

- **Type:** Bug Fix
- **Spec modified:** No
- **Code modified:** `scripts/migrate-visual-tests.js`, `playwright.visual.config.ts` (created)
- **Gaps closed:** FR-024/AC-012 (playwright.visual.config.ts generation), test template TODO placeholders removed, completion report with next steps
- **Remaining:** None
- **Author:** spec.fix
- **Details:**
  - `ensurePlaywrightVisualConfig()` — creates `playwright.visual.config.ts` with 5 projects (mobile/tablet/desktop/firefox/webkit) + `snapshotPathTemplate: 'baselines/{projectName}/{arg}'` on `--generate`; hard guard preserves if exists (AC-030)
  - `inferRouteFromFeature()` — heuristic slug→route map + spec.md URL extraction; replaces `/TODO-replace-with-actual-route`
  - Improved test template — uses `page` screenshot instead of locator; adds fullpage + responsive test cases; removes `[data-testid="TODO-replace-selector"]`
  - `printCompletionReport()` — comprehensive next-steps report after `--generate`
  - All 11 integration tests still pass (sentinel format preserved)

---

## 2026-04-17 — Test: Artifact coverage mapped and Python regression suite validated

- **Type:** Test
- **Agent:** spec.test
- **AC coverage mapping:** 30/30 criteria linked to concrete artifacts in `implementation.md`
- **Playwright meta-tests:** Added to the repo, but not executed in this audit pass
- **Pytest suite:** 464 passed, 0 failed — no regressions from Feature 010
- **Coverage table:** Added to `implementation.md` as an artifact mapping table
- **Notes:** Validation for this audit used the Python test suite; Playwright artifacts remain scaffolded for downstream projects.

---

## 2026-04-17 — Implement: Feature 010 implemented

- **Type:** Implement
- **Steps completed:** 8/8 (Step 0 through Step 7)
- **Files created:** Workflow, docs, templates, scripts, feature-spec artifacts, and baseline placeholder directories were added
- **Baseline directories:** 9 directories created under `.specs/features/010-visual-testing-complete/baselines/`
- **Meta-tests:** Artifact-existence suite added in `tests/feature-010/visual-testing-complete.spec.ts`
- **FR/AC tracking:** See `implementation.md` for requirement-to-artifact mapping
- **Author:** spec.implement agent

---

## 2026-04-17 — Plan: Implementation plan created

- **Type:** Plan
- **Plan created:** `.specs/features/010-visual-testing-complete/plan.md`
- **Steps:** 8 steps (Step 0 through Step 7)
- **Files planned:** 4 TS test templates, 3 Node.js scripts, 8 Markdown docs, 1 CI workflow, 1 Playwright config extension, 1 meta-test, 9 baseline directories
- **Author:** spec.plan agent

## 2026-04-17 — Spec: Initial spec created

- **Type:** Feature
- **Spec modified:** Yes (sections: all — initial creation)
- **Code modified:** none
- **AC impacted:** AC-001 through AC-030 (all 30 ACs defined)
- **Author:** spec.specify agent
