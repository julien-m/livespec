## 2026-06-08 — [Spec Update]: Normalize changelog format

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None
- **AC impacted:** None
- **Author:** spec.doctor

---

# Changelog — 011-visual-migrate-integration

---

### 2026-04-18 — Fix: Generator template quality — 3 issues resolved

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** scripts/migrate-visual-tests.js
- **AC impacted:** None (template quality improvement, existing ACs still satisfied)
- **Author:** spec.fix
- **Fixes:**
  1. Issue 1 (Mockup comparison): `toHaveScreenshot(path.basename(mockupPath))` was using the Pencil filename as the snapshot name, making Playwright create an auto-baseline with that name instead of comparing to the mockup. Fixed: mockup is now documented as a design reference only, and generated tests always use stable screenshot names like `${slug}-full.png`.
  2. Issue 2 (Generic selectors): Header test used `'header, nav, [data-testid="header"]'` — generic and imprecise. Fixed: 5 new analysis helpers (`analyzeExistingTests`, `detectFixturesFromDir`, `extractSelectorsFromExistingTests`, `extractWaitPatterns`, `extractCommonTestCases`) extract the most-used project selector containing "header"; falls back to generic if none found.
  3. Issue 3 (Inline routes): Empty-state test used hardcoded `page.route('**/api/workers**', ...)` etc. Fixed: `detectFixturesFromDir` detects exported `mockEmpty*` fixture from `fixtures.ts`; uses it when found, else falls back to single `**/api/**` catch-all with a TODO comment.
- **Analysis computed once** before the generation loop (`analyzeExistingTests`) — O(#existing_tests) overhead, not per-feature.
- **All 11 integration tests still pass** — template behavior (file creation, sentinel, idempotency) unchanged.

---

### 2026-04-17 — Test: AC coverage validated

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None (test report generated)
- **Coverage:** 11 automated integration tests passing; AC-011 validated by command-spec review
- **Report:** `checks/2026-04-17-test.md`
- **Author:** spec.test

---

### 2026-04-17 — Feature: Initial implementation of visual migrate integration

- **Type:** Feature
- **Spec modified:** No
- **Code modified:** scripts/migrate-visual-tests.js, commands/spec-migrate.md, tests/integration/test_migrate_visual.py, tests/integration/fixtures/migrate-visual/
- **AC impacted:** AC-001 through AC-012 (all satisfied)
- **Author:** claude-code

---

### 2026-04-17 — Plan: Technical plan regenerated (review findings addressed)

- **Type:** Feature
- **Spec modified:** No
- **Code modified:** None (plan.md updated)
- **AC impacted:** None (pre-implementation)
- **Author:** spec.plan
- **Changes from regeneration:** (1) Visual scaffolding moved to commands/spec-migrate.md command layer (not migrate.sh); (2) "already up to date" early-exit removed so scaffolding runs unconditionally; (3) Shell injection avoided — sentinel uses files=N dirs=M, no inline node -e; (4) set +e/set -e guards around subprocess call; (5) Integration tests moved to tests/integration/test_migrate_visual.py; (6) FR-005 added to Step 1 FR coverage.

---

### 2026-04-17 — Spec: Feature specification created

- **Type:** Spec Update
- **Spec modified:** Yes (created — all sections)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-012 (all defined)
- **Author:** spec.specify
