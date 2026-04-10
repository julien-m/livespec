# Visual Helper Scaffold — Playwright + Pixelmatch Reference Implementation

**Status:** Reference template for visual regression testing  
**Last Updated:** 2026-04-10  
**Scope:** TypeScript/Node.js, Playwright 1.40+, pixelmatch 5.x

---

## Overview

This document provides a complete reference implementation scaffold for integrating visual regression testing into a Playwright test suite using pixelmatch for image comparison. It serves as both documentation and a copy-paste-ready template.

**Key components:**
1. **VisualHelper class** — Unified API for capture, comparison, and delta generation
2. **Baseline management** — Store, retrieve, update visual baselines
3. **Diff reporting** — Generate visual deltas with annotation overlays
4. **CI/CD integration** — Headless mode, artifact capture, report generation

---

## Core API Reference

### VisualHelper Class

```typescript
/**
 * Unified visual regression testing helper
 * 
 * Usage:
 *   const helper = new VisualHelper(page, { baselineDir: './baselines' });
 *   await helper.snapshot('login-form', { threshold: 0.01 });
 */
class VisualHelper {
  constructor(page: Page, options: VisualHelperOptions);
  
  /**
   * Capture and compare against baseline
   * 
   * @param name Snapshot identifier (auto-creates path: `baselineDir/{name}.png`)
   * @param options Comparison options (threshold, mask regions, element selector)
   * @returns { passed: boolean, diff?: DiffReport }
   */
  async snapshot(
    name: string,
    options?: SnapshotOptions
  ): Promise<SnapshotResult>;

  /**
   * Capture without comparison (for baseline creation)
   * 
   * @param name Snapshot identifier
   * @returns { path: string, size: { width, height } }
   */
  async capture(name: string): Promise<CaptureResult>;

  /**
   * Update existing baseline with current screenshot
   * 
   * @param name Snapshot identifier
   * @param force Skip confirmation (default: false for interactive mode)
   */
  async updateBaseline(name: string, force?: boolean): Promise<void>;

  /**
   * Compare two arbitrary images
   * 
   * @param actual Path to actual screenshot
   * @param baseline Path to baseline screenshot
   * @param options Pixelmatch configuration
   * @returns { matched: boolean, diffPixels: number, report: DiffReport }
   */
  async compareImages(
    actual: string,
    baseline: string,
    options?: CompareOptions
  ): Promise<ComparisonResult>;

  /**
   * List all registered baselines
   * 
   * @returns Array of baseline metadata
   */
  getBaselines(): BaselineMetadata[];

  /**
   * Clear diff artifacts (optional cleanup)
   */
  async cleanup(): Promise<void>;
}
```

---

## Initialization & Configuration

### Basic Setup

```typescript
import { test, expect } from '@playwright/test';
import { VisualHelper } from './visual-helper';

test.describe('Visual Regression', () => {
  let visual: VisualHelper;

  test.beforeEach(async ({ page }) => {
    visual = new VisualHelper(page, {
      baselineDir: './test/visual/baselines',
      diffDir: './test/visual/diffs',
      threshold: 0.01,  // 1% pixel difference tolerance
      updateBaselines: process.env.UPDATE_BASELINES === 'true',
    });
  });

  test('login form renders correctly', async () => {
    await page.goto('/login');
    const result = await visual.snapshot('login-form');
    expect(result.passed).toBe(true);
  });
});
```

### VisualHelperOptions Interface

```typescript
interface VisualHelperOptions {
  /** Directory for baseline images (created if missing) */
  baselineDir: string;
  
  /** Directory for diff/delta artifacts */
  diffDir?: string;  // default: baselineDir + '/diffs'
  
  /** Pixel-level difference threshold (0.0 - 1.0) */
  threshold?: number;  // default: 0.01 (1%)
  
  /** Auto-update baselines on mismatch */
  updateBaselines?: boolean;  // default: false
  
  /** Include metadata in baseline (timestamp, URL, browser) */
  metadata?: boolean;  // default: true
  
  /** Pixelmatch color tolerance (0-32) */
  colorFuzz?: number;  // default: 0.1
  
  /** Number of parallel diff operations */
  concurrency?: number;  // default: 4
}
```

---

## Snapshot Options & Results

### SnapshotOptions Interface

