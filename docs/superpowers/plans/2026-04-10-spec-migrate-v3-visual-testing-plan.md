# spec.migrate v3 — Visual Testing Infrastructure Migration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add migration v3 to LiveSpec so existing projects can retrofit the visual testing infrastructure (visual.ts helper, dirs, deps) by running `/spec.migrate`.

**Architecture:** Four deliverables — `templates/visual.ts` (deployable TypeScript helper), `scripts/scaffold-visual-testing.sh` (idempotent migration script with package manager detection), `migrations/3/migrate.md` (DSL definition), and a `VERSION` bump to 3. The migration scaffolds infrastructure only; baseline capture is deferred to the user running `/spec.test`.

**Tech Stack:** Bash 5+, TypeScript 5+, Playwright 1.40+, pixelmatch 5.x, sharp 0.33+

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `templates/visual.ts` | Create | Deployable TypeScript helper with `compareRegression`, `compareDesign`, `_pixelmatchDiff` |
| `scripts/scaffold-visual-testing.sh` | Create | Migration script — detect package manager, scaffold, install deps, self-validate |
| `migrations/3/migrate.md` | Create | DSL migration definition for v3 |
| `VERSION` | Modify | Bump 2 → 3 |

---

## Task 1: Create `templates/visual.ts`

**Files:**
- Create: `templates/visual.ts`

This file is the source of truth for the helper scaffold. It is copied as-is into `tests/e2e/helpers/visual.ts` in target projects.

- [ ] **Step 1: Create the templates/ directory and write `templates/visual.ts`**

