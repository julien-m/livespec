import { test, expect } from '@playwright/test';

// @spec FR-019: Animation tests capture keyframes at 0%, 50%, 100% — spec.md#fr-019
// @spec FR-020: Keyframe baselines in baselines/animations/[feature]/[component]-[percent].png — spec.md#fr-020
// @spec FR-021: Use page.waitForTimeout(ms) to pause at keyframe intervals — spec.md#fr-021
// @spec FR-022: Animation test metadata: duration, easing, keyframe percentages — spec.md#fr-022

// Animation metadata (FR-022)
const ANIMATION = {
  component: 'modal',
  feature: 'dashboard',
  trigger: '[data-testid="open-modal"]',
  target: '[data-testid="modal"]',
  durationMs: 300,
  easing: 'ease-in-out',
  keyframes: [0, 0.5, 1.0], // 0%, 50%, 100%
};

test.describe(`Animation: ${ANIMATION.feature}/${ANIMATION.component}`, () => {
  // @spec AC-022: Capture at 0%, 50%, 100% intervals — spec.md#ac-022
  // EC-004: Higher tolerance for animation tests — timing variance ±10-20ms
  const ANIM_TOLERANCE = 0.08; // 8% maxDiffPixelRatio

  // @spec AC-022: Keyframe 0% — initial state before animation — spec.md#ac-022
  test('keyframe 0% — initial state (before animation)', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Capture before animation starts — component in resting state
    // @spec FR-020: Baseline path: baselines/animations/dashboard/modal-kf-0pct.png
    await expect(page.locator(ANIMATION.target)).toHaveScreenshot(
      `${ANIMATION.component}-kf-0pct.png`,
      {
        // @spec FR-019: animations: 'allow' for animation tests (unlike static tests) — spec.md#fr-019
        animations: 'allow',
        maxDiffPixelRatio: ANIM_TOLERANCE,
      }
    );
  });

  // @spec AC-024: Mid-transition detects jank (opacity flicker, position jump) — spec.md#ac-024
  test('keyframe 50% — mid-transition', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    await page.locator(ANIMATION.trigger).click();

    // @spec FR-021: waitForTimeout at 50% keyframe interval — spec.md#fr-021
    await page.waitForTimeout(ANIMATION.durationMs * 0.5);

    // @spec AC-023: Baseline in baselines/animations/ — spec.md#ac-023
    await expect(page.locator(ANIMATION.target)).toHaveScreenshot(
      `${ANIMATION.component}-kf-50pct.png`,
      {
        animations: 'allow',
        maxDiffPixelRatio: ANIM_TOLERANCE,
      }
    );
  });

  // @spec AC-025: Missing animation detection (instant state change) — spec.md#ac-025
  // @spec AC-026: Animation incomplete at 100% keyframe — spec.md#ac-026
  test('keyframe 100% — final state (animation complete)', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    await page.locator(ANIMATION.trigger).click();

    // @spec FR-021: waitForTimeout at 100% keyframe — spec.md#fr-021
    await page.waitForTimeout(ANIMATION.durationMs);

    // @spec AC-026: Fails if animation not complete at 100% keyframe — spec.md#ac-026
    await expect(page.locator(ANIMATION.target)).toHaveScreenshot(
      `${ANIMATION.component}-kf-100pct.png`,
      {
        animations: 'allow',
        maxDiffPixelRatio: ANIM_TOLERANCE,
      }
    );
  });
});

// Baseline paths (FR-020):
//   baselines/animations/dashboard/modal-kf-0pct.png
//   baselines/animations/dashboard/modal-kf-50pct.png
//   baselines/animations/dashboard/modal-kf-100pct.png
//
// EC-004: Animation timing variance ±10-20ms across test runs.
//   Increase ANIM_TOLERANCE to 0.10 if tests are flaky due to timing.
//   Use fixed waitForTimeout() values — do not rely on CSS transition events.
//
// To detect missing animations (AC-025):
//   If kf-50pct is identical to kf-0pct or kf-100pct, the animation was skipped.
//   This will fail the test because the 50% keyframe won't match the baseline
//   (which was captured during the actual mid-transition state).
