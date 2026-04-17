# Mockup Workflow Guide

Designer-driven visual baseline workflow for Figma → code fidelity testing.

## Overview

Visual tests compare code screenshots against **designer-exported mockups** — not against the first code capture. This prevents bugs in the initial implementation from becoming permanent baselines.

```
Designer exports Figma mockup → baselines/mockups/component.png
Developer implements component → visual test runs
Test compares code vs mockup → fails if diff > 2%
Designer approves diff → baseline updated
```

## Step 1 — Export from Figma

1. Select the component or artboard in Figma
2. In the Export panel, set scale to **2x** (Retina) — see EC-001 in troubleshooting for 1x/2x mismatch
3. Format: **PNG**
4. Click Export

## Step 2 — Place the mockup

Save the PNG to the correct path:

```
baselines/mockups/<feature-slug>/<component-name>.png
```

Example: `baselines/mockups/auth/signup-form.png`

> EC-008: Baselines are namespaced by feature slug to avoid collisions between features that share component names.

## Step 3 — Create metadata file

Create a `.meta.yml` file alongside the PNG. Run the validator to generate a stub:

```bash
node scripts/validate-mockup-metadata.js baselines/mockups/<feature-slug>/ --fix
```

Then fill in the stub values in `<component-name>.meta.yml`:

```yaml
type: mockup
figma_url: https://figma.com/file/<file-id>/...
artboard_name: Signup Form
component: signup-form
exported_date: 2026-04-17
designer_name: Jane Designer
resolution: 2x
tolerance: 0.02
last_updated: 2026-04-17
invalidate_on:
  - figma_mockup_change
  - designer_approval_revoked
```

### Required fields (AC-002)

| Field | Description |
|-------|-------------|
| `figma_url` | Direct link to the Figma artboard |
| `artboard_name` | Name of the artboard/frame in Figma |
| `exported_date` | ISO 8601 date of the export |
| `designer_name` | Name of the designer who exported |
| `resolution` | `1x` or `2x` |
| `tolerance` | `maxDiffPixelRatio` (default: `0.02` = 2%) |

## Step 4 — Validate metadata

```bash
node scripts/validate-mockup-metadata.js baselines/mockups/
```

All PNGs should show `[OK]`. Fix any `[ERROR]` entries before committing.

## Step 5 — Run visual tests

```bash
npx playwright test tests/visual/mockup-comparison.spec.ts
```

On first run with a new mockup, the test will use the PNG you placed as the baseline for comparison.

If the test fails, a diff image is generated in `test-results/`.

## Approval workflow (AC-006)

When a visual test fails in CI:

1. CI uploads diff artifacts — download from the GitHub Actions run
2. Designer reviews the `actual`, `expected`, and `diff` images
3. If the change is **intentional** (the code is correct and the mockup needs updating):
   ```bash
   npx playwright test --update-snapshots tests/visual/mockup-comparison.spec.ts
   ```
   Then update the `.meta.yml`:
   ```yaml
   approved_by: Jane Designer
   approved_date: 2026-04-17
   diff_percentage: 3.2
   ```
4. If the change is a **bug** (code does not match the designer's intent): fix the code and re-run

## Configuring tolerance per component (AC-004)

Edit `TOLERANCE` in `tests/visual/mockup-comparison.spec.ts`:

```typescript
const TOLERANCE = 0.05; // 5% for components with drop shadows or gradients
```

> EC-010: Increase tolerance to 5% for components with drop shadows, gradients, or anti-aliased edges where CSS and Figma rendering may differ slightly.

## What happens when no mockup exists (AC-005)

If the test runs and no PNG exists at `baselines/mockups/<component>.png`, the test is **skipped** with a `TODO` message:

```
TODO: No mockup baseline at baselines/mockups/signup-form.png.
Designer must export from Figma and place at baselines/mockups/signup-form.png
```

This is intentional — tests do not fail just because a mockup hasn't been created yet. Add mockups progressively as features are designed.

## Related

- **Read** [`troubleshooting.md`](troubleshooting.md) for EC-001 through EC-015
- **Read** [`migration-guide.md`](migration-guide.md) to generate visual tests for existing features in batch