```typescript
interface SnapshotOptions {
  /** Pixel-level threshold for this snapshot (overrides default) */
  threshold?: number;
  
  /** Element selector to compare (e.g., '.modal-content') */
  selector?: string;
  
  /** Full page (true) or viewport (false, default) */
  fullPage?: boolean;
  
  /** Rectangular regions to ignore/mask */
  maskRegions?: Array<{ x: number; y: number; width: number; height: number }>;
  
  /** Custom pixelmatch options */
  pixelmatchOptions?: {
    threshold?: number;    // per-pixel threshold
    includeAA?: boolean;   // anti-alias matching
  };
  
  /** Wait for element/network before capture */
  waitFor?: string | (() => Promise<void>);
  
  /** Save diff even if passed (for visual review) */
  saveDiffAlways?: boolean;
  
  /** Filename suffix (auto-appends: `{name}-{suffix}.png`) */
  suffix?: string;
}
```

### SnapshotResult Interface

```typescript
interface SnapshotResult {
  /** Comparison passed within threshold */
  passed: boolean;
  
  /** Matched pixels (0-100%) */
  match: number;
  
  /** Total differing pixels */
  diffPixels: number;
  
  /** Total compared pixels */
  totalPixels: number;
  
  /** Diff report if failed/generated */
  diff?: DiffReport;
  
  /** Baseline path */
  baselinePath: string;
  
  /** Actual screenshot path */
  actualPath: string;
  
  /** Benchmark (milliseconds) */
  duration: number;
}
```

### DiffReport Interface

```typescript
interface DiffReport {
  /** Path to visual diff image (base + annotated regions) */
  diffImagePath: string;
  
  /** Path to pixel-level diff mask */
  diffMaskPath: string;
  
  /** Bounding boxes of changed regions */
  changedRegions: Array<{
    x: number;
    y: number;
    width: number;
    height: number;
    pixelCount: number;
  }>;
  
  /** Metadata for context */
  metadata: {
    timestamp: string;
    browser: string;
    viewport: { width: number; height: number };
    url: string;
    threshold: number;
  };
}
```

---

## Common Usage Patterns

### Pattern 1: Basic Snapshot with Defaults

```typescript
test('modal displays with correct styling', async ({ page }) => {
  const visual = new VisualHelper(page);
  
  await page.click('button:has-text("Open Modal")');
  await page.waitForSelector('.modal-overlay');
  
  const result = await visual.snapshot('modal-open');
  expect(result.passed).toBe(true);
});
```

### Pattern 2: Element-Only Comparison

```typescript
test('button states render correctly', async ({ page }) => {
  const visual = new VisualHelper(page);
  
  await page.goto('/components/button');
  
  // Compare only the button component
  const result = await visual.snapshot('button-primary', {
    selector: 'button.btn-primary',
    threshold: 0.005,  // 0.5% tolerance
  });
  
  expect(result.passed).toBe(true);
});
```

### Pattern 3: Masking Dynamic Content

```typescript
test('form with timestamp renders correctly', async ({ page }) => {
  const visual = new VisualHelper(page);
  
  await page.goto('/form');
  
  // Mask the timestamp region (coordinates in page viewport)
  const result = await visual.snapshot('form-default', {
    maskRegions: [
      { x: 100, y: 250, width: 200, height: 30 }  // timestamp location
    ],
    threshold: 0.01,
  });
  
  expect(result.passed).toBe(true);
});
```

### Pattern 4: Full-Page Comparison

```typescript
test('landing page layout matches design', async ({ page }) => {
  const visual = new VisualHelper(page);
  
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  
  const result = await visual.snapshot('landing-page', {
    fullPage: true,
    threshold: 0.02,  // 2% for full page (more forgiving)
  });
  
  expect(result.passed).toBe(true);
});
```

### Pattern 5: Multi-State Comparison

```typescript
test('button states', async ({ page }) => {
  const visual = new VisualHelper(page);
  
  // Default state
  await visual.snapshot('button-default', { selector: 'button#submit' });
  
  // Hover state
  await page.hover('button#submit');
  await visual.snapshot('button-hover', { selector: 'button#submit' });
  
  // Disabled state
  await page.addInitScript(() => {
    document.querySelector('button#submit')?.setAttribute('disabled', '');
  });
  await visual.snapshot('button-disabled', { selector: 'button#submit' });
});
```

