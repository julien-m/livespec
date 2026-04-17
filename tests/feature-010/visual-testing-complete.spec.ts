import { test, expect } from '@playwright/test';
import { existsSync, readFileSync } from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

// Meta-tests for Feature 010 — Visual Testing Complete
// Validates artifact existence and structural correctness.
// No screenshot comparisons — pure file-system assertions (per constitution: no UI tests for LiveSpec itself).

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.join(__dirname, '../..');

// AC-001 through AC-006: Mockup workflow artifacts
test('mockup-comparison.spec.ts template exists', () => {
  expect(existsSync(path.join(ROOT, 'tests/visual/mockup-comparison.spec.ts'))).toBe(true);
});

test('validate-mockup-metadata.js script exists', () => {
  expect(existsSync(path.join(ROOT, 'scripts/validate-mockup-metadata.js'))).toBe(true);
});

test('mockup-workflow.md guide exists', () => {
  expect(existsSync(path.join(ROOT, 'docs/visual-testing/mockup-workflow.md'))).toBe(true);
});

test('mockup-comparison.spec.ts contains tolerance configuration', () => {
  const content = readFileSync(path.join(ROOT, 'tests/visual/mockup-comparison.spec.ts'), 'utf-8');
  expect(content).toContain('maxDiffPixelRatio');
  expect(content).toContain('TOLERANCE');
});

test('mockup-comparison.spec.ts handles missing baseline with skip', () => {
  const content = readFileSync(path.join(ROOT, 'tests/visual/mockup-comparison.spec.ts'), 'utf-8');
  expect(content).toContain('test.skip');
  expect(content).toContain('TODO');
});

// AC-007 through AC-011: Full-page layout artifacts
test('fullpage-layout.spec.ts template exists', () => {
  expect(existsSync(path.join(ROOT, 'tests/visual/fullpage-layout.spec.ts'))).toBe(true);
});

test('fullpage-testing.md guide exists', () => {
  expect(existsSync(path.join(ROOT, 'docs/visual-testing/fullpage-testing.md'))).toBe(true);
});

test('fullpage-layout.spec.ts uses fullPage option', () => {
  const content = readFileSync(path.join(ROOT, 'tests/visual/fullpage-layout.spec.ts'), 'utf-8');
  expect(content).toContain('fullPage');
});

// AC-012 through AC-016: Responsive viewport artifacts
test('responsive-viewports.spec.ts template exists', () => {
  expect(existsSync(path.join(ROOT, 'tests/visual/responsive-viewports.spec.ts'))).toBe(true);
});

test('responsive-testing.md guide exists', () => {
  expect(existsSync(path.join(ROOT, 'docs/visual-testing/responsive-testing.md'))).toBe(true);
});

test('playwright.config.ts defines 5 viewport+browser projects', () => {
  const config = readFileSync(path.join(ROOT, 'playwright.config.ts'), 'utf-8');
  expect(config).toContain('mobile-chromium');
  expect(config).toContain('tablet-chromium');
  expect(config).toContain('desktop-chromium');
  expect(config).toContain('desktop-firefox');
  expect(config).toContain('desktop-webkit');
});

test('playwright.config.ts defines correct mobile viewport 375x667', () => {
  const config = readFileSync(path.join(ROOT, 'playwright.config.ts'), 'utf-8');
  expect(config).toContain('375');
  expect(config).toContain('667');
});

test('playwright.config.ts defines snapshotPathTemplate for per-project baselines', () => {
  const config = readFileSync(path.join(ROOT, 'playwright.config.ts'), 'utf-8');
  expect(config).toContain('snapshotPathTemplate');
  expect(config).toContain('{projectName}');
});

test('responsive-viewports.spec.ts supports viewport-specific skipping', () => {
  const content = readFileSync(path.join(ROOT, 'tests/visual/responsive-viewports.spec.ts'), 'utf-8');
  expect(content).toContain('APPLICABLE_VIEWPORTS');
  expect(content).toContain('test.skip');
});

// AC-017 through AC-021: Cross-browser artifacts
test('cross-browser-testing.md guide exists', () => {
  expect(existsSync(path.join(ROOT, 'docs/visual-testing/cross-browser-testing.md'))).toBe(true);
});

test('cross-browser-testing.md covers all 3 browsers', () => {
  const content = readFileSync(path.join(ROOT, 'docs/visual-testing/cross-browser-testing.md'), 'utf-8');
  expect(content).toContain('Chromium');
  expect(content).toContain('Firefox');
  expect(content).toContain('WebKit');
});

