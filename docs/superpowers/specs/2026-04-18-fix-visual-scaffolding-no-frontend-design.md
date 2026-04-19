# Design Spec: Fix visual scaffolding generation for non-frontend projects

**Date:** 2026-04-18  
**Status:** Approved (auto-brainstorm)  
**Branch:** feature/legacy-test-merge

---

## Problem

Three independent code paths generate visual scaffolding files without checking if the target project has a web frontend:

1. `scripts/migrate-visual-tests.js --generate` → creates `playwright.visual.config.ts`
2. `migrations/4/migrate.md` GENERATE_FILE action → creates `docker-compose.visual.yml`
3. `.claude/commands/spec.test.md` Phase 4.5.2 → creates `docker-compose.visual.yml`

**Symptom:** Running `/spec.migrate` on LiveSpec (Python CLI, no web frontend) generates `docker-compose.visual.yml` and `playwright.visual.config.ts` — files that serve no purpose and pollute the repo.

---

## Root Cause

The script has two modes (`FRONTEND_MODE = true/false`) but no third case: "no visual layer at all." Legacy mode (`FRONTEND_MODE = false`) currently runs unconditionally even when the project has zero web frontend indicators.

---

## Solution

### 1. `scripts/migrate-visual-tests.js`

Add `detectWebFrontend()` at startup, unifying the existing mode flags with a new `package.json` web-deps check into a single `hasWebFrontend` boolean. Guard the `--generate`/`--dry-run` path with an early exit placed **after** `printScanTable` (user sees the scan before we explain the skip) but before `generateTests`.

**`detectWebFrontend()` function:**
```js
function detectWebFrontend() {
  // Existing frontend indicators (already computed at startup)
  if (hasFrontendE2E || hasFrontendConfig || hasPencilMockups) return true;
  // Known routes directories (already listed in ROUTES_DIRS)
  if (ROUTES_DIRS.some(d => existsSync(d))) return true;
  // package.json with web framework dependencies
  try {
    const pkg = JSON.parse(readFileSync('package.json', 'utf8'));
    const deps = { ...pkg.dependencies, ...pkg.devDependencies };
    const WEB_MARKERS = [
      'react', 'vue', 'next', 'nuxt', 'svelte', '@angular', 'astro',
      'vite', 'webpack', 'remix', 'solid-js', 'qwik', '@sveltejs',
    ];
    // Non-exhaustive — add markers as needed
    return WEB_MARKERS.some(m => Object.keys(deps).some(d => d.startsWith(m)));
  } catch { return false; }
}
const hasWebFrontend = detectWebFrontend();
```

**Guard placement** — in the `if (dryRun || generate)` block:
```js
if (dryRun || generate) {
  printScanTable(features);  // Always show scan (informational)

  if (!hasWebFrontend && !args.includes('--force')) {
    console.log('\nNo web frontend detected — visual scaffolding skipped.');
    console.log('Use --force to generate anyway (e.g. projects using Playwright without a JS framework).');
    if (generate) {
      // FR-006: always emit sentinel on --generate; use reason= to distinguish from "all covered"
      console.log('VISUAL_SCAFFOLD_RESULT: files=0 dirs=0 routes=0 reason=no-frontend');
    }
    process.exit(0);
  }

  generateTests(features, dryRun);
}
```

**Sentinel distinction:** The existing "all features already have tests" path emits `VISUAL_SCAFFOLD_RESULT: files=0 dirs=0 routes=0` (no `reason=`). The new early exit emits `reason=no-frontend` so downstream parsers can distinguish the two cases.

**`--force` flag:** Added to help output:
```
  node scripts/migrate-visual-tests.js --generate [--force]  # --force: bypass frontend detection
```

**`--scan` mode:** NOT gated — scan is read-only and informational. Always works.

---

### 2. `migrations/4/migrate.md`

Add the following block **immediately before the GENERATE_FILE section**:

```markdown
### FRONTEND CHECK (prerequisite for GENERATE_FILE)

Before creating `docker-compose.visual.yml`, check if the project has a web frontend layer:

Check for any of the following indicators:
- Directory exists: `frontend/tests/e2e/`, `frontend/`, or any of `src/app/routes`, `frontend/app/routes`, `app/routes`, `src/routes`, `src/pages`, `pages`
- File exists: `frontend/playwright.config.ts`, `playwright.config.ts`, `cypress.config.ts`, `.specs/design/screens/` (Pencil mockups)
- File `package.json` exists AND contains one of these in `dependencies` or `devDependencies`: `react`, `vue`, `next`, `nuxt`, `svelte`, `@angular`, `astro`, `vite`, `webpack`, `remix`, `solid-js`, `qwik`

If NONE of the above are found:
```
LOG: "No web frontend detected — docker-compose.visual.yml skipped."
SKIP the GENERATE_FILE action entirely.
```

If ANY indicator is found: proceed with GENERATE_FILE as documented below.
```

The agent instruction file is self-contained: no `--force` flag needed since the check is embedded in the migration prose and the agent can surface the skip in the migration report.

---

### 3. `.claude/commands/spec.test.md`