```typescript
/**
 * Visual testing helper for LiveSpec projects.
 * Provides regression detection (vs baseline) and design fidelity (vs Pencil mockup).
 *
 * Usage:
 *   import { compareRegression, compareDesign } from './visual'
 *
 *   // Regression check (2% threshold) — use in spec.check flows
 *   await compareRegression(page, 'login-default', { threshold: 0.02 })
 *
 *   // Design fidelity (5% threshold) — use in spec.test Phase 4.5.3
 *   await compareDesign(page, '.specs/design/screens/login.png', { threshold: 0.05 })
 */

import { Page } from '@playwright/test'
import pixelmatch from 'pixelmatch'
import { PNG } from 'pngjs'
import * as fs from 'fs'
import * as path from 'path'
import sharp from 'sharp'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface IgnoreRegion {
  x: number
  y: number
  width: number
  height: number
}

export interface RegressionOptions {
  /** Pixel difference threshold (0.0–1.0). Default: 0.02 (2%) */
  threshold?: number
  /** If true, overwrites the baseline with the current screenshot. Default: false */
  updateBaseline?: boolean
}

export interface DesignOptions {
  /** Pixel difference threshold (0.0–1.0). Default: 0.05 (5%) */
  threshold?: number
  /** Regions to exclude from comparison (dynamic content, timestamps, avatars) */
  ignoreRegions?: IgnoreRegion[]
}

interface DiffResult {
  /** Mismatch percentage (0.0–1.0) */
  mismatch: number
  baselinePath: string
  diffPath: string
  actualPath: string
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Compare the current page screenshot against a stored baseline.
 * Baseline dir: .specs/features/<test-suite>/baselines/
 * Diff output:  test-results/visual-diffs/<testName>/
 *
 * Throws on mismatch > threshold with paths to diff images.
 */
export async function compareRegression(
  page: Page,
  testName: string,
  options: RegressionOptions = {}
): Promise<void> {
  const threshold = options.threshold ?? 0.02
  const updateBaseline = options.updateBaseline ?? false

  const baselineDir = path.join('.specs', 'features', _testSuiteName(), 'baselines')
  const baselinePath = path.join(baselineDir, `${testName}.png`)
  const diffDir = path.join('test-results', 'visual-diffs', testName)

  const actualBuffer = await page.screenshot({ fullPage: false })

  if (!fs.existsSync(baselinePath) || updateBaseline) {
    fs.mkdirSync(baselineDir, { recursive: true })
    fs.writeFileSync(baselinePath, actualBuffer)
    console.log(`[visual] Baseline saved: ${baselinePath}`)
    return
  }

  const result = await _pixelmatchDiff(actualBuffer, fs.readFileSync(baselinePath), {
    diffDir,
  })

  if (result.mismatch > threshold) {
    throw new Error(
      `[visual] Regression detected for "${testName}": ${(result.mismatch * 100).toFixed(2)}% diff (threshold: ${(threshold * 100).toFixed(2)}%)\n` +
      `  baseline: ${result.baselinePath}\n` +
      `  diff:     ${result.diffPath}\n` +
      `  actual:   ${result.actualPath}\n` +
      `Run with updateBaseline: true to accept the new appearance.`
    )
  }
}

/**
 * Compare the current page screenshot against a Pencil mockup PNG.
 * Mockup path: .specs/design/screens/<screen-name>.png
 * Diff output: test-results/visual-diffs/<testName>-design/
 *
 * Throws on mismatch > threshold with paths to diff images.
 * If mockupPath does not exist, logs a warning and skips (no error).
 */
export async function compareDesign(
  page: Page,
  mockupPath: string,
  options: DesignOptions = {}
): Promise<void> {
  const threshold = options.threshold ?? 0.05
  const ignoreRegions = options.ignoreRegions ?? []

  if (!fs.existsSync(mockupPath)) {
    console.warn(`[visual] Design fidelity skipped — mockup not found: ${mockupPath}`)
    return
  }

  const testName = path.basename(mockupPath, '.png') + '-design'
  const diffDir = path.join('test-results', 'visual-diffs', testName)

  const actualBuffer = await page.screenshot({ fullPage: false })
  const mockupBuffer = fs.readFileSync(mockupPath)

  const result = await _pixelmatchDiff(actualBuffer, mockupBuffer, {
    diffDir,
    ignoreRegions,
  })

  if (result.mismatch > threshold) {
    throw new Error(
      `[visual] Design divergence for "${testName}": ${(result.mismatch * 100).toFixed(2)}% diff (threshold: ${(threshold * 100).toFixed(2)}%)\n` +
      `  mockup:   ${mockupPath}\n` +
      `  diff:     ${result.diffPath}\n` +
      `  actual:   ${result.actualPath}\n` +
      `Review the design diff and either fix the implementation or update the mockup.`
    )
  }

  console.log(`[visual] Design fidelity OK for "${testName}": ${(result.mismatch * 100).toFixed(2)}% diff`)
}

// ---------------------------------------------------------------------------
// Internal
// ---------------------------------------------------------------------------

interface PixelmatchOptions {
  diffDir: string
  ignoreRegions?: IgnoreRegion[]
}

interface DiffResult {
  mismatch: number
  baselinePath: string
  diffPath: string
  actualPath: string
}

async function _pixelmatchDiff(
  actualBuffer: Buffer,
  expectedBuffer: Buffer,
  options: PixelmatchOptions
): Promise<DiffResult> {
  const { diffDir, ignoreRegions = [] } = options

  // Normalize both images to the same dimensions via sharp
  const [actualMeta, expectedMeta] = await Promise.all([
    sharp(actualBuffer).metadata(),
    sharp(expectedBuffer).metadata(),
  ])

  const width = Math.max(actualMeta.width ?? 0, expectedMeta.width ?? 0)
  const height = Math.max(actualMeta.height ?? 0, expectedMeta.height ?? 0)

  const [actualResized, expectedResized] = await Promise.all([
    sharp(actualBuffer).resize(width, height, { fit: 'contain', background: '#ffffff' }).png().toBuffer(),
    sharp(expectedBuffer).resize(width, height, { fit: 'contain', background: '#ffffff' }).png().toBuffer(),
  ])

  if (width === 0 || height === 0) {
    throw new Error('[visual] Could not compare images with zero width or height.')
  }

  const diffPng = new PNG({ width, height })

  fs.mkdirSync(diffDir, { recursive: true })
  const baselinePath = path.join(diffDir, 'baseline.png')
  const diffPath = path.join(diffDir, 'diff.png')
  const actualPath = path.join(diffDir, 'actual.png')

  fs.writeFileSync(actualPath, actualResized)
  fs.writeFileSync(baselinePath, expectedResized)

  const actualCmp = PNG.sync.read(actualResized)
  const expectedCmp = PNG.sync.read(expectedResized)

  if (ignoreRegions.length > 0) {
    _applyIgnoreRegions(actualCmp, expectedCmp, ignoreRegions)
  }

  const mismatchPixels = pixelmatch(
    actualCmp.data,
    expectedCmp.data,
    diffPng.data,
    width,
    height,
    { threshold: 0.1, includeAA: false }
  )

  const totalPixels = width * height
  const mismatch = totalPixels > 0 ? mismatchPixels / totalPixels : 0

  fs.writeFileSync(diffPath, PNG.sync.write(diffPng))

  return { mismatch, baselinePath, diffPath, actualPath }
}

function _applyIgnoreRegions(actual: PNG, expected: PNG, regions: IgnoreRegion[]): void {
  for (const region of regions) {
    const yEnd = Math.min(region.y + region.height, actual.height)
    const xEnd = Math.min(region.x + region.width, actual.width)
    for (let y = Math.max(0, region.y); y < yEnd; y++) {
      for (let x = Math.max(0, region.x); x < xEnd; x++) {
        const idx = (y * actual.width + x) * 4
        // Zero out alpha channel — pixelmatch treats transparent pixels as equal
        actual.data[idx + 3] = 0
        expected.data[idx + 3] = 0
      }
    }
  }
}

function _testSuiteName(): string {
  // Primary: use LIVESPEC_FEATURE env var (set by /spec.test or /spec.implement)
  if (process.env.LIVESPEC_FEATURE) {
    return process.env.LIVESPEC_FEATURE.replace(/[^a-z0-9-]/gi, '-').toLowerCase()
  }
  // Fallback: derive from the calling test file path via stack trace
  const stack = new Error().stack ?? ''
  const match = stack.match(/at .+ \((.+\.(?:spec|test)\.[jt]s):\d+:\d+\)/)
  if (match) {
    const filename = path.basename(match[1]).replace(/\.(?:spec|test)\.[jt]s$/, '')
    console.warn(`[visual] LIVESPEC_FEATURE not set — deriving suite name from test file: "${filename}". Set LIVESPEC_FEATURE=<feature-id> for accurate baseline routing.`)
    return filename.replace(/[^a-z0-9-]/gi, '-').toLowerCase()
  }
  console.warn('[visual] LIVESPEC_FEATURE not set and could not derive suite name from stack. Baselines will be stored under "unknown". Set LIVESPEC_FEATURE=<feature-id>.')
  return 'unknown'
}
```

