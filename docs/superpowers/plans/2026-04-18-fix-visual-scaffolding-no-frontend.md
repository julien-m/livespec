# Fix Visual Scaffolding for Non-Frontend Projects — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent `migrate-visual-tests.js` from generating `playwright.visual.config.ts` and `docker-compose.visual.yml` when the target project has no web frontend layer.

**Architecture:** Add `detectWebFrontend()` to the JS script (guards the `--generate`/`--dry-run` path), patch the two agent-instruction files (`migrations/4/migrate.md` and `.claude/commands/spec.test.md`) with equivalent prose conditions, and add a new fixture + test class to cover the new behavior.

**Tech Stack:** Node.js (migrate-visual-tests.js), Python/pytest (integration tests), Markdown (agent instruction files)

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `scripts/migrate-visual-tests.js` | Modify | Add `detectWebFrontend()` + guard in `--generate`/`--dry-run` path |
| `migrations/4/migrate.md` | Modify | Add FRONTEND CHECK block before GENERATE_FILE action |
| `.claude/commands/spec.test.md` | Modify | Add Prerequisites block before Phase 4.5.2 docker-compose section |
| `tests/integration/fixtures/migrate-visual/package.json` | Create | Minimal `{ "dependencies": { "react": "^18.0.0" } }` — compatibility fix |
| `tests/integration/fixtures/migrate-visual-no-web/` | Create | New fixture — copy of migrate-visual structure WITHOUT package.json |
| `tests/integration/test_migrate_visual.py` | Modify | New `fixture_no_web` fixture + `TestMigrateVisualNoWebProject` class |

---

### Task 1: Create test fixtures

**Files:**
- Create: `tests/integration/fixtures/migrate-visual/package.json`
- Create: `tests/integration/fixtures/migrate-visual-no-web/.specs/livespec-version`
- Create: `tests/integration/fixtures/migrate-visual-no-web/.specs/features/001-auth-ui/spec.md`
- Create: `tests/integration/fixtures/migrate-visual-no-web/.specs/features/002-backend-only/spec.md`
- Create: `tests/integration/fixtures/migrate-visual-no-web/.specs/features/003-dashboard/spec.md`
- Create: `tests/integration/fixtures/migrate-visual-no-web/.specs/features/004-already-has-tests/spec.md`
- Create: `tests/integration/fixtures/migrate-visual-no-web/tests/visual/004-already-has-tests.spec.ts`

- [ ] **Step 1: Create the `migrate-visual-no-web` fixture FIRST (before adding package.json to migrate-visual)**

⚠️ Order matters: create no-web fixture BEFORE modifying migrate-visual, otherwise the cp in Step 3 would transfer the new package.json into the no-web fixture.

```bash
mkdir -p tests/integration/fixtures/migrate-visual-no-web/.specs/features/001-auth-ui
mkdir -p tests/integration/fixtures/migrate-visual-no-web/.specs/features/002-backend-only
mkdir -p tests/integration/fixtures/migrate-visual-no-web/.specs/features/003-dashboard
mkdir -p tests/integration/fixtures/migrate-visual-no-web/.specs/features/004-already-has-tests
mkdir -p tests/integration/fixtures/migrate-visual-no-web/tests/visual
```

- [ ] **Step 2: Populate the no-web fixture files**

Copy spec files from the existing fixture (no package.json yet in migrate-visual, so the cp is clean):

```bash
cp tests/integration/fixtures/migrate-visual/.specs/livespec-version \
   tests/integration/fixtures/migrate-visual-no-web/.specs/livespec-version

cp tests/integration/fixtures/migrate-visual/.specs/features/001-auth-ui/spec.md \
   tests/integration/fixtures/migrate-visual-no-web/.specs/features/001-auth-ui/spec.md

cp tests/integration/fixtures/migrate-visual/.specs/features/002-backend-only/spec.md \
   tests/integration/fixtures/migrate-visual-no-web/.specs/features/002-backend-only/spec.md

cp tests/integration/fixtures/migrate-visual/.specs/features/003-dashboard/spec.md \
   tests/integration/fixtures/migrate-visual-no-web/.specs/features/003-dashboard/spec.md

cp tests/integration/fixtures/migrate-visual/.specs/features/004-already-has-tests/spec.md \
   tests/integration/fixtures/migrate-visual-no-web/.specs/features/004-already-has-tests/spec.md

cp "tests/integration/fixtures/migrate-visual/tests/visual/004-already-has-tests.spec.ts" \
   "tests/integration/fixtures/migrate-visual-no-web/tests/visual/004-already-has-tests.spec.ts"
```

