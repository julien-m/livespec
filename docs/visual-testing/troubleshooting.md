# Troubleshooting Guide

Fixes for all edge cases (EC-001 through EC-015) in the visual testing framework.

---

## EC-001: Retina baseline mismatch (1x vs 2x resolution)

**Symptom:** Tests fail because mockup was exported at 2x (Retina) but code renders at 1x, or vice versa.

**Fix:** Specify `resolution` in `.meta.yml` and match `deviceScaleFactor` in `playwright.config.ts`:

```yaml
# baselines/mockups/button.meta.yml
resolution: 2x
```

```typescript
// playwright.config.ts — for 2x (Retina) consistency
use: {
  deviceScaleFactor: 2,
}
```

If your mockup was exported at 1x, either re-export at 2x (preferred) or set `deviceScaleFactor: 1`.

---

## EC-002: Test uses stale Figma export

**Symptom:** Designer updated the Figma mockup but forgot to re-export the PNG. Tests compare against the old design.

**Fix:** Re-export the PNG from Figma and update the metadata:

```yaml
# Update .meta.yml after re-export
exported_date: 2026-04-17
last_updated: 2026-04-17
```

Consider adding a Figma webhook to notify the team when mockups are updated.

---

## EC-003: Dynamic content causes flaky tests

**Symptom:** Tests fail non-deterministically because page contains timestamps, random IDs, or live data.

**Fix:** Use the `mask` option to exclude dynamic regions:

```typescript
await expect(page).toHaveScreenshot('dashboard.png', {
  mask: [
    page.locator('[data-testid="timestamp"]'),
    page.locator('[data-testid="random-token"]'),
    page.locator('[data-testid="user-avatar"]'),
    page.locator('[data-testid="live-chart"]'),
  ],
});
```

Masked regions are filled with a solid color in the comparison. The baseline and actual must have the same mask applied.

---

## EC-004: Animation timing variance

**Symptom:** Animation tests are flaky — pass locally but fail in CI due to ±10-20ms timing differences.

**Fix:** Increase `maxDiffPixelRatio` for animation tests:

```typescript
const ANIM_TOLERANCE = 0.08; // 8% for animations (vs 2% for static tests)
```

If still flaky, increase to `0.10` (10%). Also ensure `waitForTimeout` uses fixed ms values — do not use `performance.now()` or derive from CSS values at runtime.

---

## EC-005: Browser font not available in CI

**Symptom:** Tests pass locally but fail in CI with visible font rendering differences.

**Fix:** Install browsers with system dependencies in CI:

```yaml
# .github/workflows/visual-tests.yml
- run: npx playwright install --with-deps chromium
- run: npx playwright install --with-deps firefox
- run: npx playwright install --with-deps webkit
```

For consistent font rendering, prefer web fonts loaded via `@font-face` or CDN — they render identically across OS and CI runners.

---

## EC-006: Viewport different in CI vs local

**Symptom:** Tests pass locally at viewport 1280×800 but fail in CI at a slightly different size.

**Fix:** Viewport dimensions are pinned exactly in `playwright.config.ts`. Never use `viewport: null` or omit the viewport:

```typescript
// playwright.config.ts
projects: [
  { name: 'desktop-chromium', use: { viewport: { width: 1920, height: 1080 } } },
]
```

If you're running locally without specifying a project, use:

```bash
npx playwright test --project=desktop-chromium
```

---

## EC-007: Migration generates tests for backend-only feature

**Symptom:** `migrate-visual-tests.js --generate` creates a test file for a Python validator or CLI-only feature.

**Fix:** The migration tool uses UI keyword heuristics. If it misclassifies a feature, the generated test file has `test.skip` guards — it won't fail. Manually delete the file and re-run `--generate` (the tool will skip it next time since the file exists).

To skip a feature during migration without deleting it, add a placeholder test file:

```typescript
// tests/visual/my-backend-feature.spec.ts
import { test } from '@playwright/test';
test.skip(() => true, 'No UI — backend-only feature');
```

---

## EC-008: Baseline collision between features

**Symptom:** Two features share a component name (e.g., `button`), and their baselines overwrite each other.

**Fix:** Baselines are namespaced by feature slug in the directory structure:

```
baselines/mockups/
  auth/button.png           ← auth feature
  dashboard/button.png      ← dashboard feature
```

Ensure test files use a feature-scoped `MOCKUP_DIR`:

