import { test, expect } from '@playwright/test';
import { existsSync } from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// @spec FR-001: Prioritize mockup baselines — .specs/features/010-visual-testing-complete/spec.md#fr-001
// @spec FR-003: Configurable tolerance — .specs/features/010-visual-testing-complete/spec.md#fr-003
// @spec FR-004: Skip with WARNING when mockup missing — .specs/features/010-visual-testing-complete/spec.md#fr-004

// Configure per component — replace with your component details
const COMPONENT = 'signup-form';
const MOCKUP_DIR = path.join(__dirname, '../../baselines/mockups');

// @spec AC-004: Default 2% maxDiffPixelRatio (configurable per component) — spec.md#ac-004
const TOLERANCE = 0.02;

test.describe(`Mockup comparison: ${COMPONENT}`, () => {
  test('code matches designer mockup baseline', async ({ page }) => {
    // @spec AC-001: Compare against designer mockup in baselines/mockups/ — spec.md#ac-001
    const mockupPath = path.join(MOCKUP_DIR, `${COMPONENT}.png`);

    // @spec AC-005: Skip with WARNING when mockup baseline missing — spec.md#ac-005
    // @spec FR-004: Test skips and outputs TODO when no mockup exists — spec.md#fr-004
    if (!existsSync(mockupPath)) {
      test.skip(true, `TODO: No mockup baseline at ${mockupPath}. Designer must export from Figma and place at baselines/mockups/${COMPONENT}.png`);
      return;
    }

    // Navigate to component and wait for full load (EC-009: wait for networkidle)
    await page.goto(`/components/${COMPONENT}`);
    await page.waitForLoadState('networkidle');

    // @spec AC-003: Compare code screenshot to mockup baseline (not code-to-code) — spec.md#ac-003
    // @spec FR-001: Mockup baseline takes priority over code-generated baseline — spec.md#fr-001
    await expect(page.locator('[data-testid="component-root"]')).toHaveScreenshot(
      path.basename(mockupPath),
      {
        maxDiffPixelRatio: TOLERANCE, // @spec FR-003
        animations: 'disabled',
        // EC-010: tolerance accounts for anti-aliasing in drop shadows
        // EC-001: set deviceScaleFactor in playwright.config.ts if mockup is 2x resolution
      }
    );
  });

  // @spec AC-006: --approve-visual-diff updates mockup baseline + records approval — spec.md#ac-006
  // To approve a visual diff:
  //   npx playwright test --update-snapshots tests/visual/mockup-comparison.spec.ts
  // Then update baselines/mockups/<component>.meta.yml:
  //   approved_by: <designer_name>
  //   approved_date: <ISO 8601 date>
  //   diff_percentage: <percentage at approval time>
});

// Template: to add more components, copy the test.describe block above
// and change COMPONENT, MOCKUP_DIR, TOLERANCE as needed.
//
// Example .meta.yml for baselines/mockups/<component>.png:
// ---
// type: mockup
// figma_url: https://figma.com/file/...
// artboard_name: Signup Form
// component: signup-form
// exported_date: 2026-04-17
// designer_name: Jane Designer
// resolution: 2x
// tolerance: 0.02
// last_updated: 2026-04-17
// invalidate_on:
//   - figma_mockup_change
//   - designer_approval_revoked
