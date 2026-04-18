# Legacy Test Merge in migrate-visual-tests.js — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When `migrate-visual-tests.js --generate` generates a `route-{slug}.spec.ts`, detect if a legacy `{slug}.spec.ts` exists and merge its custom test blocks + imports into the generated file before deleting the old one.

**Architecture:** Pure static analysis in `scripts/migrate-visual-tests.js`: line-based extraction of non-standard `test(...)` blocks from legacy files, regex-based import symbol merging, injection after the `mobile view` test. A deletion guard in `deleteSupersededTests` verifies custom blocks are present before removing the legacy file.

**Tech Stack:** Node.js ESM (existing), Python pytest (integration tests)

---

### Task 1: Write failing integration tests

**Files:**
- Modify: `tests/integration/test_migrate_visual.py`

- [ ] **Step 1: Add `TestMigrateVisualLegacyMerge` class with 5 failing tests**

Open `tests/integration/test_migrate_visual.py` and append this class at the end of the file:

```python
@pytest.mark.level_3a
class TestMigrateVisualLegacyMerge:
    """Tests for merging custom tests from legacy spec files into route-scan generated files."""

    LEGACY_SETTINGS_CONTENT = """\
import { expect, test } from '@playwright/test';
import { mockAuthenticatedAPIs, mockSettingsFormAPIs } from './fixtures.js';

test.describe('Settings page @visual', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthenticatedAPIs(page);
  });

  test('full page with data', async ({ page }) => {
    await page.goto('/settings', { waitUntil: 'networkidle' });
    await page.waitForSelector('h1');
    await expect(page).toHaveScreenshot('settings-full.png', { fullPage: true });
  });

  test('settings with form validation errors', async ({ page }) => {
    await page.route('**/api/settings/save', (route) =>
      route.fulfill({ status: 422, json: { detail: 'Validation failed' } })
    );
    await page.goto('/settings', { waitUntil: 'networkidle' });
    await page.waitForSelector('[role="alert"]');
    await expect(page).toHaveScreenshot('settings-validation-error.png', { fullPage: true });
  });

  test('settings with success toast', async ({ page }) => {
    await page.goto('/settings', { waitUntil: 'networkidle' });
    await page.fill('[name="username"]', 'newuser');
    await page.click('button[type="submit"]');
    await page.waitForSelector('.toast-success');
    await expect(page).toHaveScreenshot('settings-saved.png', { fullPage: true });
  });
});
"""

    def _setup_legacy(self, fixture: Path, content: str) -> tuple[Path, Path]:
        e2e_dir = fixture / "frontend" / "tests" / "e2e"
        e2e_dir.mkdir(parents=True, exist_ok=True)
        legacy = e2e_dir / "settings.spec.ts"
        legacy.write_text(content)
        return e2e_dir, legacy

    def test_merges_custom_tests_from_legacy_file(
        self, fixture_migrate_visual_frontend: Path
    ) -> None:
        """Custom test blocks from legacy settings.spec.ts are merged into route-settings.spec.ts."""
        e2e_dir, _ = self._setup_legacy(
            fixture_migrate_visual_frontend, self.LEGACY_SETTINGS_CONTENT
        )

        result = _run_generate(fixture_migrate_visual_frontend)
        assert result.returncode == 0, f"Script failed:\n{result.stdout}\n{result.stderr}"

        content = (e2e_dir / "route-settings.spec.ts").read_text()
        assert "settings with form validation errors" in content, "Custom test 1 not merged"
        assert "settings with success toast" in content, "Custom test 2 not merged"

    def test_standard_tests_not_duplicated_from_legacy(
        self, fixture_migrate_visual_frontend: Path
    ) -> None:
        """Test named 'full page with data' in legacy is NOT injected (dedup against standard)."""
        e2e_dir, _ = self._setup_legacy(
            fixture_migrate_visual_frontend, self.LEGACY_SETTINGS_CONTENT
        )

        _run_generate(fixture_migrate_visual_frontend)
        content = (e2e_dir / "route-settings.spec.ts").read_text()
        # Standard name appears exactly once (from template only)
        assert content.count("test('full page with data'") == 1, (
            "Standard test duplicated from legacy"
        )

    def test_custom_imports_merged_from_legacy(
        self, fixture_migrate_visual_frontend: Path
    ) -> None:
        """Custom imports from legacy file are added to route-settings.spec.ts."""
        e2e_dir, _ = self._setup_legacy(
            fixture_migrate_visual_frontend, self.LEGACY_SETTINGS_CONTENT
        )

        _run_generate(fixture_migrate_visual_frontend)
        content = (e2e_dir / "route-settings.spec.ts").read_text()
        assert "mockSettingsFormAPIs" in content, "Custom import not merged into route file"

    def test_provenance_comment_present(
        self, fixture_migrate_visual_frontend: Path
    ) -> None:
        """Preserved custom tests are annotated with their source file."""
        e2e_dir, _ = self._setup_legacy(
            fixture_migrate_visual_frontend, self.LEGACY_SETTINGS_CONTENT
        )

        _run_generate(fixture_migrate_visual_frontend)
        content = (e2e_dir / "route-settings.spec.ts").read_text()
        assert "Preserved from settings.spec.ts" in content, "Provenance comment missing"

    def test_legacy_file_deleted_after_merge(
        self, fixture_migrate_visual_frontend: Path
    ) -> None:
        """Legacy settings.spec.ts is deleted after custom tests are successfully merged."""
        e2e_dir, legacy = self._setup_legacy(
            fixture_migrate_visual_frontend, self.LEGACY_SETTINGS_CONTENT
        )

        result = _run_generate(fixture_migrate_visual_frontend)
        assert result.returncode == 0
        assert not legacy.exists(), "Legacy file should be deleted after successful merge"
        assert (e2e_dir / "route-settings.spec.ts").exists()
```

