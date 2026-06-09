// LiveSpec traceability anchors
// @spec(AC-012)
// @spec(AC-014)
// @spec(AC-015)
// @spec(FR-012)
// @spec(FR-013)

import { test, expect } from '@playwright/test';

// @spec FR-010: Viewport matrix: mobile (375×667), tablet (768×1024), desktop (1920×1080) — spec.md#fr-010
// @spec FR-011: Per-viewport baseline directories — spec.md#fr-011
// @spec FR-012: Execute each test once per viewport — spec.md#fr-012
// @spec FR-013: Viewport applicability metadata — spec.md#fr-013
// @spec FR-014: --update-snapshots updates all viewports in one run — spec.md#fr-014

// @spec AC-015: Viewport-specific tests can be skipped via metadata — spec.md#ac-015
// FR-013: Define which projects (viewport+browser combos) apply to this test suite.
// Set to false to skip a project. Projects defined in playwright.config.ts.
const APPLICABLE_VIEWPORTS: Record<string, boolean> = {
  'mobile-chromium': true,
  'tablet-chromium': true,
  'desktop-chromium': true,
  'desktop-firefox': false, // Skip Firefox for responsive tests — covered by cross-browser suite
  'desktop-webkit': false,  // Skip WebKit for responsive tests — covered by cross-browser suite
};

test.beforeEach(({}, testInfo) => {
  const projectName = testInfo.project.name;
  // @spec AC-015: Skip inapplicable projects with metadata — spec.md#ac-015
  if (APPLICABLE_VIEWPORTS[projectName] === false) {
    test.skip(true, `Not applicable for project: ${projectName} (viewport already covered by cross-browser suite)`);
  }
});

test.describe('Responsive viewport testing', () => {
  // @spec AC-012: Tests run at mobile 375×667, tablet 768×1024, desktop 1920×1080 — spec.md#ac-012
  test('button renders correctly at current viewport', async ({ page }, testInfo) => {
    await page.goto('/components/button');

    // EC-009: Wait for full load before capture
    await page.waitForLoadState('networkidle');

    // @spec FR-011: snapshotPathTemplate in playwright.config.ts routes baseline to
    // baselines/mobile-chromium/, baselines/tablet-chromium/, etc.
    // @spec AC-014: Failures reported with viewport label (project name) — spec.md#ac-014
    await expect(page.locator('[data-testid="button"]')).toHaveScreenshot(
      'button-default.png',
      { animations: 'disabled' }
    );
  });

  // @spec AC-012: Navigation collapses to hamburger on mobile — spec.md#ac-012
  test('navigation layout at current viewport', async ({ page }, testInfo) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('[data-testid="nav"]')).toHaveScreenshot(
      'nav-viewport.png',
      { animations: 'disabled' }
    );
  });

  // Example: desktop-only component (skip on mobile/tablet)
  // Uncomment and configure APPLICABLE_VIEWPORTS to enable:
  //
  // test('data table with horizontal scroll (desktop only)', async ({ page }, testInfo) => {
  //   await page.goto('/dashboard/table');
  //   await page.waitForLoadState('networkidle');
  //   await expect(page).toHaveScreenshot('data-table-desktop.png', { animations: 'disabled' });
  // });
  // APPLICABLE_VIEWPORTS for this test: { 'desktop-chromium': true, all others: false }
});

// @spec FR-014: Update all viewport baselines in one pass — spec.md#fr-014
// To update baselines for all viewports:
//   npx playwright test tests/visual/responsive-viewports.spec.ts --update-snapshots
//
// The parallelized matrix (playwright.config.ts projects) handles all 3 Chromium viewports
// in a single run, updating mobile, tablet, and desktop baselines simultaneously.
//
// @spec FR-013: Viewport applicability — spec.md#fr-013
// EC-006: Viewport dimensions are pinned exactly in playwright.config.ts to prevent
// CI vs local drift. Never use viewport: null or deviceScaleFactor without explicit config.
