#!/usr/bin/env node
// Usage:
//   node scripts/generate-e2e-tests.js --scan           # List features without E2E tests
//   node scripts/generate-e2e-tests.js --generate       # Create E2E test files from Gherkin scenarios
//   node scripts/generate-e2e-tests.js --dry-run        # Preview without creating files (exit 0)
//
// Multi-surface support:
//   - Reads .specs/surfaces.yaml if present (config-first)
//   - Falls back to filesystem detection (legacy behavior)
//   - Iterates over all surfaces with runner=playwright
//
// Reads .specs/features/*/spec.md Gherkin scenarios and generates Playwright E2E tests.

import { existsSync, readdirSync, readFileSync, writeFileSync, mkdirSync } from 'fs';
import { join, basename } from 'path';
import { getPlaywrightSurfaces, hasAnySurface } from './lib/surface-resolver.js';

const SPECS_DIR = '.specs/features';

// ─── Surface resolution (replaces hardcoded detection) ─────────────────────
const SURFACES = getPlaywrightSurfaces();
const hasWebFrontend = SURFACES.length > 0;

// Default TEST_DIR for scan mode (uses first surface or legacy fallback)
let TEST_DIR = SURFACES.length > 0 ? SURFACES[0].testDir : 'tests/visual';

// ─── Fixtures detection ─────────────────────────────────────────────────────

function detectFixtures(testDir) {
  const fixturesTs = join(testDir, 'fixtures.ts');
  const fixturesJs = join(testDir, 'fixtures.js');
  const mockServerTs = join(testDir, 'mock-server.ts');
  const mockServerJs = join(testDir, 'mock-server.js');

  const hasFixtures = existsSync(fixturesTs) || existsSync(fixturesJs);
  const hasMockServer = existsSync(mockServerTs) || existsSync(mockServerJs);
  const fixturesExt = existsSync(fixturesTs) ? '.ts' : existsSync(fixturesJs) ? '.js' : null;
  const mockServerExt = existsSync(mockServerTs) ? '.ts' : existsSync(mockServerJs) ? '.js' : null;

  // Check if fixtures exports mockAuthenticatedAPIs
  let hasAuthFixture = false;
  if (hasFixtures) {
    const fixPath = existsSync(fixturesTs) ? fixturesTs : fixturesJs;
    const content = readFileSync(fixPath, 'utf-8');
    hasAuthFixture = /export\s+(?:const|(?:async\s+)?function)\s+mockAuthenticatedAPIs/.test(content);
  }

  return { hasFixtures, hasMockServer, fixturesExt, mockServerExt, hasAuthFixture };
}

// ─── Helpers ────────────────────────────────────────────────────────────────

