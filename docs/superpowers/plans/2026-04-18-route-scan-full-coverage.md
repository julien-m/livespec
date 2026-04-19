# Route Scan + Full Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Étendre `migrate-visual-tests.js` pour scanner `frontend/app/routes/` en plus de `.specs/features/`, générer des tests `route-*.spec.ts` pour toutes les pages non couvertes, et supprimer automatiquement les vieux tests non-numérotés.

**Architecture:** Deux phases dans `--generate`: (1) spec-driven comme avant, (2) route-scan qui détecte les routes non couvertes, génère des tests `route-` préfixés, puis supprime les anciens. Nouveau préfixe `route-` distingue clairement les deux types.

**Tech Stack:** Node.js ESM, `fs` (existsSync, readFileSync, writeFileSync, rmSync), Python pytest pour les tests d'intégration.

---

## File Map

| Fichier | Action | Description |
|---------|--------|-------------|
| `scripts/migrate-visual-tests.js` | Modify | +8 fonctions, modifier `generateTests()`, nouvelle constante |
| `tests/integration/test_migrate_visual.py` | Modify | +tests pour route scan, deleteSuperseded |
| `tests/integration/fixtures/migrate-visual-frontend/` | Create | Nouveau fixture dédié au mode frontend + route scan |

> **Note:** On crée un NOUVEAU fixture `migrate-visual-frontend` séparé, pour ne pas activer `FRONTEND_MODE=true` sur les 8 tests existants qui utilisent `migrate-visual` en mode legacy.

---

## Task 1: Fixture de test — créer migrate-visual-frontend

**Files:**
- Create: `tests/integration/fixtures/migrate-visual-frontend/.specs/features/001-auth-ui/spec.md`
- Create: `tests/integration/fixtures/migrate-visual-frontend/frontend/app/routes/settings.tsx`
- Create: `tests/integration/fixtures/migrate-visual-frontend/frontend/app/routes/profile.tsx`
- Create: `tests/integration/fixtures/migrate-visual-frontend/frontend/app/routes/__root.tsx`
- Create: `tests/integration/fixtures/migrate-visual-frontend/frontend/tests/e2e/.gitkeep`

- [ ] **Step 1: Créer la spec feature minimale (pour que scanFeatures() ne quitte pas en erreur)**

Fichier: `tests/integration/fixtures/migrate-visual-frontend/.specs/features/001-auth-ui/spec.md`

```markdown
---
title: "Authentication"
---

# Feature: Authentication

Route: `/login`

## Acceptance Criteria

| AC-001 | User can log in with email and password |
```

- [ ] **Step 2: Créer `settings.tsx` avec h1 statique**

Fichier: `tests/integration/fixtures/migrate-visual-frontend/frontend/app/routes/settings.tsx`

```tsx
export const Route = { path: '/settings' };

export default function SettingsPage() {
  return (
    <div>
      <h1>Settings</h1>
    </div>
  );
}
```

- [ ] **Step 3: Créer `profile.tsx` — redirect-only (doit être ignoré)**

Fichier: `tests/integration/fixtures/migrate-visual-frontend/frontend/app/routes/profile.tsx`

```tsx
import { redirect } from 'some-router';

export const Route = { path: '/profile' };

export default function ProfilePage() {
  redirect('/login');
  return null;
}
```

- [ ] **Step 4: Créer `__root.tsx` avec notFoundComponent**

Fichier: `tests/integration/fixtures/migrate-visual-frontend/frontend/app/routes/__root.tsx`

```tsx
function NotFoundPage() {
  return <h1>Not Found</h1>;
}

export const rootRoute = {
  notFoundComponent: NotFoundPage,
};
```

- [ ] **Step 5: Créer le `.gitkeep` pour l'e2e dir**

Fichier: `tests/integration/fixtures/migrate-visual-frontend/frontend/tests/e2e/.gitkeep`

```
```

- [ ] **Step 6: Commit**

```bash
git add tests/integration/fixtures/migrate-visual-frontend/
git commit -m "test(fixtures): add migrate-visual-frontend fixture for route-scan tests"
```

---

## Task 2: Nouvelles fonctions utilitaires dans migrate-visual-tests.js

**Files:**
- Modify: `scripts/migrate-visual-tests.js`