- [ ] **Step 2: Verify the file was written correctly**

```bash
head -5 /Users/julienm/projects/livespec/templates/visual.ts
```
Expected: first line is the JSDoc comment `/**`

---

## Task 2: Create `scripts/scaffold-visual-testing.sh`

**Files:**
- Create: `scripts/scaffold-visual-testing.sh`

- [ ] **Step 1: Write the script**

```bash
#!/usr/bin/env bash
set -euo pipefail

# scaffold-visual-testing.sh — Copy visual.ts helper and install deps
#
# Usage: scaffold-visual-testing.sh <project-dir> <livespec-dir>
#
# Called by migrate.sh for migration v3.
# Idempotent: skips scaffold if visual.ts already exists (validates it instead).
# Self-validates before exit 0: visual.ts non-empty + deps in devDependencies.

PROJECT_DIR="${1:?Usage: scaffold-visual-testing.sh <project-dir> <livespec-dir>}"
LIVESPEC_DIR="${2:?Usage: scaffold-visual-testing.sh <project-dir> <livespec-dir>}"

PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
LIVESPEC_DIR="$(cd "$LIVESPEC_DIR" && pwd)"

TEMPLATE_SRC="$LIVESPEC_DIR/templates/visual.ts"
HELPER_DEST="$PROJECT_DIR/tests/e2e/helpers/visual.ts"
PKG_JSON="$PROJECT_DIR/package.json"

has_required_deps() {
  (
    cd "$PROJECT_DIR" &&
      node -e "const p=require('./package.json'); process.exit((p.devDependencies?.pixelmatch && p.devDependencies?.sharp) ? 0 : 1)" 2>/dev/null
  )
}

# --- Verify template exists ---

if [[ ! -f "$TEMPLATE_SRC" ]]; then
  echo "ERROR: Template not found: $TEMPLATE_SRC" >&2
  exit 1
fi

# --- Scaffold visual.ts ---

if [[ -f "$HELPER_DEST" ]]; then
  echo "  · tests/e2e/helpers/visual.ts already exists — validating"
  # Check all required symbols; overwrite with template if any are missing
  NEEDS_OVERWRITE=false
  for symbol in compareRegression compareDesign; do
    if ! grep -q "$symbol" "$HELPER_DEST"; then
      echo "  ! Missing '$symbol' in existing visual.ts — overwriting with template"
      NEEDS_OVERWRITE=true
      break
    fi
  done
  if [[ "$NEEDS_OVERWRITE" == true ]]; then
    cp "$TEMPLATE_SRC" "$HELPER_DEST"
    echo "  ✓ tests/e2e/helpers/visual.ts updated from template"
  fi
else
  mkdir -p "$(dirname "$HELPER_DEST")"
  cp "$TEMPLATE_SRC" "$HELPER_DEST"
  echo "  ✓ Scaffolded tests/e2e/helpers/visual.ts"
fi

# Final validation: non-empty + required symbols present
if [[ ! -s "$HELPER_DEST" ]]; then
  echo "ERROR: tests/e2e/helpers/visual.ts is empty after scaffold" >&2
  exit 1
fi
for symbol in compareRegression compareDesign; do
  if ! grep -q "$symbol" "$HELPER_DEST"; then
    echo "ERROR: tests/e2e/helpers/visual.ts missing export '$symbol'" >&2
    exit 1
  fi
done
echo "  ✓ tests/e2e/helpers/visual.ts validated"

# --- Handle missing package.json ---

if [[ ! -f "$PKG_JSON" ]]; then
  echo "  ! No package.json found — skipping dep install"
  echo "  ! Install manually: npm install -D $DEPS"
  # File-only mode: visual.ts is in place; exit 0 (VERSION will be bumped)
  exit 0
fi

# --- Detect package manager ---

PKG_MANAGER="unknown"
if [[ -f "$PROJECT_DIR/bun.lockb" ]] || [[ -f "$PROJECT_DIR/bun.lock" ]]; then
  PKG_MANAGER="bun"
elif [[ -f "$PROJECT_DIR/package-lock.json" ]]; then
  PKG_MANAGER="npm"
elif [[ -f "$PROJECT_DIR/yarn.lock" ]]; then
  PKG_MANAGER="yarn"
elif [[ -f "$PROJECT_DIR/pnpm-lock.yaml" ]]; then
  PKG_MANAGER="pnpm"
fi

# --- Install deps or warn ---

DEPS="pixelmatch pngjs sharp @types/pixelmatch @types/pngjs"

case "$PKG_MANAGER" in
  bun)
    if has_required_deps; then
      echo "  ✓ Deps found in devDependencies — skipping install"
    else
      echo "  ▸ Installing deps via bun..."
      (cd "$PROJECT_DIR" && bun add -d $DEPS)
      echo "  ✓ Deps installed via bun"
    fi
    ;;
  npm)
    if has_required_deps; then
      echo "  ✓ Deps found in devDependencies — skipping install"
    else
      echo "  ▸ Installing deps via npm..."
      (cd "$PROJECT_DIR" && npm install -D $DEPS)
      echo "  ✓ Deps installed via npm"
    fi
    ;;
  yarn|pnpm)
    # Check if deps were already installed manually before warning
    if has_required_deps; then
      echo "  ✓ Deps found in devDependencies — skipping install"
    else
      echo "  ! Package manager: $PKG_MANAGER — automatic install not supported"
      echo "  ! Install manually:"
      echo "    $PKG_MANAGER add -D $DEPS"
      echo "  ! Then re-run /spec.migrate to complete v3."
      exit 1
    fi
    ;;
  *)
    # No lock file detected: check if deps already present
    if has_required_deps; then
      echo "  ✓ Deps found in devDependencies — skipping install"
    else
      echo "  ! No package manager lock file found"
      echo "  ! Install manually:"
      echo "    npm install -D $DEPS"
      echo "  ! Then re-run /spec.migrate to complete v3."
      exit 1
    fi
    ;;
esac

# --- Exit criteria validation ---

# Check pixelmatch in devDependencies (run from PROJECT_DIR for relative require)
if ! (cd "$PROJECT_DIR" && node -e "const p=require('./package.json'); process.exit(p.devDependencies?.pixelmatch ? 0 : 1)" 2>/dev/null); then
  echo "ERROR: pixelmatch not found in devDependencies after install" >&2
  exit 1
fi
echo "  ✓ pixelmatch in devDependencies"

# Check sharp in devDependencies
if ! (cd "$PROJECT_DIR" && node -e "const p=require('./package.json'); process.exit(p.devDependencies?.sharp ? 0 : 1)" 2>/dev/null); then
  echo "ERROR: sharp not found in devDependencies after install" >&2
  exit 1
fi
echo "  ✓ sharp in devDependencies"

echo ""
echo "  Visual testing infrastructure ready."
echo "  Next: run /spec.test to capture visual baselines for your existing features."
echo ""

exit 0
```