function slugify(str) {
  return str.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

// ─── Step translation heuristics ────────────────────────────────────────────

const STEP_PATTERNS = [
  { regex: /(?:user )?navigates? to (\S+)/i, code: (m) => `await page.goto('${m[1]}');` },
  { regex: /(?:user )?(?:is on|visits?) (?:the )?['"]*(\S+?)['"]*\s*page/i, code: (m) => `await page.goto('/${m[1].toLowerCase()}');` },
  { regex: /(?:user )?clicks? (?:the |on )?['"]*(.+?)['"]*$/i, code: (m) => `await page.locator('[data-testid="TODO-${slugify(m[1])}"]').click();` },
  { regex: /(?:user )?enters? ['"]*(.+?)['"]*\s+in (?:the )?['"]*(.+?)['"]*$/i, code: (m) => `await page.locator('[data-testid="TODO-${slugify(m[2])}"]').fill('${m[1]}');` },
  { regex: /(?:user )?submits? (?:the )?form/i, code: () => `await page.locator('[type="submit"]').click();` },
  { regex: /(?:system |page )?displays? ['"]*(.+?)['"]*$/i, code: (m) => `await expect(page.locator('text=${m[1]}')).toBeVisible();` },
  { regex: /(?:system )?redirects? to (\S+)/i, code: (m) => `await page.waitForURL('**${m[1]}**');` },
  { regex: /(?:system )?shows? (?:an? )?error/i, code: () => `await expect(page.locator('[role="alert"]')).toBeVisible();` },
  { regex: /(?:system )?(?:issues?|sets?) (?:an? )?(?:session )?cookie/i, code: () => `// Cookie set (verified via browser context)` },
  { regex: /does not|is not|are not/i, code: (m) => `// TODO: negate assertion — ${m.input.trim()}` },
];

function translateStep(stepText) {
  const trimmed = stepText.replace(/^(Given|When|Then|And|But)\s+/i, '').trim();
  for (const pattern of STEP_PATTERNS) {
    const match = trimmed.match(pattern.regex);
    if (match) return { code: pattern.code(match), matched: true };
  }
  return { code: `// TODO: ${trimmed}`, matched: false };
}

// ─── Gherkin extraction ─────────────────────────────────────────────────────

function extractGherkinBlocks(specContent) {
  const blocks = [];
  const gherkinRegex = /```gherkin\s*\n([\s\S]*?)```/g;
  let match;

  // Also extract user story headings above each gherkin block
  const lines = specContent.split('\n');

  while ((match = gherkinRegex.exec(specContent)) !== null) {
    const blockContent = match[1];
    const blockStart = match.index;

    // Find user story heading above this block
    const textBefore = specContent.slice(0, blockStart);
    const usMatch = textBefore.match(/###\s+US-(\d+):\s*(.+?)\s*$/m);
    const userStory = usMatch ? { id: `US-${usMatch[1]}`, title: usMatch[2].trim() } : null;

    // Parse the gherkin block
    let featureName = null;
    const scenarios = [];
    let currentScenario = null;

    for (const line of blockContent.split('\n')) {
      const trimmed = line.trim();

      const featureMatch = trimmed.match(/^Feature:\s*(.+)/);
      if (featureMatch) {
        featureName = featureMatch[1].trim();
        continue;
      }

      const scenarioMatch = trimmed.match(/^Scenario:\s*(.+)/);
      if (scenarioMatch) {
        if (currentScenario) scenarios.push(currentScenario);
        currentScenario = { name: scenarioMatch[1].trim(), steps: [] };
        continue;
      }

      const stepMatch = trimmed.match(/^(Given|When|Then|And|But)\s+(.+)/);
      if (stepMatch && currentScenario) {
        currentScenario.steps.push({
          keyword: stepMatch[1],
          text: trimmed,
          body: stepMatch[2].trim(),
        });
      }
    }
    if (currentScenario) scenarios.push(currentScenario);

    blocks.push({ featureName, scenarios, userStory });
  }

  return blocks;
}

// ─── Route extraction from spec ─────────────────────────────────────────────

function extractRouteFromSpec(specContent) {
  const routeCounts = {};

  // Pattern: navigates to /path, goto /path
  const navMatches = specContent.matchAll(/(?:navigates? to|goto)\s+(\/[a-z][a-z0-9\-/]*)/gi);
  for (const m of navMatches) {
    const route = m[1];
    routeCounts[route] = (routeCounts[route] || 0) + 1;
  }

  // Pattern: backtick routes in Mermaid or inline code
  const tickMatches = specContent.matchAll(/`(\/[a-z][a-z0-9\-/]*)`/g);
  for (const m of tickMatches) {
    const route = m[1];
    if (!route.startsWith('/api') && !route.startsWith('/ws')) {
      routeCounts[route] = (routeCounts[route] || 0) + 1;
    }
  }

  // Pattern: routes in Mermaid node labels
  const mermaidMatches = specContent.matchAll(/\[["']?(\/[a-z][a-z0-9\-/]*)["']?\]/g);
  for (const m of mermaidMatches) {
    const route = m[1];
    if (!route.startsWith('/api') && !route.startsWith('/ws')) {
      routeCounts[route] = (routeCounts[route] || 0) + 1;
    }
  }

  if (Object.keys(routeCounts).length === 0) return '/';

  // Return most common route
  const sorted = Object.entries(routeCounts).sort((a, b) => b[1] - a[1]);
  return sorted[0][0];
}

// ─── Existing test detection ────────────────────────────────────────────────

function hasExistingTest(featureNum, slug, testDir) {
  const candidates = [
    join(testDir, `e2e-${featureNum}-${slug}.spec.ts`),
    join(testDir, `${featureNum}-${slug}.spec.ts`),
  ];

  for (const candidate of candidates) {
    if (!existsSync(candidate)) continue;

    const content = readFileSync(candidate, 'utf-8');
    const lineCount = content.split('\n').length;
    if (lineCount <= 10) continue;

    // Must have at least one real test (not just a placeholder)
    const testCalls = [...content.matchAll(/test\(\s*['"](.*?)['"]/g)];
    const hasRealTest = testCalls.some(m => !m[1].includes('placeholder'));
    if (hasRealTest) return true;
  }

  return false;
}

// ─── Scenario translation ───────────────────────────────────────────────────

function translateScenario(scenario) {
  const steps = scenario.steps.map(step => {
    const result = translateStep(step.text);
    return { ...step, ...result };
  });

  const allUnmatched = steps.every(s => !s.matched);
  const someMatched = steps.some(s => s.matched);

  if (allUnmatched) {
    // Emit test.todo() with Gherkin as block comment
    const gherkinBlock = scenario.steps.map(s => `   * ${s.text}`).join('\n');
    return {
      type: 'todo',
      code: `  test.todo('${escapeQuotes(scenario.name)}');\n  /*\n${gherkinBlock}\n   */`,
    };
  }

  // Emit test() with translated steps
  const bodyLines = [];
  let currentPhase = null;

  for (const step of steps) {
    // Phase comments
    const keyword = step.keyword.toLowerCase();
    if ((keyword === 'given') && currentPhase !== 'setup') {
      bodyLines.push('    // Setup');
      currentPhase = 'setup';
    } else if ((keyword === 'when') && currentPhase !== 'action') {
      bodyLines.push('    // Action');
      currentPhase = 'action';
    } else if ((keyword === 'then') && currentPhase !== 'assertion') {
      bodyLines.push('    // Assertion');
      currentPhase = 'assertion';
    }

    bodyLines.push(`    ${step.code}`);
  }

  return {
    type: 'test',
    code: `  test('${escapeQuotes(scenario.name)}', async ({ page }) => {\n${bodyLines.join('\n')}\n  });`,
  };
}

function escapeQuotes(str) {
  return str.replace(/'/g, "\\'");
}

// ─── Feature scanning ───────────────────────────────────────────────────────

function scanFeatures() {
  if (!existsSync(SPECS_DIR)) {
    console.error(`Missing .specs/features/ directory. Is this a LiveSpec project?`);
    process.exit(1);
  }

  const features = readdirSync(SPECS_DIR, { withFileTypes: true })
    .filter(e => e.isDirectory())
    .map(e => e.name);

  return features.map(featureDir => {
    const specPath = join(SPECS_DIR, featureDir, 'spec.md');

    // Extract feature number (NNN or NNN.N pattern)
    const numMatch = featureDir.match(/^([\d.]+)-/);
    const featureNum = numMatch ? numMatch[1] : null;

    // Extract slug (everything after the number prefix)
    const slug = featureDir.replace(/^[\d.]+-/, '');

    const hasSpec = existsSync(specPath);
    let gherkinBlocks = [];
    let specContent = '';

    if (hasSpec) {
      specContent = readFileSync(specPath, 'utf-8');
      gherkinBlocks = extractGherkinBlocks(specContent);
    }

    const hasGherkin = gherkinBlocks.length > 0 &&
      gherkinBlocks.some(b => b.scenarios.length > 0);

    const existingTest = featureNum ? hasExistingTest(featureNum, slug, TEST_DIR) : false;

    return {
      dir: featureDir,
      featureNum,
      slug,
      specPath,
      hasSpec,
      hasGherkin,
      gherkinBlocks,
      specContent,
      hasTests: existingTest,
      action: hasGherkin && !existingTest ? 'GENERATE' : existingTest ? 'SKIP (has tests)' : !hasGherkin ? 'SKIP (no Gherkin)' : 'OK',
    };
  });
}

// ─── Test file generation ───────────────────────────────────────────────────

function generateTestFile(feature, fixtures) {
  const { featureNum, slug, gherkinBlocks, specContent } = feature;

  // Feature title from spec
  let featureTitle = slug.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
  const titleMatch = specContent.match(/^title:\s*["']?(.+?)["']?\s*$/m);
  if (titleMatch) featureTitle = titleMatch[1].replace(/^Feature:\s*/i, '').trim();
  // Fallback to Gherkin Feature: line
  for (const block of gherkinBlocks) {
    if (block.featureName) { featureTitle = block.featureName; break; }
  }

  // Route extraction
  const route = extractRouteFromSpec(specContent);

  // Fixture imports
  let fixtureImports = '';
  if (fixtures.hasFixtures && fixtures.hasAuthFixture) {
    const ext = fixtures.fixturesExt === '.ts' ? '.js' : fixtures.fixturesExt;
    fixtureImports = `import { mockAuthenticatedAPIs } from './fixtures${ext || '.js'}';`;
  }

  // beforeEach content
  let beforeEachContent;
  if (fixtures.hasFixtures && fixtures.hasAuthFixture) {
    beforeEachContent = `await mockAuthenticatedAPIs(page);`;
  } else {
    beforeEachContent = `await page.goto(ROUTE);`;
  }

  // Translate all scenarios
  const testBlocks = [];
  for (const block of gherkinBlocks) {
    if (block.userStory) {
      testBlocks.push(`  // ${block.userStory.id}: ${block.userStory.title}`);
    }
    for (const scenario of block.scenarios) {
      const translated = translateScenario(scenario);
      testBlocks.push(translated.code);
    }
  }

  const tests = testBlocks.join('\n\n');
  const fixtureImportLine = fixtureImports ? `\n${fixtureImports}` : '';

  return `import { test, expect } from '@playwright/test';${fixtureImportLine}

// E2E tests for: ${featureTitle}
// Feature: ${featureNum}-${slug}
// Generated by: scripts/generate-e2e-tests.js
// Source: .specs/features/${featureNum}-${slug}/spec.md

const ROUTE = '${route}';

test.describe('${escapeQuotes(featureTitle)}', () => {

  test.beforeEach(async ({ page }) => {
    ${beforeEachContent}
  });

${tests}
});
`;
}

// ─── Output formatting ──────────────────────────────────────────────────────

function printScanTable(features) {
  console.log(`\nE2E Test Generation Scan  [test dir: ${TEST_DIR}]\n`);
  console.log('Feature                          | Gherkin | Has Tests | Action');
  console.log('--------------------------------|---------|-----------|-------------------');
  for (const f of features) {
    const name = f.dir.padEnd(32).slice(0, 32);
    const hasGherkin = f.hasGherkin ? '  YES  ' : '   NO  ';
    const hasTests = f.hasTests ? '   YES  ' : '    NO  ';
    console.log(`${name}|${hasGherkin}  |${hasTests} | ${f.action}`);
  }

  const needTests = features.filter(f => f.hasGherkin && !f.hasTests).length;
  const totalGherkin = features.filter(f => f.hasGherkin).length;
  console.log(`\n${totalGherkin} feature(s) with Gherkin scenarios, ${needTests} without E2E tests`);
  if (needTests > 0) {
    console.log(`Run with --generate to scaffold test files, or --dry-run to preview`);
  }
}

function generateTests(features, dryRun) {
  const toGenerate = features.filter(f => f.hasGherkin && !f.hasTests);

  if (toGenerate.length === 0) {
    console.log('All features with Gherkin scenarios already have E2E tests. Nothing to generate.');
    console.log(`E2E_GENERATE_RESULT: files=0 skipped=${features.filter(f => f.hasTests).length} reason=all-covered`);
    process.exit(0);
  }

  const fixtures = detectFixtures(TEST_DIR);
  let generated = 0;
  let skipped = 0;
  const createdPaths = [];

  console.log(`\n${dryRun ? '[DRY RUN] Would generate' : 'Generating'} ${toGenerate.length} E2E test file(s):\n`);

  for (const feature of toGenerate) {
    const filename = `e2e-${feature.featureNum}-${feature.slug}.spec.ts`;
    const testPath = join(TEST_DIR, filename);

    if (dryRun) {
      console.log(`  [WOULD CREATE] ${testPath}`);
      const scenarioCount = feature.gherkinBlocks.reduce((acc, b) => acc + b.scenarios.length, 0);
      console.log(`    → ${scenarioCount} scenario(s) from ${feature.gherkinBlocks.length} Gherkin block(s)`);
      generated++;
      continue;
    }

    // Guard: never overwrite
    if (existsSync(testPath)) {
      console.log(`  [SKIP] ${testPath} already exists`);
      skipped++;
      continue;
    }

    const content = generateTestFile(feature, fixtures);
    mkdirSync(TEST_DIR, { recursive: true });
    writeFileSync(testPath, content);
    console.log(`  [CREATED] ${testPath}`);
    createdPaths.push(testPath);
    generated++;
  }

  const totalSkipped = features.filter(f => f.hasTests).length + skipped;

  if (!dryRun) {
    // Human-readable summary
    console.log(`\nE2E test generation:`);
    console.log(`  ${generated} file(s) created:`);
    for (const p of createdPaths) {
      console.log(`    ${p}`);
    }
    if (totalSkipped > 0) {
      console.log(`  ${totalSkipped} feature(s) skipped (tests already exist)`);
    }
  }

  // Sentinel output — always last line
  const reason = dryRun ? 'dry-run' : '';
  const reasonSuffix = reason ? ` reason=${reason}` : '';
  console.log(`E2E_GENERATE_RESULT: files=${generated} skipped=${totalSkipped}${reasonSuffix}`);
}

// ─── Main ───────────────────────────────────────────────────────────────────

const args = process.argv.slice(2);
const scan = args.includes('--scan');
const generate = args.includes('--generate');
const dryRun = args.includes('--dry-run');

if (!scan && !generate && !dryRun) {
  console.log('Usage:');
  console.log('  node scripts/generate-e2e-tests.js --scan       # List features without E2E tests');
  console.log('  node scripts/generate-e2e-tests.js --generate   # Create E2E test files from Gherkin');
  console.log('  node scripts/generate-e2e-tests.js --dry-run    # Preview without creating files');
  process.exit(1);
}

if (!hasWebFrontend && !args.includes('--force')) {
  console.log('\nNo web frontend detected — E2E test generation skipped.');
  console.log('Use --force to generate anyway.');
  console.log('E2E_GENERATE_RESULT: files=0 skipped=0 reason=no-frontend');
  process.exit(0);
}

// Multi-surface loop: iterate over all playwright surfaces
let totalGenerated = 0;
let totalSkipped = 0;

for (const surface of SURFACES) {
  TEST_DIR = surface.testDir;

  if (SURFACES.length > 1) {
    console.log(`\n── Surface: ${surface.name} (${surface.id}) → ${surface.testDir} ──`);
  }

  const features = scanFeatures();

  if (scan) {
    printScanTable(features);
    continue;
  }

  if (dryRun || generate) {
    printScanTable(features);
    generateTests(features, dryRun);
  }
}

if (scan) {
  process.exit(0);
}
