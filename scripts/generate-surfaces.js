#!/usr/bin/env node
// Migration script: generates .specs/surfaces.yaml from filesystem detection.
// Idempotent: skips if surfaces.yaml already exists.
//
// Usage:
//   node scripts/generate-surfaces.js              # Generate surfaces.yaml
//   node scripts/generate-surfaces.js --dry-run    # Preview without creating file
//   node scripts/generate-surfaces.js --force      # Overwrite existing file

import { existsSync, readdirSync, readFileSync, writeFileSync } from 'fs';
import { join } from 'path';

const SURFACES_CONFIG = '.specs/surfaces.yaml';

const WEB_MARKERS = [
  'react', 'vue', 'next', 'nuxt', 'svelte', '@angular', 'astro',
  'vite', 'webpack', 'remix', 'solid-js', 'qwik', '@sveltejs',
];

// Backend directory names — skip these even if they have web deps (e.g., vite as bundler)
const BACKEND_DIR_NAMES = new Set(['api', 'server', 'backend', 'worker', 'workers', 'functions', 'lambda']);

function hasWebDeps(dir) {
  const pkgPath = join(dir, 'package.json');
  if (!existsSync(pkgPath)) return false;
  try {
    const pkg = JSON.parse(readFileSync(pkgPath, 'utf-8'));
    const deps = { ...pkg.dependencies, ...pkg.devDependencies };
    // Must have a UI framework, not just a bundler
    const UI_FRAMEWORKS = ['react', 'vue', 'next', 'nuxt', 'svelte', '@angular', 'astro', 'solid-js', 'qwik', '@sveltejs'];
    const hasBundlerOnly = WEB_MARKERS.some(m => Object.keys(deps).some(d => d.startsWith(m)));
    const hasUIFramework = UI_FRAMEWORKS.some(m => Object.keys(deps).some(d => d.startsWith(m)));
    // If only bundler (vite, webpack) without UI framework, not a web surface
    return hasUIFramework || (hasBundlerOnly && hasRoutesDir(dir));
  } catch { return false; }
}

function hasPlaywrightConfig(dir) {
  return existsSync(join(dir, 'playwright.config.ts')) ||
    existsSync(join(dir, 'playwright.config.js'));
}

function hasRoutesDir(dir) {
  // Only check routes dirs that indicate a frontend (pages, app routes)
  // Exclude src/routes alone — could be backend API routes (Hono, Express)
  const frontendRouteCandidates = ['app/routes', 'src/pages', 'pages', 'src/app/routes'];
  if (frontendRouteCandidates.some(c => existsSync(join(dir, c)))) return true;

  // src/routes is ambiguous — check for .tsx/.jsx files (frontend) vs .ts/.js only (backend)
  const srcRoutes = join(dir, 'src', 'routes');
  if (existsSync(srcRoutes)) {
    try {
      const files = readdirSync(srcRoutes);
      return files.some(f => f.endsWith('.tsx') || f.endsWith('.jsx') || f.endsWith('.vue'));
    } catch { return false; }
  }
  return false;
}

function detectTestDir(dir) {
  const candidates = [
    join(dir, 'tests', 'e2e'),
    join(dir, 'tests', 'visual'),
    join(dir, 'test', 'e2e'),
  ];
  for (const c of candidates) {
    if (existsSync(c)) return c;
  }
  return join(dir, 'tests', 'e2e');
}

function findPlaywrightConfig(dir) {
  const tsPath = join(dir, 'playwright.config.ts');
  if (existsSync(tsPath)) return tsPath;
  const jsPath = join(dir, 'playwright.config.js');
  if (existsSync(jsPath)) return jsPath;
  return null;
}

