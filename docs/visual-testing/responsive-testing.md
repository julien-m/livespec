# Responsive Viewport Testing Guide

Test UI across mobile, tablet, and desktop breakpoints with separate baselines per viewport.

## The 3-viewport matrix (AC-012)

| Viewport | Dimensions | Project name |
|----------|-----------|--------------|
| Mobile | 375 × 667 | `mobile-chromium` |
| Tablet | 768 × 1024 | `tablet-chromium` |
| Desktop | 1920 × 1080 | `desktop-chromium` |

All 3 use Chromium for responsive testing. Cross-browser coverage (Firefox, WebKit) is handled in the cross-browser suite at desktop resolution.

## How viewport routing works

`playwright.config.ts` defines the viewport matrix and `snapshotPathTemplate`:

```typescript
snapshotPathTemplate: '{testDir}/{testFileDir}/baselines/{projectName}/{testName}-{arg}{ext}',

projects: [
  { name: 'mobile-chromium',  use: { browserName: 'chromium', viewport: { width: 375, height: 667 } } },
  { name: 'tablet-chromium',  use: { browserName: 'chromium', viewport: { width: 768, height: 1024 } } },
  { name: 'desktop-chromium', use: { browserName: 'chromium', viewport: { width: 1920, height: 1080 } } },
]
```

Each test runs 3 times (once per project). Baselines are stored in separate directories:

```
baselines/
  mobile-chromium/
    button-default.png
    nav-viewport.png
  tablet-chromium/
    button-default.png
    nav-viewport.png
  desktop-chromium/
    button-default.png
    nav-viewport.png
```

## AC-014: Viewport-labeled failures

When a test fails, the CI output identifies which viewport failed:

```
✗  [mobile-chromium] › responsive-viewports.spec.ts › button renders correctly at current viewport
     Screenshot comparison failed with 12% difference (baseline: mobile-chromium/button-default.png)
```

## AC-015 / FR-013: Skipping inapplicable viewports

Some components only exist on certain viewports (e.g., a desktop sidebar that collapses to a bottom nav on mobile). Use the `APPLICABLE_VIEWPORTS` map in the test file:

```typescript
const APPLICABLE_VIEWPORTS: Record<string, boolean> = {
  'mobile-chromium': false,  // Skip — sidebar doesn't exist on mobile
  'tablet-chromium': true,
  'desktop-chromium': true,
  'desktop-firefox': false,
  'desktop-webkit': false,
};

test.beforeEach(({}, testInfo) => {
  if (!APPLICABLE_VIEWPORTS[testInfo.project.name]) {
    test.skip(true, `Not applicable for ${testInfo.project.name}`);
  }
});
```

## AC-016 / FR-014: Updating all viewport baselines

Update baselines for all 3 viewports in a single command:

```bash
npx playwright test tests/visual/responsive-viewports.spec.ts --update-snapshots
```

The 3 Chromium projects run in parallel (based on `workers` setting), updating `mobile-chromium/`, `tablet-chromium/`, and `desktop-chromium/` baselines simultaneously.

## EC-006: Pinning viewport dimensions

Viewport dimensions are pinned exactly in `playwright.config.ts`. This prevents the common issue of tests passing locally (at a slightly different viewport) and failing in CI.

Never use `viewport: null` (inherits the OS viewport size) in visual tests. Always use explicit pixel dimensions.

## Common responsive bugs caught

| Bug | How visual test catches it |
|-----|---------------------------|
| Button text overflows on mobile | mobile-chromium test fails, desktop passes |
| Navigation doesn't collapse to hamburger | mobile nav screenshot shows desktop layout |
| Sidebar and main content overlap at tablet | tablet baseline shows overlapping elements |
| Font too large on small screen | mobile screenshot shows text overflow |
| Image not constrained to viewport width | mobile screenshot shows horizontal scroll |
| Touch targets too small on mobile | mobile screenshot shows truncated buttons |

## Related

- **Read** [`cross-browser-testing.md`](cross-browser-testing.md) — Firefox and WebKit coverage
- **Read** [`fullpage-testing.md`](fullpage-testing.md) — full-page layout capture
- **Read** [`troubleshooting.md`](troubleshooting.md) — EC-006 viewport pinning issues