- [ ] **Step 2: Run tests to confirm all 5 fail**

```bash
cd /Users/julienm/projects/livespec
python3 -m pytest tests/integration/test_migrate_visual.py::TestMigrateVisualLegacyMerge -v 2>&1 | tail -20
```

Expected: 5 FAILED (features not implemented yet)

- [ ] **Step 3: Commit failing tests**

```bash
cd /Users/julienm/projects/livespec
git add tests/integration/test_migrate_visual.py
git commit -m "test(011): add failing integration tests for legacy test merge"
```

---

### Task 2: Add pure parsing functions in migrate-visual-tests.js

**Files:**
- Modify: `scripts/migrate-visual-tests.js` (add after line ~350, after the analysis helpers block)

- [ ] **Step 1: Add STANDARD_TEST_NAMES constant**

Insert after the line `const FRONTEND_MODE = hasFrontendE2E;` (around line 38):

```js
// Names of tests generated by the standard template — used to deduplicate legacy tests
// Must stay in sync with test names in generateE2ETemplate()
const STANDARD_TEST_NAMES = [
  'full page with data',
  'empty state — no data',
  'page header and navigation',
  'mobile view',
];
```

- [ ] **Step 2: Add extractCustomTestBlocks()**

Insert after the `analyzeExistingTests()` function (around line 350):