### Pattern 6: Conditional Update (Debug Mode)

```typescript
test('responsive layout on tablet', async ({ page }) => {
  const visual = new VisualHelper(page, {
    updateBaselines: process.env.UPDATE_BASELINES === 'true',
  });
  
  await page.setViewportSize({ width: 768, height: 1024 });
  await page.goto('/dashboard');
  
  const result = await visual.snapshot('dashboard-tablet');
  
  if (!result.passed) {
    console.error('Diff:', result.diff?.diffImagePath);
    // In UPDATE_BASELINES mode, next run updates automatically
  }
});
```

---

## Baseline Management

### Creating Initial Baselines

```typescript
// Command: npm run test:visual -- --update-baselines
test.beforeEach(async ({ page }) => {
  const visual = new VisualHelper(page, {
    baselineDir: './test/visual/baselines',
    updateBaselines: process.env.UPDATE_BASELINES === 'true',
  });
  // First run: captures and stores baselines
  // Second run: compares against stored baselines
});
```

### Baseline Directory Structure

```
test/visual/
├── baselines/
│   ├── login-form.png
│   ├── modal-open.png
│   ├── button-primary.png
│   └── button-states/
│       ├── default.png
│       ├── hover.png
│       └── disabled.png
├── diffs/
│   ├── modal-open-diff.png      # Annotated overlay
│   ├── modal-open-mask.png      # Pixel-level diff
│   └── modal-open.metadata.json  # Context metadata
└── .gitignore
    diffs/
    *.tmp.png
```

### Programmatic Baseline Update

```typescript
test.only('update login form baseline', async ({ page }) => {
  const visual = new VisualHelper(page, {
    baselineDir: './test/visual/baselines',
  });
  
  await page.goto('/login');
  
  // Capture new baseline and store it
  await visual.updateBaseline('login-form', { force: true });
  
  console.log('Baseline updated: test/visual/baselines/login-form.png');
});
```

### Listing Baselines

```typescript
test('verify all baselines exist', async ({ page }) => {
  const visual = new VisualHelper(page);
  const baselines = visual.getBaselines();
  
  console.table(baselines);
  // Output:
  // ┌─────────────┬─────────┬────────────┐
  // │ name        │ size    │ updated    │
  // ├─────────────┼─────────┼────────────┤
  // │ login-form  │ 245 KB  │ 2 hours    │
  // │ modal-open  │ 189 KB  │ 3 days     │
  // └─────────────┴─────────┴────────────┘
});
```

---

## Diff Reporting & Artifacts

### Generated Artifacts

When a snapshot fails, three artifacts are created:

**1. Actual Screenshot**
```
test/visual/diffs/modal-open-actual.png
```
The captured screenshot at test time.

**2. Diff Overlay**
```
test/visual/diffs/modal-open-diff.png
```
Baseline + annotated red bounding boxes around changed regions.

**3. Diff Mask**
```
test/visual/diffs/modal-open-mask.png
```
Pixel-level diff showing exact pixel differences (white = changed, black = same).

**4. Metadata**
```
test/visual/diffs/modal-open.metadata.json
{
  "name": "modal-open",
  "timestamp": "2026-04-10T14:32:10Z",
  "browser": "chromium",
  "viewport": { "width": 1280, "height": 720 },
  "url": "http://localhost:3000/modals",
  "threshold": 0.01,
  "matched": 0.987,
  "diffPixels": 1425,
  "totalPixels": 921600,
  "changedRegions": [
    { "x": 400, "y": 200, "width": 150, "height": 100, "pixelCount": 850 }
  ]
}
```

### Accessing Diff Report