- [ ] **Step 1: Ajouter la constante `ROUTES_DIRS` après les constantes existantes (après `const FRONTEND_MODE = ...`)**

```javascript
// Candidate routes directories — detected at startup (ordered by specificity)
const ROUTES_DIRS = [
  'frontend/app/routes',
  'src/app/routes',
  'app/routes',
  'src/routes',
  'src/pages',
  'pages',
];
```

- [ ] **Step 2: Ajouter les 4 fonctions utilitaires après `analyzeExistingTests`**

```javascript
// Returns true if the file is a redirect-only file (no visual content)
function isRedirectOnlyFile(content) {
  const hasRedirect = /\bredirect\s*\(/.test(content);
  const hasVisualContent = /<h[1-6][^>]*>[^<{]/.test(content) || /return\s*\([\s\S]*?<[A-Za-z]/.test(content);
  return hasRedirect && !hasVisualContent;
}

// Extract heading from route file JSX — best effort, fallback to capitalized slug
function extractHeadingFromRouteFile(content, slug) {
  const match = content.match(/<h[12][^>]*>\s*([A-Za-z][^<{}\n]{1,60}?)\s*<\/h[12]>/);
  if (match) return match[1].trim();
  return slug
    .split('-')
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

// Auto-detect the routes directory from ROUTES_DIRS
function detectRoutesDir() {
  return ROUTES_DIRS.find(d => existsSync(d)) || null;
}

// Build a Set of routes already covered by numbered spec-driven tests
function buildCoveredRoutes(features) {
  const covered = new Set();
  for (const feature of features) {
    const specPath = join(SPECS_DIR, feature.dir, 'spec.md');
    if (existsSync(specPath)) {
      const specContent = readFileSync(specPath, 'utf-8');
      const ctx = parseSpecContext(specContent, '');
      if (ctx.route) covered.add(ctx.route);
    }
    // Also add heuristic route from slug as fallback
    const heuristicRoute = inferRouteFromFeature(feature.slug, '');
    covered.add(heuristicRoute);
  }
  return covered;
}
```

- [ ] **Step 3: Vérifier syntaxe**

```bash
node --check scripts/migrate-visual-tests.js
# Attendu: aucune sortie (pas d'erreur de syntaxe)
```

- [ ] **Step 4: Commit**

```bash
git add scripts/migrate-visual-tests.js
git commit -m "feat(migrate): add route scan utility functions"
```

---

## Task 3: `scanRouteFiles` et `detectNotFoundFromRoot`

**Files:**
- Modify: `scripts/migrate-visual-tests.js` (après les fonctions de Task 2)

- [ ] **Step 1: Ajouter `scanRouteFiles` après `buildCoveredRoutes`**

```javascript
// Scan routesDir for pages without spec coverage
// Returns array of route-feature objects for test generation
function scanRouteFiles(routesDir, coveredRoutes, analysis) {
  if (!routesDir || !existsSync(routesDir)) return [];

  const SKIP_FILES = new Set(['__root.tsx', '__root.jsx', '__root.vue']);
  const ROUTE_EXTS = ['.tsx', '.jsx', '.vue', '.ts', '.js'];

  const files = readdirSync(routesDir).filter(f => {
    if (SKIP_FILES.has(f)) return false;
    if (f.startsWith('_')) return false;
    if (!ROUTE_EXTS.some(ext => f.endsWith(ext))) return false;
    return true;
  });

  const results = [];
  for (const file of files) {
    const slug = file.replace(/\.(tsx|jsx|vue|ts|js)$/, '');
    const route = slug === 'index' ? '/' : `/${slug}`;

    // Skip if already covered by a numbered spec test
    if (coveredRoutes.has(route)) continue;

    const filePath = join(routesDir, file);
    const content = readFileSync(filePath, 'utf-8');

    // Skip redirect-only files
    if (isRedirectOnlyFile(content)) continue;

    const heading = extractHeadingFromRouteFile(content, slug);
    const testPath = join(TEST_DIR, `route-${slug}.spec.ts`);

    results.push({ slug, route, heading, testPath, isRouteScan: true });
  }
  return results;
}

// Detect 404 page from __root.tsx notFoundComponent
function detectNotFoundFromRoot(routesDir) {
  if (!routesDir) return null;

  // Resolve which file actually exists
  const rootTsx = join(routesDir, '__root.tsx');
  const rootJsx = join(routesDir, '__root.jsx');
  const rootPath = existsSync(rootTsx) ? rootTsx : existsSync(rootJsx) ? rootJsx : null;
  if (!rootPath) return null;

  const content = readFileSync(rootPath, 'utf-8');
  if (!content.includes('notFoundComponent')) return null;

  return {
    slug: 'not-found',
    route: '/nonexistent-page-404',
    heading: 'Not Found',
    testPath: join(TEST_DIR, 'route-not-found.spec.ts'),
    isRouteScan: true,
  };
}
```

