# Visual Baselines Protocol

> Universal workflow for screenshot-based visual regression and design fidelity testing.
> Applies to UI features only. Non-UI features skip visual baselines.

---

## Overview

This protocol defines two orthogonal testing responsibilities:

| Testing Goal | Command | Tool | Threshold | Stores |
|---|---|---|---|---|
| **Regression Detection** | `/spec.check` | Playwright native | 2% (configurable) | `.specs/features/NNN/baselines/` |
| **Design Fidelity** | `/spec.test` | pixelmatch | 5-8% (configurable) | `.specs/design/screens/` |

**Regression** answers: "Has this feature changed since we last approved it?"
**Fidelity** answers: "Does this implementation match the design mockup?"

These are independent checks. A feature can regress (change from baseline) while remaining faithful to design, or diverge from design while being stable from its own baseline.

---

## Capture

Visual baselines are captured in two contexts:

### Initial Capture (`/spec.test` Phase 4.5.2)

On first implementation of a UI feature:
1. Run visual tests via resolved test command (e.g., `npx playwright test --grep visual`)
2. Screenshots are saved to `.specs/features/NNN/baselines/`
3. Baselines are committed only after all non-visual tests (Phase 4) pass
4. This prevents bootstrapping a baseline from a broken implementation state

### Subsequent Captures

Once a baseline exists, it is updated only when:
- Design is intentionally approved (update via `/spec.implement --update-baseline`)
- Or manually via `spec.test --update-baseline`

### Storage

Baselines live in `.specs/features/NNN-feature-name/baselines/`:

```
.specs/features/
  001-auth/
    baselines/
      login-default.png       # Default state
      login-loading.png       # Loading state
      login-error.png         # Error state
      archived/
        2026-04-05/
          login-default.png   # Previous version (archived)
```

Archived baselines (in `baselines/archived/`) are ignored by hooks and regression checks.

---

## Comparison

### Regression Detection (Playwright Native)

When `/spec.check` executes Step 8:
1. Run `page.screenshot()` or `locator.screenshot()` to capture current state
2. Compare against baseline pixel-by-pixel via Playwright's snapshot comparison
3. Diff threshold: **2%** (default, configurable per component)
4. Output: ✅ Baseline match OR ❌ Regression (diff + percentage)

Playwright native comparison is built-in and does NOT require additional tools.

### Design Fidelity (pixelmatch)

When `/spec.test` executes Phase 4.5.3:
1. For each newly captured baseline
2. If `.specs/design/screens/[name].png` exists (Pencil export), compare via pixelmatch
3. Diff threshold: **5-8%** (default, configurable per component)
4. Output: ✅ Faithful (<5%) OR 🎨 Diverged (>8%) with percentage

If design mockup is absent, fidelity check skips with warning (non-blocking).

---

## 3-Image Diff Output Format

When a pixelmatch comparison fails, the output is three images in a timestamped directory:

```
test-results/
  visual-diffs/
    [test-name]--[timestamp]/
      baseline.png       # Previously approved image (source of truth)
      diff.png           # Pixelmatch diff with changed pixels in red
      actual.png         # Current screenshot
```

This format gives developers immediate diagnosis:
- Baseline: what was approved before
- Diff: where exactly the pixels changed (red zones)
- Actual: what the code produces now

Developers can:
- Accept the change and update baseline (if intentional)
- Fix the code to match baseline (if unintentional regression)
- Adjust design if mockup expectations were wrong

---

## ignoreRegions API

Visual tests often fail on dynamic content (timestamps, avatars, network-dependent values, animations). The helper exposes a mechanism to exclude zones from comparison:

```typescript
await compareDesign(page, mockupPng, {
  threshold: 0.08,
  ignoreRegions: [
    { x: 0, y: 0, width: 1280, height: 50 },   // header with timestamp
    { x: 100, y: 200, width: 60, height: 60 }  // avatar area
  ]
})
```

Regions are specified as bounding boxes in pixel coordinates. Pixels within ignored regions do not contribute to the mismatch percentage.