function detectSurfaces() {
  const surfaces = [];

  // Priority 1: Check apps/* directories
  if (existsSync('apps')) {
    try {
      const appDirs = readdirSync('apps', { withFileTypes: true })
        .filter(d => d.isDirectory())
        .map(d => d.name);

      for (const appDir of appDirs) {
        const appPath = join('apps', appDir);
        const isWeb = hasWebDeps(appPath) || hasRoutesDir(appPath);
        const isNative = !isWeb && (
          existsSync(join(appPath, 'ios')) ||
          existsSync(join(appPath, 'android')) ||
          existsSync(join(appPath, 'Info.plist')) ||
          existsSync(join(appPath, 'Package.swift'))
        );

        if (isWeb) {
          const config = findPlaywrightConfig(appPath);
          surfaces.push({
            id: appDir,
            name: appDir.charAt(0).toUpperCase() + appDir.slice(1),
            path: appPath,
            testDir: detectTestDir(appPath),
            runner: 'playwright',
            runnerConfig: config,
          });
        } else if (isNative) {
          surfaces.push({
            id: appDir,
            name: appDir.charAt(0).toUpperCase() + appDir.slice(1),
            path: appPath,
            testDir: detectTestDir(appPath),
            runner: 'manual',
          });
        }
      }
    } catch { /* continue */ }
  }

  // Priority 2: Check packages/* directories
  if (existsSync('packages') && surfaces.length === 0) {
    try {
      const pkgDirs = readdirSync('packages', { withFileTypes: true })
        .filter(d => d.isDirectory())
        .map(d => d.name);

      for (const pkgDir of pkgDirs) {
        const pkgPath = join('packages', pkgDir);
        if (hasWebDeps(pkgPath)) {
          const config = findPlaywrightConfig(pkgPath);
          surfaces.push({
            id: pkgDir,
            name: pkgDir.charAt(0).toUpperCase() + pkgDir.slice(1),
            path: pkgPath,
            testDir: detectTestDir(pkgPath),
            runner: 'playwright',
            runnerConfig: config,
          });
        }
      }
    } catch { /* continue */ }
  }

  // Priority 3: Check frontend/ directory (legacy convention)
  if (surfaces.length === 0 && existsSync('frontend')) {
    if (hasWebDeps('frontend') || hasRoutesDir('frontend')) {
      const config = findPlaywrightConfig('frontend');
      surfaces.push({
        id: 'frontend',
        name: 'Frontend',
        path: 'frontend',
        testDir: existsSync('frontend/tests/e2e') ? 'frontend/tests/e2e' : 'frontend/tests/e2e',
        runner: 'playwright',
        runnerConfig: config,
      });
    }
  }

  // Priority 4: Root-level web app
  if (surfaces.length === 0 && (hasWebDeps('.') || hasRoutesDir('.'))) {
    const testDir = existsSync('tests/e2e') ? 'tests/e2e' :
      existsSync('tests/visual') ? 'tests/visual' : 'tests/e2e';
    const config = findPlaywrightConfig('.');
    surfaces.push({
      id: 'default',
      name: 'Default',
      path: '.',
      testDir,
      runner: 'playwright',
      runnerConfig: config,
    });
  }

  return surfaces;
}

function toYaml(surfaces) {
  const lines = ['# Auto-generated by LiveSpec Migration v8', '# Edit to match your project structure', '', 'surfaces:'];

  for (const s of surfaces) {
    lines.push(`  - id: ${s.id}`);
    lines.push(`    name: ${s.name}`);
    lines.push(`    path: ${s.path}`);
    lines.push(`    testDir: ${s.testDir}`);
    lines.push(`    runner: ${s.runner}`);
    if (s.runnerConfig) {
      lines.push(`    runnerConfig: ${s.runnerConfig}`);
    }
  }

  return lines.join('\n') + '\n';
}

// ─── Main ──────────────────────────────────────────────────────────────────

const args = process.argv.slice(2);
const dryRun = args.includes('--dry-run');
const force = args.includes('--force');

if (existsSync(SURFACES_CONFIG) && !force) {
  console.log(`${SURFACES_CONFIG} already exists — skipping generation`);
  console.log('Use --force to overwrite');
  process.exit(0);
}

const surfaces = detectSurfaces();

if (surfaces.length === 0) {
  console.log('No UI surfaces detected — skipping surfaces.yaml generation');
  process.exit(0);
}

console.log(`Detected ${surfaces.length} surface(s):`);
for (const s of surfaces) {
  console.log(`  [${s.id}] ${s.name} (${s.runner}) → ${s.testDir}`);
}

if (dryRun) {
  console.log(`\n[DRY RUN] Would create ${SURFACES_CONFIG}:`);
  console.log(toYaml(surfaces));
  process.exit(0);
}

const yaml = toYaml(surfaces);
writeFileSync(SURFACES_CONFIG, yaml);
console.log(`\n✅ Created ${SURFACES_CONFIG}`);