- [ ] **Step 2: Vérifier syntaxe**

```bash
node --check scripts/migrate-visual-tests.js
```

- [ ] **Step 3: Commit**

```bash
git add scripts/migrate-visual-tests.js
git commit -m "feat(migrate): add scanRouteFiles and detectNotFoundFromRoot"
```

---

## Task 4: `generateRouteTest`, `deleteSupersededTests`, et modifier `generateE2ETemplate`

**Files:**
- Modify: `scripts/migrate-visual-tests.js`

- [ ] **Step 1: Modifier la signature de `generateE2ETemplate` pour accepter un `externalSpecCtx` optionnel**

Changer la signature de:
```javascript
function generateE2ETemplate(feature, analysis = {}) {
```
En:
```javascript
function generateE2ETemplate(feature, analysis = {}, externalSpecCtx = null) {
```

Et remplacer cette ligne dans le corps:
```javascript
const specCtx = parseSpecContext(specContent, implPath);
```
Par:
```javascript
const specCtx = externalSpecCtx || parseSpecContext(specContent, implPath);
```

> Note: `title` est toujours extrait de `specContent` pour les commentaires dans le template — ce code reste inchangé. Seul `specCtx` (heading, route, acRows) peut venir de l'extérieur.

- [ ] **Step 2: Ajouter `generateRouteTest` après `generateE2ETemplate`**

```javascript
// Generate a test file for a route-scan feature (no spec context, 4 base tests only)
function generateRouteTest(routeFeature, analysis = {}, dryRun = false) {
  const { slug, route, heading, testPath } = routeFeature;

  if (dryRun) {
    console.log(`  [WOULD CREATE/UPDATE] ${testPath} (route scan: ${route})`);
    return;
  }

  mkdirSync(TEST_DIR, { recursive: true });

  const syntheticFeature = { dir: slug, slug, specPath: '' };
  // externalSpecCtx: heading + route from route file scan, no AC extras
  const specCtx = { heading, route, acRows: [] };
  const content = generateE2ETemplate(syntheticFeature, analysis, specCtx);
  writeFileSync(testPath, content);
  console.log(`  [CREATED/UPDATED] ${testPath} (route: ${route})`);
}
```

- [ ] **Step 3: Ajouter `deleteSupersededTests` après `generateRouteTest`**

```javascript
// Delete old non-numbered, non-route-prefixed tests whose route is now covered
function deleteSupersededTests(allCoveredRoutes, dryRun) {
  if (!existsSync(TEST_DIR)) return 0;

  const files = readdirSync(TEST_DIR).filter(f => f.endsWith('.spec.ts'));
  const superseded = files.filter(f => {
    // Keep numbered tests (NNN-*)
    if (/^\d{3}-/.test(f)) return false;
    // Keep route-scan tests (route-*)
    if (f.startsWith('route-')) return false;

    // Infer route from filename slug
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
      rmSync(filePath);
      console.log(`  🗑  Deleted ${f} (route ${route} now covered)`);
      removed++;
    }
  }
  return removed;
}
```

- [ ] **Step 4: Vérifier syntaxe**

```bash
node --check scripts/migrate-visual-tests.js
```

- [ ] **Step 5: Commit**

```bash
git add scripts/migrate-visual-tests.js
git commit -m "feat(migrate): add generateRouteTest and deleteSupersededTests"
```

---

## Task 5: Intégrer dans `generateTests()`

**Files:**
- Modify: `scripts/migrate-visual-tests.js` — fonction `generateTests`