```typescript
const MOCKUP_DIR = path.join(__dirname, '../../baselines/mockups/auth');
```

---

## EC-009: Component not loaded before capture

**Symptom:** Screenshots show loading states, spinners, or empty components.

**Fix:** Always wait for the component to be fully loaded:

```typescript
await page.goto('/components/my-component');
await page.waitForLoadState('networkidle');
// Also wait for the specific element if it loads asynchronously
await page.waitForSelector('[data-testid="component-root"]', { state: 'visible' });
// Or wait for a specific text/attribute that indicates loaded state
await page.waitForFunction(() => document.querySelector('[data-testid="component-root"]')?.dataset.loaded === 'true');
```

---

## EC-010: Drop shadow vs CSS shadow tolerance

**Symptom:** Mockup has Figma drop shadow, code uses CSS `box-shadow`. Slight rendering difference causes test failure even when visually equivalent.

**Fix:** Increase tolerance for components with shadows:

```typescript
const TOLERANCE = 0.05; // 5% for drop shadow / gradient components
```

Run the test once to see the actual diff percentage, then set tolerance slightly above it. If the designer agrees the CSS shadow is visually equivalent, they can approve the diff and update the baseline.

---

## EC-011: Keyframe captured at wrong timing

**Symptom:** The 50% keyframe snapshot shows the initial or final state, not the mid-transition.

**Fix:** Use fixed `waitForTimeout()` with the exact animation duration. Common causes of wrong timing:
- Animation hasn't started yet when 0% capture fires → add `await page.waitForTimeout(16)` (1 frame) before triggering
- CI is slow → increase the wait time: `durationMs * 0.5 + 50` (add 50ms buffer)

```typescript
await page.locator(trigger).click();
await page.waitForTimeout(16); // Wait for animation to start (1 frame buffer)
await page.waitForTimeout(ANIMATION.durationMs * 0.5);
// Now capture 50% keyframe
```

---

## EC-012: Full-page baseline file too large

**Symptom:** Full-page screenshot is very large (>5MB), causing slow tests or storage issues.

**Fix:** Use viewport-only screenshots instead of `fullPage: true`:

```typescript
// Instead of:
await expect(page).toHaveScreenshot('page.png', { fullPage: true });

// Use:
await expect(page).toHaveScreenshot('page.png', { fullPage: false }); // viewport only
```

For very long pages that need scroll coverage, capture at specific scroll positions:

```typescript
await page.evaluate(() => window.scrollTo(0, 0));
await expect(page).toHaveScreenshot('page-top.png');

await page.evaluate(() => window.scrollTo(0, 1000));
await expect(page).toHaveScreenshot('page-mid.png');
```

---

## EC-013: CI matrix 9 jobs, running too long

**Symptom:** Full 9-job matrix (3 viewports × 3 browsers) takes 45+ minutes in CI.

**Fix:** Default configuration uses 5 critical combinations. To restore or customize:

```yaml
# .github/workflows/visual-tests.yml
strategy:
  matrix:
    project:
      # 5 critical (default)
      - mobile-chromium
      - tablet-chromium
      - desktop-chromium
      - desktop-firefox
      - desktop-webkit
      # Uncomment for full 9-job matrix:
      # - mobile-firefox
      # - mobile-webkit
      # - tablet-firefox
      # - tablet-webkit
```

Consider running the full matrix on a weekly schedule rather than every PR.

---

## EC-014: Diff images accidentally committed to repo

**Symptom:** `test-results/` or `playwright-report/` directories appear in git status.

**Fix:** Ensure `.gitignore` includes:

```
test-results/
playwright-report/
```

If they were already committed, remove them:

```bash
git rm -r --cached test-results/ playwright-report/
git commit -m "chore: remove committed test results from repo"
```

---

## EC-015: Tests pass locally, fail in CI (font missing)

**Symptom:** A test passes on your machine but fails in CI with font rendering differences.

**Fix:** This is the same as EC-005. Install with system dependencies in CI:

```yaml
- run: npx playwright install --with-deps
```

To debug: run the CI command locally using Docker with the same base image:

```bash
docker run --rm -v $(pwd):/app -w /app mcr.microsoft.com/playwright:v1.40.0-jammy bash -c "npm ci && npx playwright test"
```

This reproduces the exact CI environment locally.

---

## Related

- **Read** [`README.md`](README.md) — documentation index
- **Read** [`mockup-workflow.md`](mockup-workflow.md) — Figma export and approval workflow
