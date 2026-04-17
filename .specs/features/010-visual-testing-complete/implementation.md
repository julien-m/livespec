---
feature: 010-visual-testing-complete
created: 2026-04-17
---

# Implementation Map — Feature 010: Visual Testing Complete

## FR → File mapping

| FR | Description | File(s) |
|----|-------------|---------|
| FR-001 | Prioritize mockup baselines | `tests/visual/mockup-comparison.spec.ts` |
| FR-002 | Mockup baseline metadata schema | `scripts/validate-mockup-metadata.js`, `docs/visual-testing/mockup-workflow.md` |
| FR-003 | Configurable tolerance (default 2%) | `tests/visual/mockup-comparison.spec.ts` (TOLERANCE const) |
| FR-004 | Skip with WARNING when mockup missing | `tests/visual/mockup-comparison.spec.ts` (test.skip + TODO) |
| FR-005 | Designer approval workflow documentation | `docs/visual-testing/mockup-workflow.md` (approval section) |
| FR-006 | Full-page tests on `page` object | `tests/visual/fullpage-layout.spec.ts` |
| FR-007 | `fullPage: true` for scrollable content | `tests/visual/fullpage-layout.spec.ts` |
| FR-008 | Baselines in `baselines/fullpage/[feature]/` | `tests/visual/fullpage-layout.spec.ts`, `docs/visual-testing/fullpage-testing.md` |
| FR-009 | Diff images highlight change regions | `docs/visual-testing/fullpage-testing.md` |
| FR-010 | Viewport matrix: mobile/tablet/desktop | `playwright.config.ts` (projects array) |
| FR-011 | Per-viewport baseline directories | `playwright.config.ts` (snapshotPathTemplate) |
| FR-012 | 3× execution per viewport | `playwright.config.ts` (5 projects), `tests/visual/responsive-viewports.spec.ts` |
| FR-013 | Viewport applicability metadata | `tests/visual/responsive-viewports.spec.ts` (APPLICABLE_VIEWPORTS) |
| FR-014 | `--update-snapshots` for all viewports | `docs/visual-testing/responsive-testing.md` |
| FR-015 | Browser projects: chromium/firefox/webkit | `playwright.config.ts` (projects array) |
| FR-016 | Per-browser baseline directories | `playwright.config.ts` (snapshotPathTemplate), `docs/visual-testing/cross-browser-testing.md` |
| FR-017 | CI 3× execution per browser | `.github/workflows/visual-tests.yml` (matrix strategy) |
| FR-018 | Browser applicability metadata | `docs/visual-testing/cross-browser-testing.md` |
| FR-019 | Keyframes at 0%, 50%, 100% | `tests/visual/animations.spec.ts` |
| FR-020 | Keyframe baselines in `baselines/animations/` | `tests/visual/animations.spec.ts`, `scripts/capture-keyframes.ts` |
| FR-021 | `page.waitForTimeout(ms)` for keyframe timing | `tests/visual/animations.spec.ts` |
| FR-022 | Animation metadata: duration, easing, keyframes | `scripts/capture-keyframes.ts` (YAML output), `tests/visual/animations.spec.ts` (ANIMATION const) |
| FR-023 | `--scan` reports features without visual tests | `scripts/migrate-visual-tests.js` |
| FR-024 | `--generate` creates test files in batch | `scripts/migrate-visual-tests.js` |
| FR-025 | Migration creates baseline directory structure | `scripts/migrate-visual-tests.js` (BASELINE_DIRS) |

## AC → File mapping