- [ ] **Step 1: Modifier `generateTests` — déclarer les compteurs et les variables route-scan AVANT le guard early-exit**

Dans `generateTests(features, dryRun)`, remplacer le début actuel par:

```javascript
function generateTests(features, dryRun) {
  const toGenerate = features.filter(f => f.hasUI && !f.hasTests);

  // Analyze existing tests once (reused by both spec-driven and route-scan)
  const analysis = FRONTEND_MODE ? analyzeExistingTests(TEST_DIR) : {};

  // Build covered routes from all spec-driven features
  const specCoveredRoutes = FRONTEND_MODE ? buildCoveredRoutes(features) : new Set();

  // Scan route files for uncovered pages
  const routesDir = FRONTEND_MODE ? detectRoutesDir() : null;
  if (FRONTEND_MODE && !routesDir) {
    console.log('[route-scan] No routes directory found — skipping route scan.');
  }
  const routeScanFeatures = routesDir
    ? scanRouteFiles(routesDir, specCoveredRoutes, analysis)
    : [];

  // Detect 404 page
  const notFoundFeature = routesDir ? detectNotFoundFromRoot(routesDir) : null;
  if (notFoundFeature && !specCoveredRoutes.has(notFoundFeature.route)) {
    routeScanFeatures.push(notFoundFeature);
  }

  // Early-exit only if NOTHING to generate (spec-driven AND route-scan)
  const totalToGenerate = toGenerate.length + routeScanFeatures.length;

  if (totalToGenerate === 0) {
    console.log('All UI features already have visual tests. Nothing to generate.');
    if (!dryRun) {
      console.log('\nChecking infrastructure:');
      ensurePlaywrightConfig(false);
      ensurePackageJsonScripts(false);
      console.log('VISUAL_SCAFFOLD_RESULT: files=0 dirs=0 routes=0');
    }
    process.exit(0);
  }

  console.log(`\n${dryRun ? '[DRY RUN] Would generate' : 'Generating'} ${toGenerate.length} spec test(s) + ${routeScanFeatures.length} route test(s):\n`);

  let generated = 0;
  let skipped = 0;
  let dirsCreated = 0;
  let routeGenerated = 0;
  const featureList = [];

  if (!dryRun && FRONTEND_MODE) {
    console.log('🔍 Detected frontend/tests/e2e/ — using Pencil mockup mode');
    console.log('🧹 Cleaning up old migration artifacts...');
    cleanupOldMigration(false);
    mkdirSync(FRONTEND_E2E_DIR, { recursive: true });
  }

  // Phase 1: Spec-driven tests (AC-030: never overwrite numbered tests)
  for (const feature of toGenerate) {
    const testContent = generateTestTemplate(feature, analysis);

    if (dryRun) {
      console.log(`  [WOULD CREATE] ${feature.testPath}`);
      if (!FRONTEND_MODE) {
        for (const dir of BASELINE_DIRS_LEGACY) {
          console.log(`  [WOULD CREATE DIR] baselines/${dir}/${feature.slug}/`);
        }
      }
    } else {
      // @spec AC-030: Hard guard — never overwrite existing numbered tests
      if (existsSync(feature.testPath)) {
        console.log(`  [SKIP] ${feature.testPath} already exists (preserved)`);
        skipped++;
        continue;
      }
      mkdirSync(TEST_DIR, { recursive: true });
      writeFileSync(feature.testPath, testContent);
      console.log(`  [CREATED] ${feature.testPath}`);
      featureList.push(basename(feature.testPath));
      if (!FRONTEND_MODE) {
        for (const dir of BASELINE_DIRS_LEGACY) {
          const baselineDir = join('baselines', dir, feature.slug);
          mkdirSync(baselineDir, { recursive: true });
          const gitkeep = join(baselineDir, '.gitkeep');
          if (!existsSync(gitkeep)) writeFileSync(gitkeep, '');
          dirsCreated++;
        }
        console.log(`  [CREATED DIRS] baselines/{${BASELINE_DIRS_LEGACY.join(',')}}/${feature.slug}/`);
      }
      generated++;
    }
  }

  // Phase 2: Route-scan tests (always overwrite — scaffold)
  if (routeScanFeatures.length > 0) {
    console.log(`\n🔍 Route scan (${routeScanFeatures.length} uncovered page(s)):`);
    for (const routeFeature of routeScanFeatures) {
      generateRouteTest(routeFeature, analysis, dryRun);
      if (!dryRun) routeGenerated++;
    }
  }

  // Phase 3: Build full covered routes set (spec + route-scan) for deletion check
  const allCoveredRoutes = new Set([...specCoveredRoutes]);
  for (const rf of routeScanFeatures) allCoveredRoutes.add(rf.route);

  // Phase 4: Delete superseded old tests
  deleteSupersededTests(allCoveredRoutes, dryRun);

  if (!dryRun) {
    console.log('\nChecking infrastructure:');
    const configUpdated = ensurePlaywrightConfig(false);
    const scriptsAdded = ensurePackageJsonScripts(false);

    printCompletionReport({ generated, skipped, configUpdated, scriptsAdded, featureList, routeGenerated });

    // @spec FR-006: Structured sentinel line (includes routes= for route-scan count)
    console.log(`VISUAL_SCAFFOLD_RESULT: files=${generated} dirs=${dirsCreated} routes=${routeGenerated}`);
  } else {
    console.log('\n[DRY RUN] Infrastructure:');
    ensurePlaywrightConfig(true);
    ensurePackageJsonScripts(true);
    cleanupOldMigration(true);
  }

  process.exit(0);
}
```

