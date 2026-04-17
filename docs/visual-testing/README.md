# Visual Testing Documentation

Comprehensive visual testing framework for LiveSpec-powered projects. Covers mockup fidelity, full-page layout, responsive viewports, cross-browser rendering, animation keyframes, CI/CD integration, and migration tooling.

## Prerequisites

- Node.js 18+
- Playwright 1.40+ (`npm install @playwright/test`)
- Figma account (for mockup export workflow)
- GitHub Actions (for CI/CD with PR diff comments)

## Quick-start: adding visual tests to your project

**Step 1 — Run the migration scan**

```bash
node scripts/migrate-visual-tests.js --scan
```

**Step 2 — Generate test scaffolding**

```bash
node scripts/migrate-visual-tests.js --generate
```

**Step 3 — Add a mockup baseline**

Export your component from Figma at 2x → save to `baselines/mockups/<feature>/component.png` → run:

```bash
node scripts/validate-mockup-metadata.js baselines/mockups/ --fix
```

Then fill in the stub `.meta.yml` values.

## Guides

| Guide | Description |
|-------|-------------|
| **Read** [`mockup-workflow.md`](mockup-workflow.md) | Designer workflow: Figma export → baseline → code comparison → approval |
| **Read** [`fullpage-testing.md`](fullpage-testing.md) | Full-page layout capture: z-index bugs, layout shifts, scroll behavior |
| **Read** [`responsive-testing.md`](responsive-testing.md) | 3-viewport matrix: mobile (375×667), tablet (768×1024), desktop (1920×1080) |
| **Read** [`cross-browser-testing.md`](cross-browser-testing.md) | 3-browser matrix: Chromium, Firefox, WebKit — rendering parity testing |
| **Read** [`animation-testing.md`](animation-testing.md) | Keyframe capture: 0%, 50%, 100% — detecting missing/janky animations |
| **Read** [`migration-guide.md`](migration-guide.md) | Batch migration: scaffold visual tests for 50+ existing features |
| **Read** [`troubleshooting.md`](troubleshooting.md) | EC-001 through EC-015: all edge cases and their fixes |

## Test templates

| Template | Purpose |
|----------|---------|
| `tests/visual/mockup-comparison.spec.ts` | Compare code rendering against Figma mockup baselines |
| `tests/visual/fullpage-layout.spec.ts` | Full-page layout validation with z-index and scroll checks |
| `tests/visual/responsive-viewports.spec.ts` | Responsive testing across 3 viewports |
| `tests/visual/animations.spec.ts` | Animation keyframe testing (0%, 50%, 100%) |

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/validate-mockup-metadata.js` | Validate `.meta.yml` files for all mockup baselines |
| `scripts/capture-keyframes.ts` | Capture animation keyframes to establish baselines |
| `scripts/migrate-visual-tests.js` | Batch migration: scan and generate visual tests |
| `scripts/visual-diff-pr-comment.js` | Post visual diff PR comment from CI |

## CI/CD

Visual tests run automatically on pull requests via `.github/workflows/visual-tests.yml`:

- **5 project combinations** (EC-013): mobile-chromium, tablet-chromium, desktop-chromium, desktop-firefox, desktop-webkit
- **Diff artifacts** uploaded on failure (30-day retention)
- **PR comments** posted with diff images and designer review instructions

To expand to all 9 combinations (3 viewports × 3 browsers), add the remaining 4 projects to the matrix in `visual-tests.yml`.

## Baseline structure

```
baselines/
  mockups/<feature>/      # Designer-exported Figma PNGs
  fullpage/<feature>/     # Full-page layout screenshots
  mobile-chromium/        # Per-project (viewport+browser) snapshots
  tablet-chromium/
  desktop-chromium/
  desktop-firefox/
  desktop-webkit/
  animations/<feature>/   # Animation keyframe baselines
```

## Spec reference

This documentation implements Feature 010 — Visual Testing Complete. See `.specs/features/010-visual-testing-complete/spec.md` for the full specification.
