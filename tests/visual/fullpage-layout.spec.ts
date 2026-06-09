// LiveSpec traceability anchors
// @spec(AC-007)
// @spec(AC-008)
// @spec(AC-009)
// @spec(AC-010)
// @spec(AC-011)
// @spec(FR-006)
// @spec(FR-007)
// @spec(FR-008)

import { test, expect } from '@playwright/test';

// @spec FR-006: Full-page tests capture entire viewport — .specs/features/010-visual-testing-complete/spec.md#fr-006
// @spec FR-007: fullPage: true for scrollable content — .specs/features/010-visual-testing-complete/spec.md#fr-007
// @spec FR-008: Baselines in baselines/fullpage/[feature]/[screen]-[state].png — spec.md#fr-008
// @spec FR-009: Diff images highlight regions with changes — spec.md#fr-009

// Configuration — replace with your feature's routes and selectors
const FEATURE = 'dashboard';

test.describe(`Full-page layout validation: ${FEATURE}`, () => {
  // @spec AC-007: Full-page screenshot captures entire viewport — spec.md#ac-007
  // @spec AC-009: Z-index regression detection — spec.md#ac-009
  test('modal open — z-index validation (full page)', async ({ page }) => {
    await page.goto('/dashboard');

    // EC-009: Wait for full load before capture
    await page.waitForLoadState('networkidle');

    // Open the modal
    await page.locator('[data-testid="open-modal"]').click();
    await page.waitForSelector('[data-testid="modal"]', { state: 'visible' });

    // @spec FR-007: fullPage: true captures entire scrollable area
    await expect(page).toHaveScreenshot('dashboard-modal-open.png', {
      fullPage: true,
      animations: 'disabled',
      // EC-003: Mask dynamic content regions (timestamps, random data)
      // mask: [page.locator('[data-testid="timestamp"]')],
    });
  });

  // @spec AC-010: Layout shift detection — spec.md#ac-010
  test('sidebar and content alignment (viewport only)', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // fullPage: false — viewport only for layout alignment checks
    await expect(page).toHaveScreenshot('dashboard-layout.png', {
      fullPage: false,
      animations: 'disabled',
    });
  });

  // @spec AC-011: Scroll behavior — sticky headers — spec.md#ac-011
  test('sticky header remains visible during scroll', async ({ page }) => {
    await page.goto('/long-page');
    await page.waitForLoadState('networkidle');

    // Scroll to trigger sticky behavior
    await page.evaluate(() => window.scrollTo(0, 500));

    await expect(page).toHaveScreenshot('sticky-header-scrolled.png', {
      animations: 'disabled',
    });
  });

  // @spec AC-011: Scroll-locked modal validation — spec.md#ac-011
  test('scroll locked when modal is open', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    await page.locator('[data-testid="open-modal"]').click();
    await page.waitForSelector('[data-testid="modal"]', { state: 'visible' });

    // Attempt scroll — should be locked
    await page.evaluate(() => window.scrollTo(0, 500));

    // EC-003: If page has timestamps or other dynamic content, mask them:
    // const dynamicMasks = [page.locator('[data-testid="timestamp"]')];
    await expect(page).toHaveScreenshot('dashboard-modal-scroll-locked.png', {
      animations: 'disabled',
    });
  });
});

// Baseline paths (FR-008):
//   baselines/fullpage/dashboard/dashboard-modal-open.png
//   baselines/fullpage/dashboard/dashboard-layout.png
//   baselines/fullpage/dashboard/sticky-header-scrolled.png
//   baselines/fullpage/dashboard/dashboard-modal-scroll-locked.png
//
// EC-012: If full-page screenshot > 5MB, consider using fullPage: false (viewport only)
// or splitting into paginated captures.