// AC-022 through AC-026: Animation artifacts
test('animations.spec.ts template exists', () => {
  expect(existsSync(path.join(ROOT, 'tests/visual/animations.spec.ts'))).toBe(true);
});

test('capture-keyframes.ts script exists', () => {
  expect(existsSync(path.join(ROOT, 'scripts/capture-keyframes.ts'))).toBe(true);
});

test('animation-testing.md guide exists', () => {
  expect(existsSync(path.join(ROOT, 'docs/visual-testing/animation-testing.md'))).toBe(true);
});

test('animations.spec.ts captures 3 keyframes (0%, 50%, 100%)', () => {
  const content = readFileSync(path.join(ROOT, 'tests/visual/animations.spec.ts'), 'utf-8');
  expect(content).toContain('kf-0pct');
  expect(content).toContain('kf-50pct');
  expect(content).toContain('kf-100pct');
});

test('animations.spec.ts uses animations: allow', () => {
  const content = readFileSync(path.join(ROOT, 'tests/visual/animations.spec.ts'), 'utf-8');
  expect(content).toContain("animations: 'allow'");
});

test('animations.spec.ts uses waitForTimeout for keyframe timing', () => {
  const content = readFileSync(path.join(ROOT, 'tests/visual/animations.spec.ts'), 'utf-8');
  expect(content).toContain('waitForTimeout');
});

// AC-027 through AC-030: Migration tool artifacts
test('migrate-visual-tests.js script exists', () => {
  expect(existsSync(path.join(ROOT, 'scripts/migrate-visual-tests.js'))).toBe(true);
});

test('migration-guide.md guide exists', () => {
  expect(existsSync(path.join(ROOT, 'docs/visual-testing/migration-guide.md'))).toBe(true);
});

test('migrate-visual-tests.js supports --scan, --generate, --dry-run flags', () => {
  const content = readFileSync(path.join(ROOT, 'scripts/migrate-visual-tests.js'), 'utf-8');
  expect(content).toContain('--scan');
  expect(content).toContain('--generate');
  expect(content).toContain('--dry-run');
});

test('migrate-visual-tests.js has hard guard against overwriting existing tests (AC-030)', () => {
  const content = readFileSync(path.join(ROOT, 'scripts/migrate-visual-tests.js'), 'utf-8');
  expect(content).toContain('existsSync');
  // The hard guard: checks if test file exists before writing
  expect(content).toContain('already exists');
});

// CI/CD artifacts
test('visual-tests.yml CI workflow exists', () => {
  expect(existsSync(path.join(ROOT, '.github/workflows/visual-tests.yml'))).toBe(true);
});

test('visual-tests.yml uses matrix strategy', () => {
  const content = readFileSync(path.join(ROOT, '.github/workflows/visual-tests.yml'), 'utf-8');
  expect(content).toContain('matrix');
  expect(content).toContain('mobile-chromium');
  expect(content).toContain('desktop-webkit');
});

test('visual-diff-pr-comment.js script exists', () => {
  expect(existsSync(path.join(ROOT, 'scripts/visual-diff-pr-comment.js'))).toBe(true);
});

test('visual-diff-pr-comment.js is idempotent (updates existing comment)', () => {
  const content = readFileSync(path.join(ROOT, 'scripts/visual-diff-pr-comment.js'), 'utf-8');
  expect(content).toContain('visual-diff-bot');
  expect(content).toContain('existing');
});

// Documentation index
test('docs/visual-testing/README.md index exists', () => {
  expect(existsSync(path.join(ROOT, 'docs/visual-testing/README.md'))).toBe(true);
});

test('troubleshooting.md guide exists and covers EC-001 through EC-015', () => {
  const content = readFileSync(path.join(ROOT, 'docs/visual-testing/troubleshooting.md'), 'utf-8');
  for (let i = 1; i <= 15; i++) {
    expect(content).toContain(`EC-${String(i).padStart(3, '0')}`);
  }
});

// Baseline directories (AC-013, AC-018, AC-023)
const baselineDirs = [
  'mockups', 'fullpage', 'mobile', 'tablet', 'desktop',
  'chromium', 'firefox', 'webkit', 'animations',
];

for (const dir of baselineDirs) {
  test(`baseline directory exists: ${dir}`, () => {
    expect(
      existsSync(path.join(ROOT, `.specs/features/010-visual-testing-complete/baselines/${dir}`))
    ).toBe(true);
  });
}