- [ ] **Step 3: Now add `package.json` to the existing `migrate-visual` fixture**

The new `hasWebFrontend` guard checks for `package.json` with web deps. The existing fixture has none, so adding it prevents a regression that would break all 5 `TestMigrateVisualGenerate` tests.

```bash
cat > tests/integration/fixtures/migrate-visual/package.json << 'EOF'
{ "dependencies": { "react": "^18.0.0" } }
EOF
```

- [ ] **Step 4: Verify fixture structure**

```bash
find tests/integration/fixtures/migrate-visual-no-web -type f | sort
find tests/integration/fixtures/migrate-visual -type f | sort
```

Expected — `migrate-visual-no-web` has all the same files as `migrate-visual` PLUS no `package.json`. `migrate-visual` now has `package.json`.

- [ ] **Step 5: Commit fixtures**

```bash
git add tests/integration/fixtures/migrate-visual/package.json \
        tests/integration/fixtures/migrate-visual-no-web/
git commit -m "test(fixtures): add package.json to migrate-visual; new migrate-visual-no-web fixture"
```

---

### Task 2: Write failing tests for no-frontend guard

**Files:**
- Modify: `tests/integration/test_migrate_visual.py`

- [ ] **Step 1: Add `fixture_no_web` and `TestMigrateVisualNoWebProject` to the test file**

Open `tests/integration/test_migrate_visual.py`. Add the following block **after** the `TestMigrateVisualLegacyMerge` class (at the end of the file):

```python
# ─────────────────────────────────────────────────────────────────────────────
# No-web-frontend guard tests

FIXTURE_MIGRATE_VISUAL_NO_WEB = FIXTURES / "migrate-visual-no-web"


@pytest.fixture()
def fixture_no_web(tmp_path: Path) -> Path:
    """Copy the migrate-visual-no-web fixture to tmp_path for isolation."""
    dst = tmp_path / "project"
    shutil.copytree(FIXTURE_MIGRATE_VISUAL_NO_WEB, dst)
    return dst


@pytest.mark.level_3a
class TestMigrateVisualNoWebProject:
    """Guard: no visual scaffolding generated for projects without a web frontend.

    A project without package.json (with web deps), frontend config files, or
    routes directories should skip all visual scaffold generation.
    """

    def test_exits_zero(self, fixture_no_web: Path) -> None:
        """--generate on a non-web project must exit 0 (valid state, not an error)."""
        result = _run_generate(fixture_no_web)
        assert result.returncode == 0, (
            f"Expected exit 0 for no-web project, got {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_no_playwright_config_created(self, fixture_no_web: Path) -> None:
        """No playwright.visual.config.ts must be created for non-web projects."""
        _run_generate(fixture_no_web)
        assert not (fixture_no_web / "playwright.visual.config.ts").exists(), (
            "playwright.visual.config.ts should NOT be generated for a non-web project"
        )

    def test_no_test_files_created(self, fixture_no_web: Path) -> None:
        """No visual test files (tests/visual/*.spec.ts) must be created."""
        _run_generate(fixture_no_web)
        visual_dir = fixture_no_web / "tests" / "visual"
        # The fixture has one pre-existing test for feature 004; count should not grow
        existing = {f.name for f in visual_dir.iterdir()} if visual_dir.exists() else set()
        assert "001-auth-ui.spec.ts" not in existing, (
            "Visual test for 001-auth-ui should NOT be generated for a non-web project"
        )
        assert "003-dashboard.spec.ts" not in existing, (
            "Visual test for 003-dashboard should NOT be generated for a non-web project"
        )

    def test_sentinel_emitted_with_no_frontend_reason(self, fixture_no_web: Path) -> None:
        """FR-006: sentinel must be emitted; reason=no-frontend distinguishes from 'all covered'."""
        result = _run_generate(fixture_no_web)
        expected = "VISUAL_SCAFFOLD_RESULT: files=0 dirs=0 routes=0 reason=no-frontend"
        assert expected in result.stdout, (
            f"Expected sentinel '{expected}' in stdout.\n"
            f"Got stdout: {result.stdout}"
        )

    def test_skip_message_in_output(self, fixture_no_web: Path) -> None:
        """User-facing message must explain why nothing was generated."""
        result = _run_generate(fixture_no_web)
        assert "No web frontend detected" in result.stdout, (
            f"Expected 'No web frontend detected' in stdout.\nGot: {result.stdout}"
        )

    def test_force_flag_bypasses_guard(self, fixture_no_web: Path) -> None:
        """--force overrides the guard and generates files as if a web frontend existed."""
        import os
        result = subprocess.run(
            ["node", str(SCRIPT_PATH), "--generate", "--force"],
            cwd=str(fixture_no_web),
            capture_output=True,
            text=True,
            timeout=30,
            env=os.environ.copy(),
        )
        assert result.returncode == 0, (
            f"Expected exit 0 with --force, got {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        # With --force and 2 UI features (001-auth-ui, 003-dashboard), visual dir must be created
        visual_dir = fixture_no_web / "tests" / "visual"
        assert visual_dir.exists(), (
            "tests/visual/ should be created when --force bypasses the guard"
        )
```