```typescript
test('inspect diff when failed', async ({ page }) => {
  const visual = new VisualHelper(page);
  const result = await visual.snapshot('modal-open');
  
  if (!result.passed && result.diff) {
    console.log('Diff image:', result.diff.diffImagePath);
    console.log('Changed regions:', result.diff.changedRegions);
    
    // Inspect for debugging
    result.diff.changedRegions.forEach((region) => {
      console.log(
        `Change at (${region.x}, ${region.y}): ${region.width}x${region.height}`
      );
    });
  }
});
```

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/visual-tests.yml
name: Visual Regression Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  visual-tests:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - run: npm ci
      - run: npx playwright install --with-deps
      
      - name: Run visual tests
        run: npm run test:visual
        env:
          CI: true
          PLAYWRIGHT_BROWSERS: chromium
      
      - name: Upload diff artifacts
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: visual-diffs
          path: test/visual/diffs/
          retention-days: 7
      
      - name: Comment PR with results
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const metadata = fs.readdirSync('test/visual/diffs')
              .filter(f => f.endsWith('.metadata.json'))
              .map(f => JSON.parse(fs.readFileSync(`test/visual/diffs/${f}`)))
              .filter(m => !m.matched);
            
            if (metadata.length > 0) {
              github.rest.issues.createComment({
                issue_number: context.issue.number,
                owner: context.repo.owner,
                repo: context.repo.repo,
                body: `## Visual Regression Detected\n\n${
                  metadata.map(m => `- **${m.name}**: ${(m.diffPixels || 0).toLocaleString()} pixels changed`).join('\n')
                }\n\n[View diffs](${process.env.ARTIFACT_URL})`
              });
            }
```

### Environment Variables

```bash
# Development
UPDATE_BASELINES=false
VISUAL_THRESHOLD=0.01
DEBUG_DIFFS=true

# CI/CD
CI=true
PLAYWRIGHT_BROWSERS=chromium
VISUAL_THRESHOLD=0.01
ARTIFACT_RETENTION_DAYS=7
```

---

## Threshold Strategy

### Threshold Selection Guidelines

| Scenario | Threshold | Rationale |
|----------|-----------|-----------|
| **UI components** (button, badge) | `0.005` (0.5%) | Strict: pixel-perfect design |
| **Layouts** (grid, flexbox) | `0.01` (1%) | Moderate: spacing tolerance |
| **Full pages** | `0.02` (2%) | Loose: anti-aliasing, rendering variance |
| **Responsive** | `0.03` (3%) | Very loose: layout reflow differences |
| **Text-heavy** (paragraphs) | `0.015` (1.5%) | Font rasterization variance |

### Adaptive Thresholding

```typescript
function getThresholdForTest(testName: string): number {
  if (testName.includes('button') || testName.includes('badge')) {
    return 0.005;  // Component: strict
  }
  if (testName.includes('full') || testName.includes('page')) {
    return 0.02;   // Full page: loose
  }
  if (testName.includes('responsive') || testName.includes('mobile')) {
    return 0.03;   // Responsive: very loose
  }
  return 0.01;     // Default: moderate
}

test('renders correctly', async ({ page }) => {
  const visual = new VisualHelper(page);
  const threshold = getThresholdForTest(test.info().title);
  
  const result = await visual.snapshot('component', { threshold });
  expect(result.passed).toBe(true);
});
```

---

## Troubleshooting & Common Issues

### Issue 1: Anti-Aliasing Differences Between Runs

**Problem:** Same code produces slightly different anti-aliased text on different machines/OS.

**Solution:** Use pixelmatch's `includeAA` option:

```typescript
const result = await visual.snapshot('text-content', {
  pixelmatchOptions: {
    includeAA: true,  // Allow AA pixel matching
  },
  threshold: 0.015,  // Increase threshold for AA tolerance
});
```

### Issue 2: Dynamic Content (Timestamps, IDs)

**Problem:** Components with dynamic content always differ.

**Solution:** Use `maskRegions` to ignore dynamic areas:

```typescript
const result = await visual.snapshot('notification', {
  maskRegions: [
    { x: 200, y: 50, width: 100, height: 30 },  // Timestamp
    { x: 50, y: 100, width: 50, height: 20 },   // Random ID
  ],
});
```

### Issue 3: Slow Rendering / Layout Thrashing

**Problem:** Snapshot captured before layout stabilized.

**Solution:** Use `waitFor` to ensure stability:

```typescript
const result = await visual.snapshot('dashboard', {
  waitFor: async () => {
    await page.waitForLoadState('networkidle');
    await page.waitForFunction(() => {
      return document.querySelectorAll('[data-loading]').length === 0;
    });
  },
  fullPage: true,
});
```

### Issue 4: Baseline Staleness

**Problem:** Baseline is 6 months old, unknown if still valid.

**Solution:** Track baseline age in metadata, regenerate periodically:

```typescript
const baselines = visual.getBaselines();
const stale = baselines.filter(b => {
  const age = Date.now() - new Date(b.updated).getTime();
  return age > 90 * 24 * 60 * 60 * 1000;  // > 90 days
});