```js
// ─── Legacy merge helpers ────────────────────────────────────────────────────

// Extract test(...) blocks from a legacy file whose names are NOT in STANDARD_TEST_NAMES.
// Uses line-based parsing: reads from `  test('...` to `  });` (2-space indent).
function extractCustomTestBlocks(content) {
  const blocks = [];
  const lines = content.split('\n');
  let inBlock = false;
  let blockLines = [];
  let blockName = null;

  for (const line of lines) {
    if (!inBlock) {
      const m = line.match(/^  test\(['"]([^'"]+)['"]/);
      if (m) {
        blockName = m[1];
        blockLines = [line];
        inBlock = true;
      }
    } else {
      blockLines.push(line);
      // 2-space-indented }); signals end of a top-level test block
      if (line === '  });') {
        if (!STANDARD_TEST_NAMES.includes(blockName.toLowerCase())) {
          blocks.push({ name: blockName, block: blockLines.join('\n') });
        }
        inBlock = false;
        blockLines = [];
        blockName = null;
      }
    }
  }

  return blocks;
}

// Return test names from customBlocks that are NOT present in generatedContent.
// Used as deletion guard: if any name missing, the merge did not succeed.
function verifyCustomBlocksPresent(generatedContent, customBlocks) {
  return customBlocks
    .map(b => b.name)
    .filter(
      name =>
        !generatedContent.includes(`test('${name}'`) &&
        !generatedContent.includes(`test("${name}"`)
    );
}
```

- [ ] **Step 3: Add mergeAdditionalImports()**

Continue inserting after the functions above:

```js
// Merge imports from legacyContent into templateContent.
// Only adds symbols not already present in the template (by symbol name).
// Returns updated templateContent.
function mergeAdditionalImports(templateContent, legacyContent) {
  const legacyImportLines = (legacyContent.match(/^import .+ from .+;$/gm) || []);
  const templateImportLines = (templateContent.match(/^import .+ from .+;$/gm) || []);

  // Collect symbols already in template
  const templateSymbols = new Set();
  for (const imp of templateImportLines) {
    const m = imp.match(/\{([^}]+)\}/);
    if (m) m[1].split(',').forEach(s => templateSymbols.add(s.trim()));
  }

  const toAdd = [];
  for (const imp of legacyImportLines) {
    const m = imp.match(/\{([^}]+)\}/);
    if (!m) continue; // skip default/side-effect imports

    const legacySymbols = m[1].split(',').map(s => s.trim()).filter(Boolean);
    const newSymbols = legacySymbols.filter(s => !templateSymbols.has(s));
    const conflictSymbols = legacySymbols.filter(s => templateSymbols.has(s));

    if (conflictSymbols.length > 0) {
      console.log(`  [WARN] Import conflict: ${conflictSymbols.join(', ')} already imported`);
    }

    if (newSymbols.length === 0) continue;

    // Reconstruct import with only new symbols
    toAdd.push(imp.replace(/\{[^}]+\}/, `{ ${newSymbols.join(', ')} }`));
  }

  if (toAdd.length === 0) return templateContent;

  // Inject after the last import line in the template
  const lastImportMatch = [...templateContent.matchAll(/^import .+ from .+;$/gm)].at(-1);
  if (!lastImportMatch) return templateContent;

  const insertAt = lastImportMatch.index + lastImportMatch[0].length;
  return templateContent.slice(0, insertAt) + '\n' + toAdd.join('\n') + templateContent.slice(insertAt);
}
```

- [ ] **Step 4: Add injectCustomTestBlocks()**

Continue inserting:

```js
// Inject custom test blocks after the 'mobile view' test in templateContent.
// Falls back to before the final }); of test.describe if 'mobile view' is absent.
function injectCustomTestBlocks(templateContent, customBlocks, sourceSlug) {
  if (customBlocks.length === 0) return templateContent;

  const provenance = `\n  // ── Preserved from ${sourceSlug}.spec.ts ──`;
  const injection = provenance + '\n\n' + customBlocks.map(b => b.block).join('\n\n') + '\n';

  // Find the closing }); of the 'mobile view' test
  const mobileIdx = templateContent.indexOf("test('mobile view'");
  if (mobileIdx === -1) {
    console.warn(`  [WARN] 'mobile view' test not found — injecting before final });`);
    const lastClose = templateContent.lastIndexOf('\n});');
    if (lastClose === -1) return templateContent;
    return templateContent.slice(0, lastClose) + '\n' + injection + templateContent.slice(lastClose);
  }

  // Find `  });` after mobile view (the closing of that test block)
  const closePattern = '\n  });';
  const closeIdx = templateContent.indexOf(closePattern, mobileIdx);
  if (closeIdx === -1) return templateContent;

  const insertAt = closeIdx + closePattern.length;
  return templateContent.slice(0, insertAt) + '\n' + injection + templateContent.slice(insertAt);
}