- [ ] **Step 2: Make the script executable**

```bash
chmod +x /Users/julienm/projects/livespec/scripts/scaffold-visual-testing.sh
```

- [ ] **Step 3: Verify the file is executable**

```bash
ls -la /Users/julienm/projects/livespec/scripts/scaffold-visual-testing.sh
```
Expected: `-rwxr-xr-x` (or similar with x bits set)

---

## Task 3: Create `migrations/3/migrate.md`

**Files:**
- Create: `migrations/3/migrate.md`

Pattern: follow `migrations/2/migrate.md` exactly.

- [ ] **Step 1: Create the migrations/3/ directory and write migrate.md**

```markdown
---
version: 3
description: "Retrofit visual testing infrastructure into existing projects"
date: 2026-04-10
---

# Migration v3: Visual Testing Infrastructure

Scaffolds visual testing helpers, creates required directories, installs
pixelmatch and sharp, and adds root-level test-results output to .gitignore.

After migration, run /spec.test to capture visual baselines for existing features.

## Actions

MKDIR tests/e2e/helpers
MKDIR .specs/design/screens
RUN scaffold-visual-testing.sh
GITIGNORE test-results/
SET_VERSION 3
```

- [ ] **Step 2: Verify the file was created**

```bash
cat /Users/julienm/projects/livespec/migrations/3/migrate.md
```
Expected: frontmatter with `version: 3` and the DSL actions block.

