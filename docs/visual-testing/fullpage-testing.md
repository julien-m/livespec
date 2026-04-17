# Full-Page Layout Testing Guide

Validate full-page layout including z-index, content alignment, and scroll behavior.

## When to use full-page tests

| Scenario | Use Component Test | Use Full-Page Test |
|----------|-------------------|-------------------|
| Button style, padding, text | ✅ | |
| Modal renders correctly in isolation | ✅ | |
| Modal doesn't render under header (z-index) | | ✅ |
| Sidebar width and content alignment | | ✅ |
| Sticky header during scroll | | ✅ |
| Footer alignment at bottom | | ✅ |
| Scroll locked when modal open | | ✅ |

> A component can look perfect in isolation but fail in full-page context. A modal with correct z-index in unit tests can still render under a fixed header when the full page is assembled.

## AC-007: Capturing the full viewport

Use `page` (not a locator) for full-page screenshots:

```typescript
// Viewport only (default)
await expect(page).toHaveScreenshot('layout.png', { fullPage: false });

// Entire scrollable page (FR-007)
await expect(page).toHaveScreenshot('layout-full.png', { fullPage: true });
```

## AC-009: Detecting z-index regressions

Full-page tests catch z-index bugs that component tests miss:

```typescript
// Open modal and capture full page — modal should overlay header
await page.locator('[data-testid="open-modal"]').click();
await page.waitForSelector('[data-testid="modal"]', { state: 'visible' });
await expect(page).toHaveScreenshot('dashboard-modal-open.png', { fullPage: true });
```

If the modal renders behind the header, the pixel diff will show the modal content obscured. The diff image highlights the overlapping region.

## AC-010: Detecting layout shifts

Capture the sidebar + content area to detect width/alignment changes:

```typescript
await expect(page).toHaveScreenshot('dashboard-layout.png', { fullPage: false });
```

A CSS change to sidebar width (e.g., 240px → 220px) without updating content offset creates a visible gap in the diff.

## AC-011: Scroll behavior validation

Test sticky headers and scroll-locked modals:

```typescript
// Sticky header
await page.evaluate(() => window.scrollTo(0, 500));
await expect(page).toHaveScreenshot('header-at-scroll-500.png');

// Scroll lock (modal open should prevent scrolling)
await page.locator('[data-testid="open-modal"]').click();
await page.evaluate(() => window.scrollTo(0, 500));
await expect(page).toHaveScreenshot('modal-scroll-locked.png');
```

## FR-008: Baseline directory structure

```
baselines/fullpage/
  <feature>/
    <screen>-<state>.png
```

Example:
```
baselines/fullpage/
  dashboard/
    dashboard-layout.png
    dashboard-modal-open.png
    sticky-header-scrolled.png
```

## EC-003: Masking dynamic content

Pages with timestamps, random IDs, or live data need masking to avoid flaky tests:

```typescript
await expect(page).toHaveScreenshot('dashboard.png', {
  mask: [
    page.locator('[data-testid="timestamp"]'),
    page.locator('[data-testid="random-token"]'),
    page.locator('[data-testid="user-avatar"]'),
  ],
});
```

## EC-012: Handling very long pages

Full-page screenshots of extremely long pages can be large:

- Pages under 50 viewport-heights: use `fullPage: true` safely
- Very long pages (feeds, audit logs): use `fullPage: false` (viewport snapshot) or test specific scroll positions
- If the screenshot file exceeds 5MB, consider paginated captures with explicit `page.evaluate(() => window.scrollTo(0, Y))` between snapshots

## Related

- **Read** [`responsive-testing.md`](responsive-testing.md) — test full-page layouts across viewports
- **Read** [`troubleshooting.md`](troubleshooting.md) — EC-003, EC-009, EC-012 fixes
