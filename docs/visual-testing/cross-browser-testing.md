<!-- LiveSpec traceability anchors -->
<!-- @spec(AC-019) -->
<!-- @spec(AC-020) -->
<!-- @spec(AC-021) -->
<!-- @spec(FR-016) -->
<!-- @spec(FR-018) -->

# Cross-Browser Testing Guide

Detect rendering differences across Chromium, Firefox, and WebKit (Safari) browser engines.

## The 3-engine matrix (AC-017)

| Browser | Engine | Project name | Platform equivalent |
|---------|--------|--------------|---------------------|
| Chromium | Blink | `desktop-chromium` | Chrome, Edge |
| Firefox | Gecko | `desktop-firefox` | Firefox |
| WebKit | WebKit | `desktop-webkit` | Safari (macOS/iOS) |

All 3 run at desktop resolution (1920×1080). Responsive breakpoint coverage is handled by the 3-viewport Chromium suite.

## How browser-specific baselines work (AC-018, FR-016)

`snapshotPathTemplate` in `playwright.config.ts` routes baselines to per-project directories:

```
baselines/
  desktop-chromium/
    button-hover.png
  desktop-firefox/
    button-hover.png    ← may differ from Chromium
  desktop-webkit/
    button-hover.png    ← may differ from both
```

Each browser has its own baseline. A visual difference between browsers is expected (they render fonts, borders, and shadows differently) — the test catches **unexpected regressions within a browser**, not cross-browser differences.

## Common rendering differences (AC-019)

| Property | Chromium | Firefox | WebKit |
|----------|----------|---------|--------|
| `font-weight: 500` | Medium weight | Medium weight | Often renders as 400 |
| `border-radius` | Identical | Nearly identical | Slight subpixel differences |
| `box-shadow` | Identical | Very close | Slight anti-aliasing variance |
| Scrollbar | Styled via CSS | Styled via CSS | Cannot be styled (system scrollbar) |
| `outline` on focus | Blue | Dotted | Blue |
| Form controls | OS-dependent | OS-dependent | Very different from others |
| Subpixel rendering | Varies | Varies | ClearType-style |

> **Example:** A button with `font-weight: 500` renders at visual weight 400 in WebKit/Safari. If the designer intends medium weight, the WebKit baseline captures the Safari rendering as the correct target — and tests catch regressions within WebKit.

## AC-021 / FR-018: Skipping browser-specific tests

For browser-specific features (e.g., a Chromium-only API or a WebKit-specific CSS workaround), skip inapplicable browsers in the test file:

```typescript
const APPLICABLE_BROWSERS: Record<string, boolean> = {
  'desktop-chromium': true,
  'desktop-firefox': true,
  'desktop-webkit': false, // CSS Houdini not supported in WebKit
};

test.beforeEach(({}, testInfo) => {
  if (!APPLICABLE_BROWSERS[testInfo.project.name]) {
    test.skip(true, `Not applicable for ${testInfo.project.name}`);
  }
});
```

Alternatively, filter by `browserName` in the test:

```typescript
test('custom scrollbar styling', async ({ page, browserName }) => {
  test.skip(browserName === 'webkit', 'WebKit does not support scrollbar styling');
  // ...
});
```

## AC-020: Browser-labeled failure reporting

When a cross-browser test fails, the project name in the output identifies which browser:

```
✗  [desktop-webkit] › cross-browser.spec.ts › button renders at all browsers
     Screenshot comparison failed (baseline: desktop-webkit/button-default.png)
```

## EC-005 / EC-015: Font availability in CI

A common cause of CI failures is missing system fonts. Always install browsers with dependencies:

```yaml
# .github/workflows/visual-tests.yml
- run: npx playwright install --with-deps firefox
- run: npx playwright install --with-deps webkit
- run: npx playwright install --with-deps chromium
```

For consistent font rendering across environments, prefer web fonts (loaded via `@font-face` or CDN) over system fonts. Web fonts are downloaded and rendered identically across OS and CI.

## Establishing browser baselines

On first run, Playwright creates baselines for each browser project:

```bash
# Create all browser baselines in one pass
npx playwright test tests/visual/ --update-snapshots
```

This creates `baselines/desktop-chromium/`, `baselines/desktop-firefox/`, and `baselines/desktop-webkit/` simultaneously.

## Related

- **Read** [`responsive-testing.md`](responsive-testing.md) — viewport matrix (mobile/tablet/desktop)
- **Read** [`troubleshooting.md`](troubleshooting.md) — EC-005, EC-015 font issues in CI
