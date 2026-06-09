<!-- LiveSpec traceability anchors -->
<!-- @spec(AC-024) -->
<!-- @spec(AC-025) -->

# Animation Testing Guide

Validate transitions, keyframes, and animation correctness using timed screenshot captures.

## Why animations need special treatment

Static visual tests use `animations: 'disabled'` to prevent flaky snapshots. Animation tests intentionally enable animations to validate:

- The animation plays (not missing/instant)
- Intermediate states are smooth (no jank)
- The final state is correct
- Duration matches the design spec

## AC-022: Keyframe capture strategy

Capture 3 keyframes per animation: 0% (initial), 50% (mid-transition), 100% (final).

```typescript
const ANIMATION = {
  durationMs: 300,   // FR-022: animation duration in metadata
  easing: 'ease-in-out',
  keyframes: [0, 0.5, 1.0],
};

// Keyframe 0% — state before animation
await expect(element).toHaveScreenshot('modal-kf-0pct.png', { animations: 'allow' });

// Keyframe 50% — mid-transition
await page.locator('[data-testid="open-modal"]').click();
await page.waitForTimeout(ANIMATION.durationMs * 0.5); // FR-021
await expect(element).toHaveScreenshot('modal-kf-50pct.png', { animations: 'allow' });

// Keyframe 100% — final state
await page.waitForTimeout(ANIMATION.durationMs); // FR-021
await expect(element).toHaveScreenshot('modal-kf-100pct.png', { animations: 'allow' });
```

## FR-021: Using `waitForTimeout` for keyframe timing

Animation tests use `page.waitForTimeout(ms)` to pause at exact intervals. This is intentional — it provides deterministic keyframe capture:

```typescript
// 50% keyframe: wait half the animation duration
await page.waitForTimeout(300 * 0.5); // 150ms

// 100% keyframe: wait the full duration
await page.waitForTimeout(300); // 300ms
```

> Note: `waitForTimeout` is discouraged in most Playwright tests (prefer network idle or selector waits), but it is the correct approach for animation keyframe testing where you need time-based snapshots.

## AC-023: Baseline directory structure (FR-020)

```
baselines/
  animations/
    <feature>/
      <component>-kf-0pct.png
      <component>-kf-50pct.png
      <component>-kf-100pct.png
```

Example: `baselines/animations/dashboard/modal-kf-50pct.png`

## EC-004: Tolerance for animation tests

Animation timing can vary ±10-20ms across test runs and machines. Use higher tolerance:

```typescript
const ANIM_TOLERANCE = 0.08; // 8% maxDiffPixelRatio (vs 2% for static tests)
```

If tests are still flaky, increase to 0.10 (10%). The tolerance accounts for:
- Sub-frame timing differences
- GPU rendering variance
- CI machine speed differences

## AC-024: Detecting janky transitions

A jank in animation (opacity flicker, position jump) shows as an unexpected pixel diff at the 50% keyframe:

```
✗  50% keyframe test fails — unexpected diff at opacity value
   Expected: smooth 50% opacity transition
   Actual: opacity jumped to 0 then back (flicker)
```

## AC-025: Detecting missing animations

If a CSS transition is removed, the component transitions instantly. The 50% keyframe will be identical to the 100% keyframe (already at final state). Since the baseline was captured during the actual mid-transition, the test fails:

```
✗  50% keyframe test fails — component already in final state
   Expected: modal at 50% transition position
   Actual: modal fully open (transition removed)
```

## AC-026: Animation duration validation

The 100% keyframe test validates the animation is complete at `durationMs`. If the animation takes longer than specified, the 100% capture will show an incomplete state:

```
✗  100% keyframe test fails — animation not complete
   Expected: modal fully open at 300ms
   Actual: modal at ~80% position at 300ms (animation takes 400ms)
```

## Using `capture-keyframes.ts` to establish baselines

For new animations, use the keyframe capture script to establish initial baselines:

```bash
# Capture 3 keyframes for modal animation
npx ts-node scripts/capture-keyframes.ts \
  --component modal \
  --feature dashboard \
  --trigger '[data-testid="open-modal"]' \
  --duration 300 \
  --url http://localhost:3000/dashboard
```

This creates the 3 baseline PNGs and a YAML metadata file.

## Related

- **Read** [`troubleshooting.md`](troubleshooting.md) — EC-004 timing variance, EC-011 keyframe timing
