import { test, expect } from '@playwright/test';

// Pre-existing visual test — must not be overwritten by migration
test.describe('Visual tests: Settings Modal', () => {
  test('renders correctly', async ({ page }) => {
    await page.goto('/settings');
    await expect(page.locator('[data-testid="settings-modal"]')).toBeVisible();
  });
});