- [ ] **Step 2: Mettre à jour `printCompletionReport` pour accepter et afficher `routeGenerated`**

Dans la section FRONTEND_MODE de `printCompletionReport`, ajouter après le log des fichiers:

```javascript
if (routeGenerated > 0) {
  console.log(`  - ${routeGenerated} route-scan test(s) generated (route-*.spec.ts)`);
}
```

- [ ] **Step 3: Vérifier syntaxe + dry-run**

```bash
node --check scripts/migrate-visual-tests.js
node scripts/migrate-visual-tests.js --dry-run 2>&1 | head -30
# Attendu: "No routes directory found" (livespec n'a pas de frontend/app/routes/)
```

- [ ] **Step 4: Commit**

```bash
git add scripts/migrate-visual-tests.js
git commit -m "feat(migrate): integrate route scan into --generate with auto-deletion"
```

---

## Task 6: Tests d'intégration Python

**Files:**
- Modify: `tests/integration/test_migrate_visual.py`

- [ ] **Step 1: Ajouter le fixture `fixture_migrate_visual_frontend` et le helper `_parse_sentinel_routes`**

Ajouter dans `tests/integration/test_migrate_visual.py`, après les helpers existants:

```python
FIXTURE_MIGRATE_VISUAL_FRONTEND = Path(__file__).parent / "fixtures" / "migrate-visual-frontend"


@pytest.fixture
def fixture_migrate_visual_frontend(tmp_path: Path) -> Path:
    """Frontend fixture with frontend/app/routes/ for route-scan tests."""
    import shutil
    dest = tmp_path / "migrate-visual-frontend"
    shutil.copytree(FIXTURE_MIGRATE_VISUAL_FRONTEND, dest)
    return dest


def _parse_sentinel_routes(stdout: str) -> tuple[int, int, int]:
    """Parse VISUAL_SCAFFOLD_RESULT: files=N dirs=M routes=R"""
    m = re.search(r"VISUAL_SCAFFOLD_RESULT: files=(\d+) dirs=(\d+) routes=(\d+)", stdout)
    if not m:
        return (-1, -1, -1)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
```

> Note: Le helper `_parse_sentinel` existant reste inchangé. Le nouveau `_parse_sentinel_routes` capture les 3 champs pour les nouveaux tests.

- [ ] **Step 2: Ajouter les classes de tests**