- [ ] **Step 2: Run the new tests to confirm they FAIL (guard not yet implemented)**

```bash
cd /Users/julienm/projects/livespec
python -m pytest tests/integration/test_migrate_visual.py::TestMigrateVisualNoWebProject -v 2>&1 | tail -30
```

Expected: ALL 6 tests FAIL — `test_sentinel_emitted_with_no_frontend_reason`, `test_skip_message_in_output` fail because the script currently generates files unconditionally; `test_no_playwright_config_created` and `test_no_test_files_created` fail because files ARE created.

- [ ] **Step 3: Also confirm existing tests still pass (they will fail too until we add package.json check)**

```bash
python -m pytest tests/integration/test_migrate_visual.py::TestMigrateVisualGenerate -v 2>&1 | tail -15
```

**Important:** These SHOULD still pass because `migrate-visual` fixture now has `package.json` with `react` dep (Task 1). If they fail, something is wrong with Task 1 — fix before continuing.

- [ ] **Step 4: Commit failing tests**

```bash
git add tests/integration/test_migrate_visual.py
git commit -m "test(011): add failing TestMigrateVisualNoWebProject — guard not yet implemented"
```

---

### Task 3: Implement `detectWebFrontend()` guard in migrate-visual-tests.js

**Files:**
- Modify: `scripts/migrate-visual-tests.js`

- [ ] **Step 1: Add `detectWebFrontend()` function and `hasWebFrontend` constant**

Open `scripts/migrate-visual-tests.js`. Find `const ROUTES_DIRS = [` (around line 48). Insert the following block **immediately after the closing `];` of the ROUTES_DIRS array** (around line 56), NOT at line 36.

⚠️ `detectWebFrontend()` references `ROUTES_DIRS` — inserting it before the `ROUTES_DIRS` declaration would cause `ReferenceError: Cannot access 'ROUTES_DIRS' before initialization`.

```js
// Project-level visual layer detection — guards --generate and --dry-run
// Returns true if the project has ANY indicator of a web frontend.
function detectWebFrontend() {
  // Already-computed frontend indicators (re-use startup variables)
  if (hasFrontendE2E || hasFrontendConfig || hasPencilMockups) return true;
  // Known routes directories (covers Next.js, Nuxt, Remix, SvelteKit, etc.)
  if (ROUTES_DIRS.some(d => existsSync(d))) return true;
  // package.json with web framework dependencies
  // Non-exhaustive — add markers as needed
  try {
    const pkg = JSON.parse(readFileSync('package.json', 'utf8'));
    const deps = { ...pkg.dependencies, ...pkg.devDependencies };
    const WEB_MARKERS = [
      'react', 'vue', 'next', 'nuxt', 'svelte', '@angular', 'astro',
      'vite', 'webpack', 'remix', 'solid-js', 'qwik', '@sveltejs',
    ];
    return WEB_MARKERS.some(m => Object.keys(deps).some(d => d.startsWith(m)));
  } catch { return false; }
}
const hasWebFrontend = detectWebFrontend();
```

Note: `hasFrontendConfig` = `existsSync(FRONTEND_CONFIG_PATH)` (line 31), `hasFrontendE2E` (line 30), `hasPencilMockups` (line 32) — all already defined before `ROUTES_DIRS`, so safe to reference inside the function.

