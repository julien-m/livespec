#!/usr/bin/env node
// Surface resolver — shared module for multi-surface test generation.
// Reads .specs/surfaces.yaml if present (FATAL on errors), falls back to filesystem detection.
//
// Usage as module:
//   import { resolveSurfaces, getPlaywrightSurfaces } from './lib/surface-resolver.js';
//
// Usage as self-test:
//   node scripts/lib/surface-resolver.js

import { existsSync, readdirSync, readFileSync } from 'fs';
import { join, relative, resolve } from 'path';

const SURFACES_CONFIG = '.specs/surfaces.yaml';
const PENCIL_MOCKUP_DIR = '.specs/design/screens';

const WEB_MARKERS = [
  'react', 'vue', 'next', 'nuxt', 'svelte', '@angular', 'astro',
  'vite', 'webpack', 'remix', 'solid-js', 'qwik', '@sveltejs',
];

const ROUTES_DIR_CANDIDATES = [
  'app/routes',
  'src/app/routes',
  'src/routes',
  'src/pages',
  'pages',
];

// ─── YAML parser (minimal, no dependency) ──────────────────────────────────
// Handles the flat list-of-objects structure of surfaces.yaml only.

function parseSimpleYaml(content) {
  const surfaces = [];
  let current = null;

  for (const rawLine of content.split('\n')) {
    const line = rawLine.trimEnd();

    // Skip comments and empty lines
    if (/^\s*#/.test(line) || /^\s*$/.test(line)) continue;

    // Skip the top-level key (surfaces:)
    if (/^surfaces:\s*$/.test(line)) continue;

    // New list item: "  - key: value"
    const itemMatch = line.match(/^\s*-\s+(\w+):\s*(.*)$/);
    if (itemMatch) {
      if (current) surfaces.push(current);
      current = {};
      current[itemMatch[1]] = itemMatch[2].replace(/^["']|["']$/g, '').trim();
      continue;
    }

    // Continuation: "    key: value"
    const kvMatch = line.match(/^\s+(\w+):\s*(.*)$/);
    if (kvMatch && current) {
      current[kvMatch[1]] = kvMatch[2].replace(/^["']|["']$/g, '').trim();
      continue;
    }
  }

  if (current) surfaces.push(current);
  return surfaces;
}

// ─── Validation ────────────────────────────────────────────────────────────

function validateSurfaces(surfaces, filePath) {
  const errors = [];

  if (!Array.isArray(surfaces) || surfaces.length === 0) {
    errors.push(`${filePath}: no surfaces defined`);
    return errors;
  }

  const ids = new Set();
  const testDirs = new Set();

  for (const s of surfaces) {
    if (!s.id) {
      errors.push(`Surface missing required field 'id'`);
      continue;
    }

    // Duplicate id
    if (ids.has(s.id)) {
      errors.push(`Duplicate surface id: '${s.id}'`);
    }
    ids.add(s.id);

    // Duplicate testDir
    if (s.testDir) {
      if (testDirs.has(s.testDir)) {
        errors.push(`Duplicate testDir: '${s.testDir}' (surface '${s.id}')`);
      }
      testDirs.add(s.testDir);
    }

    // runner is required
    if (!s.runner) {
      errors.push(`Surface '${s.id}': missing required field 'runner'`);
    }

    // path existence (warning, not error)
    if (s.path && !existsSync(s.path)) {
      console.warn(`WARNING: Surface '${s.id}': path '${s.path}' does not exist on disk`);
    }

    // runnerConfig existence (warning, not error)
    if (s.runnerConfig && !existsSync(s.runnerConfig)) {
      console.warn(`WARNING: Surface '${s.id}': runnerConfig '${s.runnerConfig}' does not exist`);
    }
  }

  return errors;
}

// ─── Config-based resolution ───────────────────────────────────────────────

function resolveFromConfig() {
  const raw = readFileSync(SURFACES_CONFIG, 'utf-8');
  let surfaces;

  try {
    surfaces = parseSimpleYaml(raw);
  } catch (e) {
    console.error(`FATAL: Failed to parse ${SURFACES_CONFIG}: ${e.message}`);
    process.exit(1);
  }

  const errors = validateSurfaces(surfaces, SURFACES_CONFIG);
  if (errors.length > 0) {
    console.error(`FATAL: ${SURFACES_CONFIG} validation failed:`);
    for (const err of errors) console.error(`  - ${err}`);
    process.exit(1);
  }

  // Enrich each surface with runtime detection
  return surfaces.map(s => enrichSurface(s));
}

// ─── Filesystem-based detection (legacy fallback) ──────────────────────────

const UI_FRAMEWORKS = [
  'react', 'vue', 'next', 'nuxt', 'svelte', '@angular', 'astro',
  'solid-js', 'qwik', '@sveltejs', 'remix',
];

function detectWebAppInDir(dir) {
  const pkgPath = join(dir, 'package.json');
  if (!existsSync(pkgPath)) return false;

  try {
    const pkg = JSON.parse(readFileSync(pkgPath, 'utf-8'));
    const deps = { ...pkg.dependencies, ...pkg.devDependencies };
    // Must have a UI framework, not just a bundler (vite/webpack alone is not enough)
    const hasUIFramework = UI_FRAMEWORKS.some(m => Object.keys(deps).some(d => d.startsWith(m)));
    if (hasUIFramework) return true;
    // Bundler + routes directory = likely web frontend
    const hasBundler = WEB_MARKERS.some(m => Object.keys(deps).some(d => d.startsWith(m)));
    return hasBundler && findRoutesDir(dir) !== null;
  } catch {
    return false;
  }
}

function findRoutesDir(basePath) {
  for (const candidate of ROUTES_DIR_CANDIDATES) {
    const full = join(basePath, candidate);
    if (existsSync(full)) return full;
  }
  // Also check root-level candidates
  if (basePath !== '.') {
    for (const candidate of ROUTES_DIR_CANDIDATES) {
      if (existsSync(candidate)) return candidate;
    }
  }
  return null;
}

function detectTestDirForPath(basePath) {
  const candidates = [
    join(basePath, 'tests', 'e2e'),
    join(basePath, 'tests', 'visual'),
    join(basePath, 'test', 'e2e'),
  ];
  for (const c of candidates) {
    if (existsSync(c)) return c;
  }
  // Default: create under basePath
  return join(basePath, 'tests', 'e2e');
}

function resolveFromFilesystem() {
  const surfaces = [];

  // Priority 1: Check if frontend/tests/e2e/ exists (legacy LiveSpec convention)
  if (existsSync('frontend/tests/e2e')) {
    surfaces.push(enrichSurface({
      id: 'default',
      name: 'Frontend',
      path: 'frontend',
      testDir: 'frontend/tests/e2e',
      runner: 'playwright',
    }));
    return surfaces;
  }

  // Priority 2: Scan apps/* for web apps
  if (existsSync('apps')) {
    try {
      const appDirs = readdirSync('apps', { withFileTypes: true })
        .filter(d => d.isDirectory())
        .map(d => d.name);

      for (const appDir of appDirs) {
        const appPath = join('apps', appDir);
        if (detectWebAppInDir(appPath)) {
          surfaces.push(enrichSurface({
            id: appDir,
            name: appDir,
            path: appPath,
            testDir: detectTestDirForPath(appPath),
            runner: 'playwright',
          }));
        }
      }

      if (surfaces.length > 0) return surfaces;
    } catch { /* continue to next fallback */ }
  }

  // Priority 3: Scan packages/* for web apps
  if (existsSync('packages')) {
    try {
      const pkgDirs = readdirSync('packages', { withFileTypes: true })
        .filter(d => d.isDirectory())
        .map(d => d.name);

      for (const pkgDir of pkgDirs) {
        const pkgPath = join('packages', pkgDir);
        if (detectWebAppInDir(pkgPath)) {
          surfaces.push(enrichSurface({
            id: pkgDir,
            name: pkgDir,
            path: pkgPath,
            testDir: detectTestDirForPath(pkgPath),
            runner: 'playwright',
          }));
        }
      }

      if (surfaces.length > 0) return surfaces;
    } catch { /* continue to next fallback */ }
  }

  // Priority 4: Check root-level web app indicators
  if (detectWebAppInDir('.') || existsSync('src/routes') || existsSync('src/pages') || existsSync('pages')) {
    const testDir = existsSync('tests/e2e') ? 'tests/e2e' : 'tests/visual';
    surfaces.push(enrichSurface({
      id: 'default',
      name: 'Default',
      path: '.',
      testDir,
      runner: 'playwright',
    }));
    return surfaces;
  }

  // No web frontend detected
  return [];
}

// ─── Surface enrichment ────────────────────────────────────────────────────

function enrichSurface(surface) {
  const basePath = surface.path || '.';

  return {
    id: surface.id,
    name: surface.name || surface.id,
    path: basePath,
    testDir: surface.testDir || join(basePath, 'tests', 'e2e'),
    runner: surface.runner || 'playwright',
    runnerConfig: surface.runnerConfig || null,
    // Derived properties for script compatibility
    frontendMode: basePath !== '.' && basePath !== 'tests/visual',
    routesDir: findRoutesDir(basePath),
    hasPencilMockups: existsSync(PENCIL_MOCKUP_DIR) &&
      readdirSync(PENCIL_MOCKUP_DIR).some(f => f.toLowerCase().endsWith('.png')),
  };
}

// ─── Public API ────────────────────────────────────────────────────────────

export function resolveSurfaces() {
  if (existsSync(SURFACES_CONFIG)) {
    return resolveFromConfig();
  }
  return resolveFromFilesystem();
}

export function getPlaywrightSurfaces() {
  return resolveSurfaces().filter(s => s.runner === 'playwright');
}

export function hasAnySurface() {
  return resolveSurfaces().length > 0;
}

// ─── Self-test (when run directly) ─────────────────────────────────────────

const isDirectRun = process.argv[1] && resolve(process.argv[1]) === resolve(new URL(import.meta.url).pathname);

if (isDirectRun) {
  console.log('Surface resolver — self-test\n');

  const configExists = existsSync(SURFACES_CONFIG);
  console.log(`Config file: ${SURFACES_CONFIG} → ${configExists ? 'FOUND' : 'not found (using filesystem detection)'}`);

  const surfaces = resolveSurfaces();
  console.log(`\nDetected ${surfaces.length} surface(s):\n`);

  for (const s of surfaces) {
    console.log(`  [${s.id}] ${s.name}`);
    console.log(`    path:       ${s.path}`);
    console.log(`    testDir:    ${s.testDir}`);
    console.log(`    runner:     ${s.runner}`);
    console.log(`    frontendMode: ${s.frontendMode}`);
    console.log(`    routesDir:  ${s.routesDir || '(none)'}`);
    console.log(`    pencilMode: ${s.hasPencilMockups}`);
    if (s.runnerConfig) console.log(`    runnerConfig: ${s.runnerConfig}`);
    console.log('');
  }

  const playwright = getPlaywrightSurfaces();
  console.log(`Playwright surfaces: ${playwright.length}`);
}