In Phase 4.5.2, before the docker-compose generation block, add the following **Prerequisites** section:

```markdown
**Prerequisites — frontend detection:** Before generating `docker-compose.visual.yml`, 
verify the project has a web frontend layer by checking for any of:
- Routes directory: `src/app/routes`, `app/routes`, `src/routes`, `src/pages`, `pages`, `frontend/app/routes`
- Config file: `frontend/playwright.config.ts`, `playwright.config.ts`, `cypress.config.ts`
- Pencil mockups: `.specs/design/screens/`
- `package.json` with a web framework dep: `react`, `vue`, `next`, `nuxt`, `svelte`, `@angular`, `astro`, `vite`, `webpack`, `remix`, `solid-js`

If no web frontend detected:
```
LOG: "No web frontend detected — docker-compose.visual.yml skipped."
SKIP docker-compose generation and continue to next step.
```
```

---

## Test Strategy

### Fixture `migrate-visual` update (compatibility fix)

**`tests/integration/fixtures/migrate-visual/package.json`** (new file):
```json
{ "dependencies": { "react": "^18.0.0" } }
```
**Required:** The new `hasWebFrontend` guard would cause the existing fixture (which has no package.json) to exit early, breaking all 5 `TestMigrateVisualGenerate` tests. Adding a minimal web dep prevents this regression. The fixture correctly simulates a React web project using LiveSpec for spec management.

### Fixture `migrate-visual-no-web` (new)

Copy of `migrate-visual` structure but:
- No `package.json`
- No routes directories
- No frontend config files

Simulates a CLI project like LiveSpec itself.

### New test class: `TestMigrateVisualNoWebProject`

```python
@pytest.fixture()
def fixture_no_web(tmp_path: Path) -> Path:
    """Copy the migrate-visual-no-web fixture to tmp_path for isolation."""
    src = FIXTURES / "migrate-visual-no-web"
    dst = tmp_path / "project"
    shutil.copytree(src, dst)
    return dst


@pytest.mark.level_3a
class TestMigrateVisualNoWebProject:
    """Guard: no visual scaffolding generated for projects without a web frontend."""

    def test_exits_zero(self, fixture_no_web: Path) -> None:
        result = _run_generate(fixture_no_web)
        assert result.returncode == 0

    def test_no_files_created(self, fixture_no_web: Path) -> None:
        _run_generate(fixture_no_web)
        assert not (fixture_no_web / "playwright.visual.config.ts").exists()
        assert not (fixture_no_web / "tests" / "visual").exists()

    def test_sentinel_emitted_with_no_frontend_reason(self, fixture_no_web: Path) -> None:
        """FR-006: sentinel must be emitted; reason=no-frontend distinguishes from 'all covered'."""
        result = _run_generate(fixture_no_web)
        assert "VISUAL_SCAFFOLD_RESULT: files=0 dirs=0 routes=0 reason=no-frontend" in result.stdout

    def test_skip_message_in_output(self, fixture_no_web: Path) -> None:
        result = _run_generate(fixture_no_web)
        assert "No web frontend detected" in result.stdout

    def test_force_flag_bypasses_guard(self, fixture_no_web: Path) -> None:
        result = subprocess.run(
            ["node", str(SCRIPT_PATH), "--generate", "--force"],
            cwd=str(fixture_no_web), capture_output=True, text=True, timeout=30,
            env=os.environ.copy(),
        )
        assert result.returncode == 0
        visual_dir = fixture_no_web / "tests" / "visual"
        assert visual_dir.exists(), "With --force, visual test dir should be created"
```

---

## Edge Cases

| Scenario | Expected |
|---|---|
| `package.json` with malformed JSON | `try/catch` → `false` → guard triggers |
| `package.json` with eslint/jest only | `false` → guard triggers |
| Routes dir present, no `package.json` (Go/Python web app) | `true` → proceeds |
| `hasFrontendE2E` true (already in legacy fixture) | `true` → proceeds |
| `--scan` on non-web project | No guard — informational only |
| `--dry-run` on non-web project | Guard triggers after scan table, no sentinel |
| `--force` on non-web project | Guard bypassed, normal generation |
| Existing "files=0 dirs=0 routes=0" sentinel (all covered) | Unchanged — no `reason=` field |
| New "no-frontend" early exit sentinel | Has `reason=no-frontend` field |

---

## Files Modified

| File | Change |
|---|---|
| `scripts/migrate-visual-tests.js` | Add `detectWebFrontend()` + guard after `printScanTable` in `--generate`/`--dry-run` |
| `migrations/4/migrate.md` | Add FRONTEND CHECK block before GENERATE_FILE |
| `.claude/commands/spec.test.md` | Add Prerequisites block before Phase 4.5.2 docker-compose generation |
| `tests/integration/fixtures/migrate-visual/package.json` | New — `{ "dependencies": { "react": "^18.0.0" } }` |
| `tests/integration/fixtures/migrate-visual-no-web/` | New fixture directory (CLI-only project) |
| `tests/integration/test_migrate_visual.py` | New `fixture_no_web` fixture + `TestMigrateVisualNoWebProject` class |
