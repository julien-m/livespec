# Test Protocol

> Centralized testing rules for LiveSpec — stack-agnostic, zero hardcoded commands.
> Referenced by `/spec.implement`, `/spec.plan`, and `/spec.check`.

---

## Visual Infrastructure Requirements

Visual testing requires the following setup before tests can capture baselines:

1. **Playwright installation** — Verify `@playwright/test` is in `package.json` dev dependencies
2. **Visual helper scaffold** — `tests/e2e/helpers/visual.ts` provides `captureBaseline()`, `compareRegression()`, and `compareDesign()` utilities
3. **Design mockups** — Reference `.specs/design/screens/` for Pencil-generated screen images to compare against
4. **Visual test mapping** — `.specs/testing/strategy.md` documents the mapping of features to visual test files (convention: `src/components/Button.tsx` → `tests/e2e/components/**/*button*`)
5. **Baseline storage** — `.specs/features/{NNN}/baselines/` holds baseline PNG files, committed only after Phase 4 non-visual tests pass
6. **Dependencies** — Ensure `pixelmatch` and `sharp` are installed (via `bun add -d` if needed)

Read [`visual-baselines.md`](visual-baselines.md) for screenshot capture protocol and lifecycle rules.

---

## Modules

| File | What it covers | When to read |
|---|---|---|
| [`discovery.md`](discovery.md) | Detect ecosystem, test runners, visual tools, verify & record | `/spec.init` Phase B, `/spec.plan` Step 7.5, first `/spec.implement` if not yet resolved, `/spec.test` Phase 0 |
| [`execution-rules.md`](execution-rules.md) | When to run tests + final validation checklist | Every `/spec.implement` phase 3, 4, 6 and `/spec.test` Phase 4 |
| [`failure-handling.md`](failure-handling.md) | Iteration limits, troubleshooting, error reporting format | On test failure during `/spec.implement` or `/spec.test` |
| [`visual-baselines.md`](visual-baselines.md) | Screenshot capture, comparison, thresholds, archival | UI features only (skip with `--no-visual`) |

All commands come from the **Resolved Test Commands** table in `plan.md` or `.specs/testing/strategy.md`. Never hardcode commands.

**Standalone test validation:** `/spec.test` orchestrates the full test lifecycle — audit AC coverage, generate missing tests from Gherkin, execute the suite, capture visual baselines, and produce a report. Referenced by `/spec.implement` Phase 6, `/spec.feature` Phase 3.5, and `/spec.ship` Step 3.5.

---

*LiveSpec Test Protocol v1.1*