if (stale.length > 0) {
  console.warn('Stale baselines:', stale.map(b => b.name));
}
```

---

## Performance Considerations

### Optimization Techniques

**1. Selective Full-Page Comparisons**
```typescript
// ❌ Slow: full page every time
await visual.snapshot('page', { fullPage: true });

// ✓ Fast: specific sections
await visual.snapshot('page-hero', { selector: '.hero-section' });
await visual.snapshot('page-content', { selector: 'main' });
```

**2. Parallel Execution**
```typescript
test.describe.parallel('Visual Tests', () => {
  test('snapshot 1', async ({ page }) => {
    const visual = new VisualHelper(page);
    await visual.snapshot('test-1');
  });
  
  test('snapshot 2', async ({ page }) => {
    const visual = new VisualHelper(page);
    await visual.snapshot('test-2');
  });
  // Runs in parallel
});
```

**3. Concurrency Control**
```typescript
const visual = new VisualHelper(page, {
  concurrency: 4,  // Max 4 diff operations simultaneously
});
```

### Benchmark Example

```typescript
test('capture performance', async ({ page }) => {
  const visual = new VisualHelper(page);
  
  const start = Date.now();
  const result = await visual.snapshot('large-page', { fullPage: true });
  const duration = Date.now() - start;
  
  console.log(`Snapshot: ${duration}ms, Match: ${result.match.toFixed(2)}%`);
  // Output: Snapshot: 342ms, Match: 99.87%
});
```

---

## Integration with Spec System

### Mapping Visual Tests to Specs

```typescript
/**
 * spec: /features/auth/login
 * scenario: User sees login form
 * acceptance: Form renders with email, password, submit button
 */
test('login form renders with required fields', async ({ page }) => {
  const visual = new VisualHelper(page, {
    baselineDir: './specs/features/auth/login/visuals',
  });
  
  await page.goto('/login');
  
  // Maps to spec: specs/features/auth/login/visuals/form-initial.png
  const result = await visual.snapshot('form-initial');
  expect(result.passed).toBe(true);
});
```

### Baseline Versioning

```
specs/features/auth/login/
├── spec.md
├── visuals/
│   ├── form-initial.png         # v1.0
│   ├── form-initial-v2.png      # v2.0 (new design)
│   └── form-error-state.png
└── tests/
    └── visual.spec.ts
```

---

## Reference: Pixelmatch Configuration

### Full pixelmatch Options

```typescript
interface PixelmatchOptions {
  /** Threshold for per-pixel differences (0-32) */
  threshold?: number;  // default: 0.1
  
  /** Include anti-aliased pixel matching */
  includeAA?: boolean;  // default: false
  
  /** Color component weighting */
  alpha?: number;        // default: 0.1
  aaColor?: [r, g, b];   // default: [255, 0, 0]
  minBrightness?: number; // default: 16
  maxBrightness?: number; // default: 240
}
```

Example:

```typescript
const result = await visual.compareImages(
  './actual.png',
  './baseline.png',
  {
    threshold: 0.1,
    includeAA: true,
    aaColor: [255, 0, 0],  // Red for AA pixels
  }
);
```

---

## Checklist for Implementation

- [ ] VisualHelper class with core methods (snapshot, capture, compareImages)
- [ ] Baseline management (store, retrieve, update)
- [ ] Diff report generation with annotated overlays
- [ ] Pixelmatch integration with configurable options
- [ ] Test fixtures and beforeEach setup
- [ ] CI/CD GitHub Actions workflow
- [ ] .gitignore for baselines and diffs
- [ ] Documentation (README with examples)
- [ ] Performance benchmarks
- [ ] Gotcha guide for common issues

---

## See Also

- **test-protocol.md** — Test discovery and execution rules
- **failure-handling.md** — Handling and reporting visual failures
- **execution-rules.md** — Baseline comparison semantics
- **discovery.md** — Finding tests and organizing visual suites