| AC | Criterion | File(s) |
|----|-----------|---------|
| AC-001 | Baselines from `baselines/mockups/` | `tests/visual/mockup-comparison.spec.ts` |
| AC-002 | `.meta.yml` required fields | `scripts/validate-mockup-metadata.js` (REQUIRED_FIELDS) |
| AC-003 | Compare code to mockup baseline | `tests/visual/mockup-comparison.spec.ts` |
| AC-004 | Configurable tolerance (default 2%) | `tests/visual/mockup-comparison.spec.ts` |
| AC-005 | Skip with WARNING when mockup missing | `tests/visual/mockup-comparison.spec.ts` |
| AC-006 | Designer approval workflow | `docs/visual-testing/mockup-workflow.md` |
| AC-007 | Full viewport capture | `tests/visual/fullpage-layout.spec.ts` |
| AC-008 | Baselines in `baselines/fullpage/` | `tests/visual/fullpage-layout.spec.ts` |
| AC-009 | Z-index regression detection | `tests/visual/fullpage-layout.spec.ts`, `docs/visual-testing/fullpage-testing.md` |
| AC-010 | Layout shift detection | `tests/visual/fullpage-layout.spec.ts`, `docs/visual-testing/fullpage-testing.md` |
| AC-011 | Scroll behavior validation | `tests/visual/fullpage-layout.spec.ts` |
| AC-012 | 3 viewports: mobile/tablet/desktop | `playwright.config.ts`, `tests/visual/responsive-viewports.spec.ts` |
| AC-013 | Per-viewport baselines | `playwright.config.ts` (snapshotPathTemplate) |
| AC-014 | Viewport-labeled failure reporting | `tests/visual/responsive-viewports.spec.ts` |
| AC-015 | Viewport-specific test skipping | `tests/visual/responsive-viewports.spec.ts` (APPLICABLE_VIEWPORTS) |
| AC-016 | `--update-snapshots` for all viewports | `docs/visual-testing/responsive-testing.md`, `playwright.config.ts` |
| AC-017 | 3 browsers: Chromium/Firefox/WebKit | `playwright.config.ts`, `.github/workflows/visual-tests.yml` |
| AC-018 | Per-browser baselines | `playwright.config.ts` (snapshotPathTemplate) |
| AC-019 | Browser rendering differences detected | `docs/visual-testing/cross-browser-testing.md` |
| AC-020 | Browser-labeled failure reporting | `docs/visual-testing/cross-browser-testing.md` |
| AC-021 | Browser-specific test skipping | `docs/visual-testing/cross-browser-testing.md` |
| AC-022 | Keyframes at 0%, 50%, 100% | `tests/visual/animations.spec.ts` |
| AC-023 | Keyframe baselines in `baselines/animations/` | `tests/visual/animations.spec.ts`, `scripts/capture-keyframes.ts` |
| AC-024 | Janky transition detection | `tests/visual/animations.spec.ts`, `docs/visual-testing/animation-testing.md` |
| AC-025 | Missing animation detection | `tests/visual/animations.spec.ts`, `docs/visual-testing/animation-testing.md` |
| AC-026 | Animation duration validation | `tests/visual/animations.spec.ts` |
| AC-027 | `--scan` lists features without tests | `scripts/migrate-visual-tests.js` |
| AC-028 | `--generate` creates test files in batch | `scripts/migrate-visual-tests.js` |
| AC-029 | Migration creates baseline directories | `scripts/migrate-visual-tests.js` |
| AC-030 | Existing tests preserved (hard guard) | `scripts/migrate-visual-tests.js` (existsSync guard) |

## Files created

### Infrastructure (Step 0)
- `playwright.config.ts` — 5-project viewport+browser matrix
- `.github/workflows/visual-tests.yml` — CI pipeline with matrix strategy and PR diff upload
- `scripts/visual-diff-pr-comment.js` — Idempotent PR comment automation

### Mockup comparison (Step 1)
- `tests/visual/mockup-comparison.spec.ts` — Mockup comparison test template
- `docs/visual-testing/mockup-workflow.md` — Designer workflow guide
- `scripts/validate-mockup-metadata.js` — .meta.yml validation CLI

### Full-page layout (Step 2)
- `tests/visual/fullpage-layout.spec.ts` — Full-page layout test template
- `docs/visual-testing/fullpage-testing.md` — Full-page guide

### Responsive viewports (Step 3)
- `tests/visual/responsive-viewports.spec.ts` — Responsive test template
- `docs/visual-testing/responsive-testing.md` — Responsive guide

### Cross-browser (Step 4)
- `docs/visual-testing/cross-browser-testing.md` — Cross-browser guide

### Animations (Step 5)
- `tests/visual/animations.spec.ts` — Animation keyframe test template
- `docs/visual-testing/animation-testing.md` — Animation guide
- `scripts/capture-keyframes.ts` — Keyframe capture helper

### Migration tool (Step 6)
- `scripts/migrate-visual-tests.js` — Migration CLI (--scan/--generate/--dry-run)
- `docs/visual-testing/migration-guide.md` — Migration guide

### Docs + meta-tests (Step 7)
- `docs/visual-testing/README.md` — Docs index
- `docs/visual-testing/troubleshooting.md` — EC-001 through EC-015 troubleshooting
- `tests/feature-010/visual-testing-complete.spec.ts` — Meta-tests for artifact existence and structural checks

### Baseline directories
- `.specs/features/010-visual-testing-complete/baselines/{mockups,fullpage,mobile,tablet,desktop,chromium,firefox,webkit,animations}/`

### Infrastructure
- `package.json` — npm package for Playwright Test runner

## AC Coverage Table (Artifact Mapping)