---

## Task 4: Bump VERSION

**Files:**
- Modify: `VERSION`

- [ ] **Step 1: Update VERSION from 2 to 3**

Write `3` to `/Users/julienm/projects/livespec/VERSION`.

- [ ] **Step 2: Verify**

```bash
cat /Users/julienm/projects/livespec/VERSION
```
Expected: `3`

---

## Task 5: Integration Test

**Files:**
- No new test file required — test manually against a mock project directory

Verify the full migration works end-to-end using a temp project with a package.json.

- [ ] **Step 1: Create a mock project directory**

```bash
MOCK_DIR="$(mktemp -d)"
mkdir -p "$MOCK_DIR/.specs"
echo "2" > "$MOCK_DIR/.specs/livespec-version"
cat > "$MOCK_DIR/package.json" <<'EOF'
{
  "name": "mock-project",
  "devDependencies": {
    "@playwright/test": "^1.40.0"
  }
}
EOF
touch "$MOCK_DIR/package-lock.json"
echo "Mock project created at: $MOCK_DIR"
```

- [ ] **Step 2: Run migrate.sh with the v3 migration**

```bash
LIVESPEC_DIR="/Users/julienm/projects/livespec"
bash "$LIVESPEC_DIR/scripts/migrate.sh" \
  "$LIVESPEC_DIR/migrations/3/migrate.md" \
  "$MOCK_DIR" \
  "$LIVESPEC_DIR"
```

Expected output includes:
```
  ✓ MKDIR tests/e2e/helpers
  ✓ MKDIR .specs/design/screens
  ▸ RUN scaffold-visual-testing.sh
  ✓ Scaffolded tests/e2e/helpers/visual.ts
  ✓ tests/e2e/helpers/visual.ts validated
  ▸ Installing deps via npm...
  ✓ Deps installed via npm
  ✓ pixelmatch in devDependencies
  ✓ sharp in devDependencies
  Visual testing infrastructure ready.
  ✓ RUN scaffold-visual-testing.sh complete
  ✓ GITIGNORE test-results/
  ✓ SET_VERSION 3
```