- [ ] **Step 2: Add `--force` to the CLI help text**

Find the block starting with `if (!scan && !generate && !dryRun)` near the bottom of the file (around line 1403). Update the help text:

```js
if (!scan && !generate && !dryRun) {
  console.log('Usage:');
  console.log('  node scripts/migrate-visual-tests.js --scan           # List features without visual tests');
  console.log('  node scripts/migrate-visual-tests.js --generate       # Create test files for missing features');
  console.log('  node scripts/migrate-visual-tests.js --dry-run        # Preview without creating files (exit 0)');
  console.log('  node scripts/migrate-visual-tests.js --generate --force  # Bypass frontend detection');
  process.exit(1);
}
```

- [ ] **Step 3: Add the guard in the `if (dryRun || generate)` block**

Find the section near the bottom (around line 1418):
```js
if (dryRun || generate) {
  printScanTable(features);
  generateTests(features, dryRun);
}
```

Replace with:
```js
if (dryRun || generate) {
  printScanTable(features);

  if (!hasWebFrontend && !args.includes('--force')) {
    console.log('\nNo web frontend detected — visual scaffolding skipped.');
    console.log('Use --force to generate anyway (e.g. projects using Playwright without a JS framework).');
    if (generate) {
      // FR-006: always emit sentinel on --generate; reason= distinguishes from "all features covered"
      console.log('VISUAL_SCAFFOLD_RESULT: files=0 dirs=0 routes=0 reason=no-frontend');
    }
    process.exit(0);
  }

  generateTests(features, dryRun);
}
```

- [ ] **Step 4: Run the new tests — they should PASS now**

```bash
python -m pytest tests/integration/test_migrate_visual.py::TestMigrateVisualNoWebProject -v 2>&1 | tail -20
```

Expected: ALL 6 tests PASS.

- [ ] **Step 5: Run existing tests to verify no regression**

```bash
python -m pytest tests/integration/test_migrate_visual.py -v --tb=short 2>&1 | tail -30
```

Expected: All tests PASS. If any `TestMigrateVisualGenerate` test fails, the issue is likely the `migrate-visual` fixture lacks `package.json` — verify Task 1 Step 1 was applied correctly.

- [ ] **Step 6: Commit**

```bash
git add scripts/migrate-visual-tests.js
git commit -m "feat(011): add hasWebFrontend guard — skip visual scaffold for non-web projects"
```

---

### Task 4: Update migrations/4/migrate.md

**Files:**
- Modify: `migrations/4/migrate.md`

- [ ] **Step 1: Add FRONTEND CHECK block before GENERATE_FILE**

Open `migrations/4/migrate.md`. Find the line `### GENERATE_FILE`. Insert the following block **immediately before** it (with a blank line between):

```markdown
### FRONTEND CHECK (prerequisite for GENERATE_FILE)

Before creating `docker-compose.visual.yml`, check if the project has a web frontend layer.

Check for ANY of the following indicators:
- Directory exists: `frontend/tests/e2e/`, `frontend/`, or any of: `src/app/routes`, `frontend/app/routes`, `app/routes`, `src/routes`, `src/pages`, `pages`
- File exists: `frontend/playwright.config.ts`, `playwright.config.ts`, `cypress.config.ts`, `.specs/design/screens/` (Pencil mockup directory)
- File `package.json` exists AND `dependencies` or `devDependencies` contains any of: `react`, `vue`, `next`, `nuxt`, `svelte`, `@angular`, `astro`, `vite`, `webpack`, `remix`, `solid-js`, `qwik`

**If NONE of the above are found:**
```
LOG: "No web frontend detected — docker-compose.visual.yml skipped."
SKIP the GENERATE_FILE action entirely.
Proceed directly to SET_VERSION 4.
```

**If ANY indicator is found:** proceed with GENERATE_FILE as documented below.

```

- [ ] **Step 2: Verify the edit looks correct**

```bash
grep -A 5 "FRONTEND CHECK" migrations/4/migrate.md | head -10
grep -B 2 "### GENERATE_FILE" migrations/4/migrate.md | head -5
```

Expected: FRONTEND CHECK block appears, followed immediately by GENERATE_FILE.

- [ ] **Step 3: Commit**

```bash
git add migrations/4/migrate.md
git commit -m "fix(migration-v4): skip docker-compose.visual.yml for non-web projects"
```