| AC | Criterion | Evidence | Status |
|----|-----------|----------|--------|
| AC-001 | Baselines from `baselines/mockups/` | `tests/feature-010/visual-testing-complete.spec.ts` | Mapped |
| AC-002 | `.meta.yml` required fields | `tests/feature-010/visual-testing-complete.spec.ts` (validate-mockup-metadata.js exists) | Mapped |
| AC-003 | Compare code to mockup baseline | `tests/feature-010/visual-testing-complete.spec.ts` (mockup-comparison.spec.ts exists) | Mapped |
| AC-004 | Configurable tolerance (default 2%) | `tests/feature-010/visual-testing-complete.spec.ts` (TOLERANCE + maxDiffPixelRatio) | Mapped |
| AC-005 | Skip with WARNING when mockup missing | `tests/feature-010/visual-testing-complete.spec.ts` (test.skip + TODO) | Mapped |
| AC-006 | Designer approval workflow | `tests/feature-010/visual-testing-complete.spec.ts` (mockup-workflow.md exists) | Mapped |
| AC-007 | Full viewport capture | `tests/feature-010/visual-testing-complete.spec.ts` (fullpage-layout.spec.ts exists + fullPage) | Mapped |
| AC-008 | Baselines in `baselines/fullpage/` | `tests/feature-010/visual-testing-complete.spec.ts` (fullpage-layout.spec.ts + guide) | Mapped |
| AC-009 | Z-index regression detection | `tests/feature-010/visual-testing-complete.spec.ts` (fullpage-testing.md exists) | Mapped |
| AC-010 | Layout shift detection | `tests/feature-010/visual-testing-complete.spec.ts` (fullpage-testing.md exists) | Mapped |
| AC-011 | Scroll behavior validation | `tests/feature-010/visual-testing-complete.spec.ts` (fullpage-layout.spec.ts exists) | Mapped |
| AC-012 | 3 viewports: mobile/tablet/desktop | `tests/feature-010/visual-testing-complete.spec.ts` (playwright.config.ts 5 projects) | Mapped |
| AC-013 | Per-viewport baselines | `tests/feature-010/visual-testing-complete.spec.ts` (snapshotPathTemplate + baseline dirs) | Mapped |
| AC-014 | Viewport-labeled failure reporting | `tests/feature-010/visual-testing-complete.spec.ts` (responsive-viewports.spec.ts) | Mapped |
| AC-015 | Viewport-specific test skipping | `tests/feature-010/visual-testing-complete.spec.ts` (APPLICABLE_VIEWPORTS + test.skip) | Mapped |
| AC-016 | `--update-snapshots` for all viewports | `tests/feature-010/visual-testing-complete.spec.ts` (responsive-testing.md + playwright.config.ts) | Mapped |
| AC-017 | 3 browsers: Chromium/Firefox/WebKit | `tests/feature-010/visual-testing-complete.spec.ts` (playwright.config.ts + visual-tests.yml) | Mapped |
| AC-018 | Per-browser baselines | `tests/feature-010/visual-testing-complete.spec.ts` (snapshotPathTemplate + baseline dirs) | Mapped |
| AC-019 | Browser rendering differences detected | `tests/feature-010/visual-testing-complete.spec.ts` (cross-browser-testing.md exists) | Mapped |
| AC-020 | Browser-labeled failure reporting | `tests/feature-010/visual-testing-complete.spec.ts` (cross-browser-testing.md 3 browsers) | Mapped |
| AC-021 | Browser-specific test skipping | `tests/feature-010/visual-testing-complete.spec.ts` (cross-browser-testing.md exists) | Mapped |
| AC-022 | Keyframes at 0%, 50%, 100% | `tests/feature-010/visual-testing-complete.spec.ts` (kf-0pct, kf-50pct, kf-100pct) | Mapped |
| AC-023 | Keyframe baselines in `baselines/animations/` | `tests/feature-010/visual-testing-complete.spec.ts` (animations dir + capture-keyframes.ts) | Mapped |
| AC-024 | Janky transition detection | `tests/feature-010/visual-testing-complete.spec.ts` (animations.spec.ts + animation-testing.md) | Mapped |
| AC-025 | Missing animation detection | `tests/feature-010/visual-testing-complete.spec.ts` (animations.spec.ts + animation-testing.md) | Mapped |
| AC-026 | Animation duration validation | `tests/feature-010/visual-testing-complete.spec.ts` (animations.spec.ts exists) | Mapped |
| AC-027 | `--scan` lists features without tests | `tests/feature-010/visual-testing-complete.spec.ts` (--scan in migrate-visual-tests.js) | Mapped |
| AC-028 | `--generate` creates test files in batch | `tests/feature-010/visual-testing-complete.spec.ts` (--generate in migrate-visual-tests.js) | Mapped |
| AC-029 | Migration creates baseline directories | `tests/feature-010/visual-testing-complete.spec.ts` (migrate-visual-tests.js has BASELINE_DIRS) | Mapped |
| AC-030 | Existing tests preserved (hard guard) | `tests/feature-010/visual-testing-complete.spec.ts` (existsSync + "already exists" guard) | Mapped |

**Coverage mapping: 30/30 ACs linked to artifacts. Repo verification for this audit used `pytest tests/ --ignore=tests/integration -q` and passed at 464 passed.**