- [ ] **Step 3: Verify exit criteria**

```bash
# visual.ts exists and is non-empty
[[ -s "$MOCK_DIR/tests/e2e/helpers/visual.ts" ]] && echo "PASS: visual.ts exists" || echo "FAIL: visual.ts missing"

# compareRegression present
grep -q "compareRegression" "$MOCK_DIR/tests/e2e/helpers/visual.ts" && echo "PASS: compareRegression present" || echo "FAIL: compareRegression missing"

# compareDesign present
grep -q "compareDesign" "$MOCK_DIR/tests/e2e/helpers/visual.ts" && echo "PASS: compareDesign present" || echo "FAIL: compareDesign missing"

# .specs/design/screens exists
[[ -d "$MOCK_DIR/.specs/design/screens" ]] && echo "PASS: design/screens dir exists" || echo "FAIL: design/screens missing"

# .gitignore has root-level test-results entry
grep -q "test-results/" "$MOCK_DIR/.gitignore" && echo "PASS: gitignore entry present" || echo "FAIL: gitignore entry missing"

# pixelmatch in devDependencies
(cd "$MOCK_DIR" && node -e "const p=require('./package.json'); process.exit(p.devDependencies?.pixelmatch ? 0 : 1)" 2>/dev/null) && echo "PASS: pixelmatch in devDeps" || echo "FAIL: pixelmatch missing"

# sharp in devDependencies
(cd "$MOCK_DIR" && node -e "const p=require('./package.json'); process.exit(p.devDependencies?.sharp ? 0 : 1)" 2>/dev/null) && echo "PASS: sharp in devDeps" || echo "FAIL: sharp missing"

# version was bumped to 3
[[ "$(cat "$MOCK_DIR/.specs/livespec-version")" == "3" ]] && echo "PASS: version = 3" || echo "FAIL: version is $(cat "$MOCK_DIR/.specs/livespec-version")"
```

- [ ] **Step 4: Clean up**

```bash
rm -rf "$MOCK_DIR"
```

---

## Task 6: Commit

- [ ] **Step 1: Stage all new files**

```bash
git add \
  /Users/julienm/projects/livespec/templates/visual.ts \
  /Users/julienm/projects/livespec/scripts/scaffold-visual-testing.sh \
  /Users/julienm/projects/livespec/migrations/3/migrate.md \
  /Users/julienm/projects/livespec/VERSION \
  /Users/julienm/projects/livespec/docs/superpowers/specs/2026-04-10-spec-migrate-v3-visual-testing-design.md \
  /Users/julienm/projects/livespec/docs/superpowers/plans/2026-04-10-spec-migrate-v3-visual-testing-plan.md
```

- [ ] **Step 2: Commit via git.commit skill (do not use git commit directly)**

Commit message hint: `feat(migrate): add v3 migration to retrofit visual testing infrastructure`

---

## Self-Review

### Spec Coverage

| Spec Requirement | Task |
|---|---|
| `templates/visual.ts` with `compareRegression`, `compareDesign`, `_pixelmatchDiff` | Task 1 |
| `scripts/scaffold-visual-testing.sh` idempotent, self-validating | Task 2 |
| `migrations/3/migrate.md` DSL definition | Task 3 |
| `VERSION` bumped to 3 | Task 4 |
| Integration test | Task 5 |
| Exit criteria: visual.ts non-empty + pixelmatch + sharp in devDeps | Task 2 Step 1 (validation block) |
| Idempotency: skip if exists, still validate; skip dep install when already declared | Task 2 Step 1 |
| Non-reversible documented | In migration description |
| yarn/pnpm: warn + exit 1 (no VERSION bump) | Task 2 Step 1 |
| Post-migration output message | Task 2 Step 1 |
| root-level GITIGNORE entry | Task 3 (full path `test-results/`) |

All spec requirements are covered.

### Placeholder Scan

No TBD, TODO, or placeholder text found. All code blocks are complete.

### Type Consistency

- `compareRegression(page, testName, options)` — consistent across Task 1 and spec
- `compareDesign(page, mockupPath, options)` — consistent
- `IgnoreRegion`, `RegressionOptions`, `DesignOptions` — defined once in Task 1, no re-use conflicts
- `_pixelmatchDiff` is internal (prefixed `_`), not exported