```python
@pytest.mark.level_3a
class TestMigrateVisualRouteScan:
    """Tests for route-scan functionality in migrate-visual-tests.js."""

    def test_generates_route_test_for_uncovered_page(self, fixture_migrate_visual_frontend: Path) -> None:
        """Route scan creates route-settings.spec.ts for settings.tsx not in any spec."""
        result = _run_generate(fixture_migrate_visual_frontend)
        assert result.returncode == 0, f"Script failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"

        e2e_dir = fixture_migrate_visual_frontend / "frontend" / "tests" / "e2e"
        route_test = e2e_dir / "route-settings.spec.ts"
        assert route_test.exists(), f"route-settings.spec.ts not generated. stdout:\n{result.stdout}"

    def test_route_test_uses_extracted_heading(self, fixture_migrate_visual_frontend: Path) -> None:
        """Route scan extracts h1 'Settings' from settings.tsx."""
        _run_generate(fixture_migrate_visual_frontend)
        content = (
            fixture_migrate_visual_frontend / "frontend" / "tests" / "e2e" / "route-settings.spec.ts"
        ).read_text()
        assert "HEADING = 'Settings'" in content, f"Heading not extracted correctly. Content:\n{content[:500]}"

    def test_skips_redirect_only_routes(self, fixture_migrate_visual_frontend: Path) -> None:
        """Profile page with redirect() and no h1 is not generated."""
        _run_generate(fixture_migrate_visual_frontend)
        e2e_dir = fixture_migrate_visual_frontend / "frontend" / "tests" / "e2e"
        assert not (e2e_dir / "route-profile.spec.ts").exists(), \
            "Redirect-only page should not get a route test"

    def test_generates_not_found_test_from_root(self, fixture_migrate_visual_frontend: Path) -> None:
        """notFoundComponent in __root.tsx produces route-not-found.spec.ts."""
        _run_generate(fixture_migrate_visual_frontend)
        e2e_dir = fixture_migrate_visual_frontend / "frontend" / "tests" / "e2e"
        assert (e2e_dir / "route-not-found.spec.ts").exists(), \
            "route-not-found.spec.ts not generated from __root.tsx"

    def test_route_test_overwrites_on_regenerate(self, fixture_migrate_visual_frontend: Path) -> None:
        """Running --generate twice overwrites route-* tests (no AC-030 protection)."""
        _run_generate(fixture_migrate_visual_frontend)
        route_test = (
            fixture_migrate_visual_frontend / "frontend" / "tests" / "e2e" / "route-settings.spec.ts"
        )
        original_mtime = route_test.stat().st_mtime

        import time
        time.sleep(0.1)
        _run_generate(fixture_migrate_visual_frontend)
        new_mtime = route_test.stat().st_mtime
        assert new_mtime > original_mtime, "route-settings.spec.ts was not overwritten on second run"

    def test_sentinel_includes_routes_count(self, fixture_migrate_visual_frontend: Path) -> None:
        """Sentinel line includes routes= count reflecting route-scan results."""
        result = _run_generate(fixture_migrate_visual_frontend)
        files, dirs, routes = _parse_sentinel_routes(result.stdout)
        assert routes >= 1, f"Sentinel routes= should be >= 1. stdout:\n{result.stdout}"


@pytest.mark.level_3a
class TestMigrateVisualDeleteSuperseded:
    """Tests for auto-deletion of superseded non-numbered tests."""

    def test_deletes_superseded_test_covered_by_route_scan(self, fixture_migrate_visual_frontend: Path) -> None:
        """Old settings.spec.ts is deleted after route-settings.spec.ts is generated."""
        e2e_dir = fixture_migrate_visual_frontend / "frontend" / "tests" / "e2e"
        e2e_dir.mkdir(parents=True, exist_ok=True)
        old_test = e2e_dir / "settings.spec.ts"
        old_test.write_text("// old hand-crafted test\n")

        _run_generate(fixture_migrate_visual_frontend)

        assert not old_test.exists(), \
            "settings.spec.ts should be deleted after route-settings.spec.ts covers /settings"
        assert (e2e_dir / "route-settings.spec.ts").exists(), \
            "route-settings.spec.ts should exist as replacement"

    def test_preserves_numbered_tests(self, fixture_migrate_visual_frontend: Path) -> None:
        """Numbered tests (001-*.spec.ts) are never deleted."""
        e2e_dir = fixture_migrate_visual_frontend / "frontend" / "tests" / "e2e"
        e2e_dir.mkdir(parents=True, exist_ok=True)
        numbered = e2e_dir / "001-auth-ui.spec.ts"
        numbered.write_text("// existing numbered test\n")

        _run_generate(fixture_migrate_visual_frontend)

        assert numbered.exists(), "Numbered test 001-auth-ui.spec.ts must not be deleted"

    def test_preserves_route_prefixed_tests_from_deletion(self, fixture_migrate_visual_frontend: Path) -> None:
        """route-* tests are never deleted by deleteSupersededTests."""
        e2e_dir = fixture_migrate_visual_frontend / "frontend" / "tests" / "e2e"
        e2e_dir.mkdir(parents=True, exist_ok=True)
        route_test = e2e_dir / "route-settings.spec.ts"
        route_test.write_text("// existing route test\n")

        _run_generate(fixture_migrate_visual_frontend)

        # File should still exist (overwritten, not deleted)
        assert route_test.exists(), "route-settings.spec.ts should not be deleted"
```

