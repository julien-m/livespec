# Visual Test Migration Guide

Scaffold visual tests for existing features in batch using the migration tool.

## Overview

The migration tool (`scripts/migrate-visual-tests.js`) scans all features in `.specs/features/` and generates Playwright test templates for features that:
- Have a `spec.md` with UI keywords (button, modal, form, page, etc.)
- Don't already have a test file in `tests/visual/`

## Step 1 — Assess coverage gaps (AC-027)

```bash
node scripts/migrate-visual-tests.js --scan
```

Output:

```
Feature Migration Scan

Feature                          | Has UI | Has Tests | Action
--------------------------------|--------|-----------|-------------------
001-user-authentication         |  YES   |   YES     | SKIP (has tests)
002-sdk-isolated                |   NO   |    NO     | SKIP (no UI)
009-visual-state-baselines      |  YES   |   YES     | SKIP (has tests)
010-visual-testing-complete     |  YES   |    NO     | GENERATE
...

5 UI feature(s), 3 without visual tests
Run with --generate to scaffold test files, or --dry-run to preview
```

## Step 2 — Preview planned changes (--dry-run)

```bash
node scripts/migrate-visual-tests.js --dry-run
```

Shows what would be created without writing any files. Exit code is always 0.

## Step 3 — Generate test files (AC-028)

```bash
node scripts/migrate-visual-tests.js --generate
```

For each feature without tests, this:
1. Creates `tests/visual/<feature-slug>.spec.ts` from a template
2. Creates baseline directories (AC-029):
   - `baselines/mockups/<feature>/`
   - `baselines/fullpage/<feature>/`
   - `baselines/mobile/<feature>/`
   - `baselines/tablet/<feature>/`
   - `baselines/desktop/<feature>/`
   - `baselines/animations/<feature>/`
3. Adds `.gitkeep` files so empty directories are committed

## Step 4 — Post-migration checklist

After running `--generate`:

1. **Export Figma mockups** for each generated feature → `baselines/mockups/<feature>/main.png`
2. **Create metadata files** → `node scripts/validate-mockup-metadata.js baselines/mockups/ --fix`
3. **Replace TODO placeholders** in generated test files:
   - Routes: `'/TODO-replace-with-actual-route'`
   - Selectors: `'[data-testid="TODO-replace-selector"]'`
4. **Establish baselines**:
   ```bash
   npx playwright test --update-snapshots tests/visual/<feature>.spec.ts
   ```
5. **Verify tests pass**:
   ```bash
   npx playwright test tests/visual/<feature>.spec.ts
   ```

## AC-030: Existing tests are never overwritten

The migration tool has a hard guard: if `tests/visual/<feature>.spec.ts` already exists, it is **never overwritten** — not even with `--generate`. There is no `--force` flag.

This preserves manually written tests that may have custom assertions, advanced scenarios, or non-standard selectors.

To regenerate a test from scratch, delete the existing file first, then run `--generate`.

## Which features to prioritize (incremental migration)

Migrate in this order:

1. **P0 stories first** — features from spec with `P0` priority markers
2. **Core user flows** — authentication, onboarding, main dashboard
3. **High-traffic pages** — pages with the most user interactions
4. **Recently changed features** — features modified in the last sprint

## EC-007: Backend-only features are skipped

Features without UI keywords (button, modal, form, page, layout, etc.) are skipped automatically. This covers:
- Python validator modules
- CLI-only commands
- Migration scripts
- Internal tooling

If a feature is incorrectly classified as "no UI", manually create the test file:

```bash
cp tests/visual/mockup-comparison.spec.ts tests/visual/<feature-slug>.spec.ts
# Edit the new file to configure COMPONENT, MOCKUP_DIR, etc.
```

## Related

- **Read** [`mockup-workflow.md`](mockup-workflow.md) — how to add Figma mockups after migration
- **Read** [`README.md`](README.md) — visual testing quick-start