---

## Configuration

### Thresholds

Default thresholds:
- Regression: 2% (catches unintentional changes)
- Fidelity: 5-8% (allows browser rendering variance)

Per-component configuration via `Visual Test Mapping` section in `.specs/testing/strategy.md`:

```yaml
Visual Test Mapping:
  button.spec.ts:
    threshold_regression: 0.02
    threshold_design: 0.05
  dashboard.spec.ts:
    threshold_regression: 0.02
    threshold_design: 0.08   # Looser for complex layouts
```

### Timeout & Performance

Pre-commit hook visual test timeout: **60 seconds** (configurable via `LIVESPEC_VISUAL_TIMEOUT`).

If visual tests exceed timeout, hook skips with warning (non-blocking during development).

---

## Baseline Lifecycle

### New Feature (No Baseline)

1. `spec.test` Phase 4.5.2 captures screenshot
2. If Phase 4 (non-visual tests) passed → baseline committed
3. If Phase 4 failed → baseline NOT committed (prevents bad reference)

### Change to Feature

1. Developer modifies code
2. Pre-commit hook runs `compareRegression()` against existing baseline
3. If diff > 2% → commit blocked (regression detected)
4. Developer either reverts change or intentionally updates baseline via `--update-baseline`

### Intentional Design Update

1. Designer approves new mockup
2. `.specs/design/screens/[name].png` is exported from Pencil and committed
3. Developer implements new design
4. `spec.test` Phase 4.5.3 runs `compareDesign()` and reports fidelity
5. If fidelity < 5% → passes, baseline is the new reference
6. If fidelity > 8% → fails, developer adjusts implementation

### Archived Baselines

Old baselines are moved to `baselines/archived/YYYY-MM-DD/` before replacement. They are:
- NOT used by regression checks (only active baselines in `baselines/` are used)
- Preserved for reference and rollback if needed
- Safe to delete after sufficient time has passed

---

## Prerequisite Check

The visual tool availability is resolved **once** during `/spec.plan` discovery and recorded in Resolved Test Commands.

- If Playwright is installed and available → visual tests are enabled
- If Playwright is NOT available → visual tests are skipped with message: "Visual baselines skipped — Playwright not installed"

The exact capture/compare command comes from **Resolved Test Commands** in `plan.md`.

---

## Flakyness Mitigation

Visual tests are deterministic only in controlled environments. Best practices:

- **Fixed viewport size**: `page.setViewportSize({ width: 1280, height: 800 })`
- **Mocked timestamps**: inject `now()` mock for time-dependent content
- **Isolated test data**: use fixtures with known avatars, images, content
- **Single browser**: screenshots always on Chrome headless (not multi-browser)
- **Disabled animations**: CSS `animation: none` in test mode if needed
- **Seeded random**: if randomness is involved, seed it for reproducibility

---

## Edge Cases

| Situation | Behavior |
|---|---|
| Baseline file corrupted or missing | Captured but not compared → warning, no regression check |
| Mockup PNG missing during fidelity check | Check skipped with warning (non-blocking) |
| ignoreRegions overlap or out-of-bounds | Clamped to image bounds, non-blocking |
| Screenshot is 0 bytes | Error, non-blocking during capture, blocking during compare |
| Playwright not installed | Hook/commands skip with warning (except CI mode) |

---

## Stack Agnosticism

This protocol describes concepts (capture, compare, threshold, regions) without prescribing tools.

**LiveSpec provides one reference implementation:**
- Tool: Playwright (page/locator screenshots)
- Comparison: pixelmatch (pixel-level diff)
- Language: TypeScript (helper in `visual.ts`)

**Other frameworks can implement the protocol:**
- Cypress (via `cy.screenshot()`)
- Storybook (via `stories` + visual snapshots)
- Vitest browser (via `@vitest/browser`)

The protocol remains valid; the implementation changes. Each team can define their own helper and thresholds.

---

*LiveSpec Visual Baselines v2.0 — 2026-04-10*