---

### Task 5: Update spec.test.md Phase 4.5.2

**Files:**
- Modify: `.claude/commands/spec.test.md`

- [ ] **Step 1: Find the docker-compose generation section**

```bash
grep -n "docker-compose.visual.yml" .claude/commands/spec.test.md | head -10
```

Locate the line containing `` #### `docker-compose.visual.yml` generation `` (around line 510).

- [ ] **Step 2: Add Prerequisites block before the generation steps**

In `.claude/commands/spec.test.md`, find the section:
```markdown
#### `docker-compose.visual.yml` generation

On first run (or if `docker-compose.visual.yml` is absent in the target project):
1. Generate `docker-compose.visual.yml` with pinned Playwright Docker image
```

Insert the following **between** the section heading and "On first run":

```markdown
**Prerequisites — frontend detection:** Before generating `docker-compose.visual.yml`, verify the project has a web frontend layer by checking for any of:
- Routes directory: `src/app/routes`, `app/routes`, `src/routes`, `src/pages`, `pages`, `frontend/app/routes`, `frontend/tests/e2e/`
- Config file: `frontend/playwright.config.ts`, `playwright.config.ts`, `cypress.config.ts`
- Pencil mockups: `.specs/design/screens/`
- `package.json` with a web framework dep: `react`, `vue`, `next`, `nuxt`, `svelte`, `@angular`, `astro`, `vite`, `webpack`, `remix`, `solid-js`

If **no web frontend detected**:
```
LOG: "No web frontend detected — docker-compose.visual.yml skipped."
SKIP docker-compose generation and proceed to the next section.
```

```

- [ ] **Step 3: Verify the edit**

```bash
grep -A 20 'docker-compose.visual.yml. generation' .claude/commands/spec.test.md | head -25
```

Expected: Prerequisites block appears before "On first run".

- [ ] **Step 4: Commit**

```bash
git add .claude/commands/spec.test.md
git commit -m "fix(spec.test): skip docker-compose.visual.yml generation for non-web projects"
```

---

### Task 6: Final verification

- [ ] **Step 1: Run full integration test suite**

```bash
python -m pytest tests/integration/test_migrate_visual.py -v --tb=short 2>&1 | tail -40
```

Expected: All tests PASS including the 6 new `TestMigrateVisualNoWebProject` tests.

- [ ] **Step 2: Smoke test on LiveSpec itself (the original bug)**

```bash
# From the project root — LiveSpec has no package.json with web deps, no routes dirs
node scripts/migrate-visual-tests.js --generate 2>&1
```

Expected output includes:
```
No web frontend detected — visual scaffolding skipped.
Use --force to generate anyway ...
VISUAL_SCAFFOLD_RESULT: files=0 dirs=0 routes=0 reason=no-frontend
```

Expected: `docker-compose.visual.yml` and `playwright.visual.config.ts` are NOT created.

- [ ] **Step 3: Verify untracked files are still untracked (the bug files were pre-existing)**

```bash
git status
```

The two files `docker-compose.visual.yml` and `playwright.visual.config.ts` that existed before this fix remain untracked — this fix prevents future generation, not retroactive cleanup. The user should delete them manually.

- [ ] **Step 4: Final commit if any cleanup needed**

```bash
git add -p  # Stage only intentional changes
git commit -m "fix(011): prevent visual scaffolding on non-web projects — complete"
```

---

## Self-Review

**Spec coverage:**
- ✅ `scripts/migrate-visual-tests.js` guard → Task 3
- ✅ `migrations/4/migrate.md` GENERATE_FILE condition → Task 4
- ✅ `spec.test.md` Prerequisites → Task 5
- ✅ `migrate-visual/package.json` compatibility fix → Task 1
- ✅ `migrate-visual-no-web` fixture → Task 1
- ✅ `TestMigrateVisualNoWebProject` 6 tests → Task 2
- ✅ Sentinel `reason=no-frontend` → Task 3 Step 3
- ✅ `--force` bypass → Task 3 Steps 2+3
- ✅ `--scan` NOT gated → confirmed in Task 3 (guard only in `if (dryRun || generate)`)

**No placeholder check:** All steps have exact commands or file content. No TBDs.

**Type consistency:** `detectWebFrontend()` defined once in Task 3 Step 1, referenced nowhere else. No signature drift.