// Find the legacy test file for a given slug, if it exists.
// Returns the file path if {testDir}/{slug}.spec.ts exists and is not numbered/route-prefixed.
function findLegacyTestFile(slug, testDir) {
  const candidate = join(testDir, `${slug}.spec.ts`);
  if (!existsSync(candidate)) return null;
  const base = basename(candidate);
  if (/^\d{3}-/.test(base) || base.startsWith('route-')) return null;
  return candidate;
}
```

- [ ] **Step 5: Verify no syntax errors**

```bash
cd /Users/julienm/projects/livespec
node --input-type=module < scripts/migrate-visual-tests.js --scan 2>&1 | head -5
node scripts/migrate-visual-tests.js --scan 2>&1 | head -5
```

Expected: scan output (not a syntax error)

---

### Task 3: Modify generateRouteTest to merge legacy

**Files:**
- Modify: `scripts/migrate-visual-tests.js:743-759` (generateRouteTest function)

- [ ] **Step 1: Replace generateRouteTest with merge-aware version**

Replace the entire `generateRouteTest` function (currently lines 743-759):

```js
// Generate a test file for a route-scan feature.
// If a legacy {slug}.spec.ts exists, extract custom blocks and merge into the new template.
// Returns { legacyPath, customBlocks } if a merge occurred, null otherwise.
function generateRouteTest(routeFeature, analysis = {}, dryRun = false) {
  const { slug, route, heading, testPath } = routeFeature;

  if (dryRun) {
    const legacyPath = findLegacyTestFile(slug, TEST_DIR);
    if (legacyPath) {
      const legacy = readFileSync(legacyPath, 'utf-8');
      const customBlocks = extractCustomTestBlocks(legacy);
      if (customBlocks.length > 0) {
        console.log(`  [WOULD MERGE] ${customBlocks.length} custom test(s) from ${slug}.spec.ts → ${testPath}`);
      }
    }
    console.log(`  [WOULD CREATE/UPDATE] ${testPath} (route scan: ${route})`);
    return null;
  }

  mkdirSync(TEST_DIR, { recursive: true });

  const syntheticFeature = { dir: slug, slug, specPath: '' };
  const specCtx = { heading, route, acRows: [] };
  let content = generateE2ETemplate(syntheticFeature, analysis, specCtx);

  // Legacy merge: detect and merge custom tests from old file
  const legacyPath = findLegacyTestFile(slug, TEST_DIR);
  let mergedCustomBlocks = [];
  if (legacyPath) {
    const legacyContent = readFileSync(legacyPath, 'utf-8');
    const customBlocks = extractCustomTestBlocks(legacyContent);
    if (customBlocks.length > 0) {
      content = mergeAdditionalImports(content, legacyContent);
      content = injectCustomTestBlocks(content, customBlocks, slug);
      console.log(`  [MERGE] ${customBlocks.length} custom test(s) from ${slug}.spec.ts → ${testPath}`);
      mergedCustomBlocks = customBlocks;
    }
  }

  writeFileSync(testPath, content);
  console.log(`  [CREATED/UPDATED] ${testPath} (route: ${route})`);

  return legacyPath ? { legacyPath, customBlocks: mergedCustomBlocks } : null;
}
```

---

### Task 4: Thread mergeResults through generateTests + deleteSupersededTests

**Files:**
- Modify: `scripts/migrate-visual-tests.js` (generateTests and deleteSupersededTests)

- [ ] **Step 1: Update deleteSupersededTests signature to accept mergeResults**

Replace the existing function signature + loop (currently lines 762-795). Find:

```js
function deleteSupersededTests(allCoveredRoutes, dryRun) {
```

Replace with the full function including deletion guard:

```js
function deleteSupersededTests(allCoveredRoutes, dryRun, mergeResults = new Map()) {
  if (!existsSync(TEST_DIR)) return 0;

  const files = readdirSync(TEST_DIR).filter(f => f.endsWith('.spec.ts'));
  const superseded = files.filter(f => {
    if (/^\d{3}-/.test(f)) return false;
    if (f.startsWith('route-')) return false;
    const slug = f.replace(/\.spec\.ts$/, '');
    const inferredRoute = slug === 'index' ? '/' : `/${slug}`;
    return allCoveredRoutes.has(inferredRoute);
  });

  if (superseded.length === 0) return 0;

  console.log(`\n🗑  Removing superseded tests (now covered by numbered or route-scan tests):`);
  let removed = 0;
  for (const f of superseded) {
    const filePath = join(TEST_DIR, f);
    const slug = f.replace(/\.spec\.ts$/, '');
    const route = slug === 'index' ? '/' : `/${slug}`;
    if (dryRun) {
      console.log(`  [WOULD DELETE] ${filePath} (route ${route} now covered)`);
    } else {
      // Deletion guard: verify merged custom tests are present before deleting
      if (mergeResults.has(filePath) && mergeResults.get(filePath).length > 0) {
        const customBlocks = mergeResults.get(filePath);
        const routeTestPath = join(TEST_DIR, `route-${slug}.spec.ts`);
        if (existsSync(routeTestPath)) {
          const generatedContent = readFileSync(routeTestPath, 'utf-8');
          const missingNames = verifyCustomBlocksPresent(generatedContent, customBlocks);
          if (missingNames.length > 0) {
            for (const name of missingNames) {
              console.warn(`  [WARN] Legacy test not found in output: "${name}" — skipping deletion of ${f}`);
            }
            continue; // Skip deletion, preserve legacy file
          }
        }
      }
      rmSync(filePath);
      console.log(`  🗑  Deleted ${f} (route ${route} now covered)`);
      removed++;
    }
  }
  return removed;
}
```

- [ ] **Step 2: Collect mergeResults in generateTests Phase 2**

In `generateTests`, find the Phase 2 block (currently around line 1213):

```js
  // Phase 2: Route-scan tests (always overwrite — scaffold)
  if (routeScanFeatures.length > 0) {
    console.log(`\n🔍 Route scan (${routeScanFeatures.length} uncovered page(s)):`);
    for (const routeFeature of routeScanFeatures) {
      generateRouteTest(routeFeature, analysis, dryRun);
      if (!dryRun) routeGenerated++;
    }
  }
```

Replace with:

```js
  // Phase 2: Route-scan tests (always overwrite — scaffold)
  const mergeResults = new Map(); // legacyPath → customBlocks[] for deletion guard
  if (routeScanFeatures.length > 0) {
    console.log(`\n🔍 Route scan (${routeScanFeatures.length} uncovered page(s)):`);
    for (const routeFeature of routeScanFeatures) {
      const mergeResult = generateRouteTest(routeFeature, analysis, dryRun);
      if (mergeResult?.legacyPath) {
        mergeResults.set(mergeResult.legacyPath, mergeResult.customBlocks);
      }
      if (!dryRun) routeGenerated++;
    }
  }
```

- [ ] **Step 3: Pass mergeResults to deleteSupersededTests in Phase 4**

Find:

```js
  // Phase 4: Delete superseded old tests
  deleteSupersededTests(allCoveredRoutes, dryRun);
```

Replace with:

```js
  // Phase 4: Delete superseded old tests (guarded by merge verification)
  deleteSupersededTests(allCoveredRoutes, dryRun, mergeResults);
```

- [ ] **Step 4: Verify no syntax errors**

```bash
cd /Users/julienm/projects/livespec
node scripts/migrate-visual-tests.js --scan 2>&1 | head -10
```

Expected: Feature scan table (no syntax errors)

---

### Task 5: Run all tests and fix any failures

- [ ] **Step 1: Run the new integration tests**

```bash
cd /Users/julienm/projects/livespec
python3 -m pytest tests/integration/test_migrate_visual.py::TestMigrateVisualLegacyMerge -v 2>&1 | tail -30
```

Expected: 5 PASSED

- [ ] **Step 2: Run the full integration test suite to check for regressions**

```bash
cd /Users/julienm/projects/livespec
python3 -m pytest tests/integration/test_migrate_visual.py -v 2>&1 | tail -30
```

Expected: All tests PASSED (including pre-existing tests for `TestMigrateVisualDeleteSuperseded`)

- [ ] **Step 3: Run the full test suite**

```bash
cd /Users/julienm/projects/livespec
python3 -m pytest tests/ -x -q 2>&1 | tail -20
```

Expected: All tests pass

- [ ] **Step 4: Fix any failures before committing**

If `test_deletes_superseded_test_covered_by_route_scan` fails:
- The test creates `settings.spec.ts` with `// old hand-crafted test\n` — no custom blocks
- `extractCustomTestBlocks` should return `[]` for this content → no merge, deletion proceeds
- Verify by tracing through `extractCustomTestBlocks("// old hand-crafted test\n")` → returns `[]`

If `test_route_test_overwrites_on_regenerate` fails:
- This test verifies that `route-settings.spec.ts` is overwritten on second run
- `generateRouteTest` still always overwrites (no AC-030 for route tests)
- Should still pass since we only added merge logic before writing, not a guard

- [ ] **Step 5: Commit**

```bash
cd /Users/julienm/projects/livespec
git add scripts/migrate-visual-tests.js tests/integration/test_migrate_visual.py
git commit -m "feat(011): merge legacy test blocks into route-scan generated files

When migrate-visual-tests.js generates route-{slug}.spec.ts and a legacy
{slug}.spec.ts exists, custom test blocks (those not in the 4 standard
template tests) are extracted and merged into the new file. Additional
imports used by custom tests are also merged. A deletion guard prevents
the legacy file from being removed if the merge verification fails."
```

---

## Self-Review

### Spec coverage

| Requirement | Task |
|---|---|
| Detect legacy file for same route | Task 2 (`findLegacyTestFile`) |
| Extract non-standard test blocks | Task 2 (`extractCustomTestBlocks`) |
| Merge imports from legacy | Task 2 (`mergeAdditionalImports`) |
| Inject custom blocks into template | Task 2 (`injectCustomTestBlocks`) |
| Deletion guard (verify before delete) | Task 4 (`deleteSupersededTests` guard) |
| Provenance comment | Task 2 (`injectCustomTestBlocks` marker) |
| Deduplication of standard test names | Task 2 (`STANDARD_TEST_NAMES`) |
| Integration tests for all behaviors | Task 1 |
| Existing tests still pass | Task 5 |

### Placeholder scan

No TBDs, TODOs, or "similar to Task N" patterns. All code blocks are complete.

### Type consistency

- `extractCustomTestBlocks(content)` → `Array<{name: string, block: string}>` — used consistently in `generateRouteTest` and `verifyCustomBlocksPresent`
- `findLegacyTestFile(slug, testDir)` → `string|null` — used in `generateRouteTest`
- `generateRouteTest()` → `{legacyPath: string, customBlocks: Array}|null` — consumed in `generateTests`
- `mergeResults: Map<string, Array>` — passed from Phase 2 to `deleteSupersededTests`