- [ ] **Step 3: Lancer les nouveaux tests seuls**

```bash
cd /Users/julienm/projects/livespec
python -m pytest tests/integration/test_migrate_visual.py::TestMigrateVisualRouteScan -v 2>&1 | tail -30
```

Attendu: PASS (ou failures clairs indiquant les gaps dans le JS).

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_migrate_visual.py tests/integration/fixtures/migrate-visual-frontend/
git commit -m "test(migrate): add route-scan and deleteSuperseded integration tests"
```

---

## Task 7: Lancer la suite complète et corriger

**Files:**
- Modify: `scripts/migrate-visual-tests.js` (corrections si nécessaire)

- [ ] **Step 1: Lancer tous les tests migrate_visual**

```bash
python -m pytest tests/integration/test_migrate_visual.py -v 2>&1 | tail -50
```

- [ ] **Step 2: Vérifier que les anciens tests ne sont pas cassés**

```bash
python -m pytest tests/integration/test_migrate_visual.py -v -k "not RouteScan and not DeleteSuperseded" 2>&1 | tail -20
# Attendu: même résultat qu'avant (aucune régression)
```

- [ ] **Step 3: Si échecs — diagnostiquer en lançant le script directement dans le fixture**

```bash
# Copier le fixture manuellement pour debug
cp -r tests/integration/fixtures/migrate-visual-frontend /tmp/debug-frontend
cd /tmp/debug-frontend
node /Users/julienm/projects/livespec/scripts/migrate-visual-tests.js --generate 2>&1
```

Points à vérifier si failures:
- `specCoveredRoutes` contient les bonnes routes (debug: ajouter `console.error([...specCoveredRoutes])` temporairement)
- `isRedirectOnlyFile` ne rejette pas des pages valides avec `return (` dans le JSX
- `deleteSupersededTests` ne supprime pas des tests non-couverts

- [ ] **Step 4: Lancer la suite complète (feature 010 méta-tests)**

```bash
cd /Users/julienm/projects/livespec
python -m pytest tests/ -v -k "not level_3b" 2>&1 | tail -20
```

- [ ] **Step 5: Commit final si corrections**

```bash
git add scripts/migrate-visual-tests.js
git commit -m "fix(migrate): correct route-scan edge cases from integration tests"
```

---

## Self-Review

**Spec coverage:**
- ✅ Route scan auto-détecté (`detectRoutesDir`)
- ✅ Filtrage redirect-only (`isRedirectOnlyFile`)
- ✅ Heading extraction (`extractHeadingFromRouteFile`)
- ✅ Couverture déduplication (`buildCoveredRoutes`)
- ✅ not-found depuis `__root.tsx` (`detectNotFoundFromRoot`) — bug jsx path corrigé
- ✅ Nommage `route-` préfixé (`scanRouteFiles`)
- ✅ Écraser les route-scan tests (`generateRouteTest`)
- ✅ Supprimer les anciens (`deleteSupersededTests`)
- ✅ Intégration dans `generateTests` — early-exit gate sur les deux
- ✅ Tests d'intégration Python complets avec fixture séparé
- ✅ Sentinel mis à jour avec `routes=`
- ✅ `_parse_sentinel` existant non cassé (helper séparé `_parse_sentinel_routes`)
- ✅ `node --check` au lieu de stdin redirect (syntaxe correcte)
- ✅ `routeGenerated` déclaré explicitement

**Codex APPROVED (iteration 2).**
