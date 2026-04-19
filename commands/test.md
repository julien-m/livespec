---
description: "Audit test coverage, generate missing tests, execute suite, verify visual fidelity"
argument-hint: "<feature-name>"
---

<!-- @spec FR-001: component-level snapshots, FR-002: reset-baselines workflow, FR-003: docker-compose gen, FR-004: human approval gate, FR-005: auto mode blocking, FR-006: maxDiffPixels threshold — .specs/features/003-visual-testing-fidelity/spec.md#fr-001 -->

# Command: /spec.test

> Post-implementation test validation — audit AC coverage, generate missing tests from Gherkin, execute the full suite, capture visual baselines, and produce a test report.

---

## Overview

```
/spec.test                        → Interactive feature selection → Phases 0-5
/spec.test feature-name           → Phases 0-5 for one feature
/spec.test --all                  → Phases 0-5 for all implemented features
/spec.test --audit-only           → Phase 0-1 only (coverage matrix, no generation/execution)
/spec.test --no-generate          → Phases 0, 1, 4-5 (execute existing tests, don't generate)
```

```mermaid
flowchart TD
    START(["/spec.test"]) --> RESOLVE["Phase 0\nResolve feature(s)\n+ preflight"]
    RESOLVE -->|"blocked"| BLOCKED(["Blocked —\nreport + recovery"])
    RESOLVE -->|"pass"| AUDIT["Phase 1 — Audit\nBuild coverage matrix\n(from check report or\nspec + implementation)"]
    AUDIT --> PLAN["Phase 2 — Plan\nList missing tests\n+ display summary"]
    PLAN --> AO{"--audit-only?"}
    AO -->|"yes"| REPORT
    AO -->|"no"| NG{"--no-generate?"}
    NG -->|"yes"| EXECUTE
    NG -->|"no"| GENERATE["Phase 3 — Generate\nCreate missing tests\nfrom Gherkin scenarios"]
    GENERATE --> EXECUTE["Phase 4 — Execute\nRun full test suite\n(unit + integration +\nE2E)"]
    EXECUTE --> VIS{"UI feature\n+ missing\nbaselines?"}
    VIS -->|"yes"| VISUAL["Phase 4.5 — Visual\nCapture missing baselines\n+ design fidelity"]
    VIS -->|"no"| REPORT
    VISUAL --> REPORT["Phase 5 — Report\nTest report + update\nimplementation.md"]
    REPORT --> SAVE["Save to\nchecks/YYYY-MM-DD-test.md"]
    SAVE --> MULTI{"Multiple\nfeatures?"}
    MULTI -->|"yes"| CONSOL["Consolidated\nreport"]
    MULTI -->|"no"| DONE(["Done"])
    CONSOL --> DONE

    style START fill:#e8f4f8,stroke:#2196F3
    style BLOCKED fill:#ffebee,stroke:#F44336
    style GENERATE fill:#fff3e0,stroke:#FF9800
    style EXECUTE fill:#fff3e0,stroke:#FF9800
    style DONE fill:#e8f5e9,stroke:#4CAF50
```

---

> **Hooks — before starting:** **Read** `before-test` hooks from all 3 levels (skip missing files):
> 1. `~/.claude/livespec/hooks/before-test.md`
> 2. `.specs/hooks/before-test.md`
> 3. `.specs/hooks/before-test.local.md` (if `mode: override` → use only this one)
>
> **Hooks — after completing:** Same resolution with `after-test` at all 3 levels.

## Relationship with other commands

| Command | Role | What it does with tests |
|---|---|---|
| `/spec.implement` | Creates code + tests during TDD | Runs EXISTING tests as validation gate. Does NOT audit coverage, does NOT generate missing tests |
| `/spec.test` | Post-implementation test validation | AUDITS coverage against AC, GENERATES missing tests from Gherkin, EXECUTES full suite, REPORTS |
| `/spec.check` | Static alignment verification | Verifies @spec anchors, FR→code mapping, runs visual regression on existing baselines |

`/spec.test` catches what `/spec.implement` misses: AC that have NO test at all, visual baselines that were skipped (`--no-visual`), and partial test coverage.

**Lifecycle placement:** `/spec.test` is typically run after `/spec.implement` (in `/spec.feature` Phase 3.5 or `/spec.ship` Step 3.5):
- **Before `/spec.check`** (most common): no check report exists — Phase 1 builds the coverage matrix from `spec.md` + `implementation.md` directly
- **After `/spec.check`** (optional): Phase 1 consumes the existing check report for faster audit

Both orders are valid. Choose based on whether you want to audit tests before or after verifying spec↔code alignment.

---

## Phase 0 — Resolve & Preflight

### Feature Resolution

Same pattern as `/spec.check`:

1. If feature name provided → find `.specs/features/NNN-feature-name/`
2. If no name → detect from current git branch (`feature/NNN-feature-name`)
3. If still no match → interactive selection (multi-spec, same as check.md Step 2):

```
| # | Feature              | Status      | Last Modified |
|---|----------------------|-------------|---------------|
| 1 | 004-notifications    | Implemented | 2026-03-12    |
| 2 | 001-user-auth        | Implemented | 2026-03-10    |

Selection: numbers (1,3), range (1-3), combined (1,3-5), or "all"
Enter = most recent feature only
```

4. If `--all` → all features with status `Implemented` or `In Progress`

### Preflight Checks (blocking)

- [ ] `.specs/` directory exists
- [ ] Feature directory exists with `spec.md`
- [ ] `spec.md` has AC section with at least 1 AC
- [ ] Resolved Test Commands available (in `plan.md` or `.specs/testing/strategy.md`)
- [ ] Test framework binary available (verify with `--version`)

**If no Resolved Test Commands:**
1. Attempt discovery via `system/testing/discovery.md` procedure
2. If discovery succeeds → write resolved commands to `.specs/testing/strategy.md` and continue
3. If discovery fails → report: "No test framework — cannot generate or execute tests. Run `/spec.plan` to resolve test commands." Exit with audit-only report.

**Non-testable features:**
- If all FR are infrastructure-only (no executable code) → report "Infrastructure feature — no executable tests" and skip
- If 0 AC map to testable behavior → report "0 testable AC" and skip to visual phase (if UI) or exit gracefully

---

## Phase 1 — Audit

**Goal:** Build a coverage matrix — what SHOULD be tested (from spec) vs what IS tested (from code).

### Data Sources (priority order)

1. **Latest check report** — scan `.specs/features/NNN/checks/` for most recent `YYYY-MM-DD.md` (not `-test.md`). If available, extract AC status (✅/⚠️/❌) and test file references. This avoids re-scanning.

2. **If no check report exists**, build the matrix from:
   - `spec.md` → extract all AC (with Gherkin scenarios) and FR
   - `implementation.md` → extract AC→test file mappings (Acceptance Criteria Mapping table)
   - Source files → grep `@spec FR-NNN` anchors for FR→file mappings

3. **If inside /spec.ship agent** (lean mode with `--auto`) → read `progress.md` from just-completed implementation for test results per step.

### Coverage Matrix

For each AC in `spec.md`:

1. **Check if a test exists** — look in `implementation.md` AC Mapping table, or grep test files for the AC identifier (`AC-NNN`)
2. **Check if a Gherkin scenario exists** — search `spec.md` for a ```gherkin block covering this AC
3. **Classify:**
   - ✅ **Covered** — test file exists, references this AC
   - ⚠️ **Partial** — test exists but doesn't cover all Gherkin steps
   - ❌ **Missing** — no test found for this AC
   - 🚫 **No Gherkin** — AC has no Gherkin scenario (cannot auto-generate)

### Behavioral Audit (sub-phase 1.5 — if `## Behavioral AC` present)

<!-- @spec FR-007: Parse Behavioral AC section, FR-008: Gap report — .specs/features/005-ui-behavioral-testing/spec.md#fr-007 -->

**Skipped if:** spec.md has no `## Behavioral AC` section (AC-011). No behavioral audit section appears in the report.

1. **Extract declared traits:** Parse the `## Behavioral AC` section of spec.md. Identify all trait names declared (e.g., `async_action`, `is_submittable`).

2. **Load required patterns:** For each declared trait, read the "Test patterns" table from `system/testing/ui-behavioral-taxonomy.md`. Extract the pattern keyword column (the grep-able string used to detect coverage).

3. **Scan test files:** For each pattern keyword, scan the feature's test files (from `implementation.md` AC Mapping or by discovering test files in the project):
   - grep for the pattern keyword in test file content
   - If found: trait + pattern is covered
   - If not found: gap detected

4. **Handle non-standard naming (EC-003):** If a test exists but uses a non-standard naming pattern that doesn't contain the taxonomy's keyword, report as gap with note: "Pattern keyword '[keyword]' not found — manual review required. Test may exist under a different name."

5. **Taxonomy missing (EC-005):** If `system/testing/ui-behavioral-taxonomy.md` does not exist but `## Behavioral AC` is present, skip behavioral audit with WARNING: "Behavioral taxonomy not found — behavioral audit skipped." (See taxonomy section 6 for asymmetry rationale.)

6. **Output — Behavioral Coverage Audit section:**

```markdown
### Behavioral Coverage Audit

| Trait | Required Pattern | Pattern Keyword | Status | Notes |
|-------|-----------------|-----------------|--------|-------|
| async_action | loading state | `loading-state` | Covered | tests/e2e/form.spec.ts:42 |
| async_action | double-click prevention | `double-click` | Gap | no test found |
| is_submittable | submit disabled when invalid | `submit-disabled` | Covered | tests/unit/form.test.ts:18 |

**Behavioral coverage:** 2/3 patterns covered (67%)
**Gaps:** 1 — async_action: double-click prevention not tested
  -> See taxonomy: system/testing/ui-behavioral-taxonomy.md#async_action

All behavioral traits covered  <-- (only shown if 0 gaps)
```

7. **Audit-only:** This sub-phase NEVER generates or modifies test files. It only reports gaps. (FR-008)

8. **Integration with Phase 5 Report:** Include the Behavioral Coverage Audit table in the test report saved to `checks/YYYY-MM-DD-test.md`.

### Visual Audit (UI features only)

If `spec.md` has a `## Screens` section:

For each referenced screen:
1. Check if a Playwright baseline exists in `baselines/`
2. Check if a visual test file exists (grep for `toHaveScreenshot` or screen name in test files)
3. Classify: ✅ Present / ❌ Missing baseline / ❌ Missing test file

### Output

```markdown
## Test Coverage Audit: NNN-feature-name

### AC Coverage

| AC | Description | Test file | Status | Gherkin? |
|---|---|---|---|---|
| AC-001 | Unread count badge | tests/api/notifications.test.ts | ✅ Covered | ✅ |
| AC-002 | Click marks read | tests/e2e/notifications.spec.ts | ✅ Covered | ✅ |
| AC-003 | Disable email notifs | tests/api/notifications.test.ts | ⚠️ Partial | ✅ |
| AC-004 | Immediate effect | — | ❌ Missing | ✅ |
| AC-005 | Mark all as read | — | ❌ Missing | ✅ |

**Coverage:** 2/5 fully covered (40%), 1 partial, 2 missing

### Visual Audit (if UI)

| Screen | Baseline | Test file | Status |
|---|---|---|---|
| login | ✅ baselines/login.png | ✅ tests/e2e/login.spec.ts | ✅ Complete |
| dashboard | ❌ Missing | ❌ Missing | ❌ Needs both |
```

---

## Phase 2 — Plan

Display what will be generated/executed before taking action:

```markdown
## Test Plan

### Tests to generate:

| # | AC | Type | Target file | From Gherkin |
|---|---|---|---|---|
| 1 | AC-004 | E2E | tests/e2e/notifications.spec.ts (append) | Scenario: "Preference change takes effect" |
| 2 | AC-005 | E2E | tests/e2e/notifications.spec.ts (append) | Scenario: "Mark all as read" |
| 3 | AC-003 | Unit | tests/api/notifications.test.ts (append) | Scenario: "Disable all email notifications" |

### Visual tests to generate:

| # | Screen | Target file | Action |
|---|---|---|---|
| 1 | dashboard | tests/e2e/dashboard.spec.ts (create) | New Playwright visual test |

### Suites to execute:
- Unit: [resolved unit command]
- Integration: [resolved integration command]
- E2E: [resolved E2E command]
- Visual: [resolved visual command]
- Lint: [resolved lint command]
- Types: [resolved type check command]

→ Proceed? (yes / no / audit-only)
```

- In `--auto` mode (from `/spec.ship` or `/spec.feature`): skip confirmation, proceed immediately
- If user chooses "audit-only": skip to Phase 5 (Report) with audit-only data
- If nothing to generate and all tests exist: skip Phase 3, go to Phase 4

---

## Phase 3 — Generate

### Deduplication (TDD awareness)

When running after `/spec.implement` (typical in `/spec.feature` and `/spec.ship` pipelines), implementation may have already created tests via TDD. Phase 1 detects these as ✅ Covered or ⚠️ Partial. Phase 3 only generates tests for AC classified as ❌ Missing — it never overwrites or duplicates tests that `/spec.implement` already created.

For each missing test identified in Phase 2:

### 3.1 — Detect Framework

Map Resolved Test Commands to test framework:

| Command pattern | Framework | Import style |
|---|---|---|
| `npx vitest` / `vitest run` | Vitest | `import { describe, it, expect } from 'vitest'` |
| `npx jest` / `jest` | Jest | `import { describe, it, expect } from '@jest/globals'` |
| `npx playwright test` | Playwright | `import { test, expect } from '@playwright/test'` |
| `pytest` | pytest | `import pytest` |
| `go test` | Go testing | `import "testing"` |
| `cargo test` | Rust | `#[cfg(test)]` |

### 3.2 — Read Existing Test Patterns

Before generating any test, read 1-2 existing test files from:
1. The same feature's test files (from `implementation.md` AC Mapping)
2. If none → nearest feature's test files
3. If none → any test file in the project matching the framework

Extract:
- Import style and dependencies
- Helper/fixture patterns (`beforeEach`, `afterEach`, seed functions, factories)
- Assertion style (`expect().toBe()`, `assert`, `assertEqual`)
- File naming convention (`*.test.ts`, `*.spec.ts`, `test_*.py`)
- Test organization (`describe` nesting, test name format)

### 3.3 — Translate Gherkin to Test

For each missing AC with a Gherkin scenario:

1. Parse the Gherkin block from `spec.md`
2. Map steps to test code:
   - `Given` → setup/arrange (`beforeEach`, seed data, navigate to page, mock dependencies)
   - `When` → action/act (API call, user click, form submission)
   - `Then` → assertion/assert (`expect`, `toEqual`, `toHaveText`, `toBeVisible`)
3. Test name MUST reference the AC: `"AC-004: preference change takes effect immediately"`
4. Match the patterns extracted in 3.2

### 3.4 — Overwrite Protection

- **Never** overwrite existing test files
- If target file exists → append new `it()` / `test()` blocks inside existing `describe()` blocks
- If the file structure is unclear or conflicts → create a new file with `_generated` suffix (e.g., `notifications_generated.spec.ts`)
- If a test with the same name already exists → skip (already covered)

### 3.5 — Compilation Gate (per generated file)

After writing each test file:

1. Run the file in isolation: e.g., `npx vitest run tests/api/notifications.test.ts` or `pytest tests/test_notifications.py -k "AC_004"`
2. If **compilation/import error** → read error, fix, and retry (max 3 iterations per file)
3. If still broken after 3 iterations → **delete the generated code** (revert to pre-generation state), mark as "Generation Failed" in report
4. If test **compiles but assertion fails** → keep the test (this reveals an implementation gap, not a generation error)

### 3.6 — Visual State Test Generation

<!-- @spec FR-004: toHaveScreenshot generation, FR-005: Baseline storage, FR-006: Metadata, FR-011: Taxonomy hash — .specs/features/009-visual-state-baselines/spec.md#fr-004 -->

When a Gherkin scenario contains `matches visual state "[state-id]"` assertions (injected by `/spec.specify` Step 5.7 sub-step 4.5), generate Playwright test code with screenshot assertions:

```typescript
// Visual state assertion — generated from behavioral trait
await expect([element]).toHaveScreenshot('[screenshot]', {
  animations: 'disabled',
  maxDiffPixels: 100,
});
```

- Look up `screenshot` from the taxonomy's `visual_states` table for the corresponding `state_id`
- The `element` locator comes from the Gherkin scenario context

**Baseline storage:** `.specs/features/NNN-slug/baselines/states/[screenshot]`

This is a `states/` subdirectory under the existing `baselines/` directory (not `baselines/components/`).

**Metadata generation:** After `--update-snapshots`, for each new baseline PNG, generate `[screenshot].meta.yml`:

```yaml
visual_state: [state-id]
behavioral_trait: [trait-name]
gherkin_scenario: "[scenario title]"
screenshot: [screenshot-filename]
created: YYYY-MM-DD
approved_by: null
approved_date: null
invalidate_on:
  - css_change
  - state_definition_change
taxonomy_hash: [git hash of system/testing/ui-behavioral-taxonomy.md]
```

The `taxonomy_hash` is obtained via `git hash-object system/testing/ui-behavioral-taxonomy.md`.

**EC-002 handling:** Before generating, check for duplicate screenshot filenames across all states. If found, raise validation error: "Duplicate screenshot name '[name]' in states '[state-a]' and '[state-b]'"

**EC-003 handling:** If baseline exists but `.meta.yml` is missing, regenerate from filename (parse state-id from `[element]-[state-id].png` pattern) and log WARNING.

**Staleness detection:** When `/spec.test` runs Phase 1 (Audit) for visual state baselines:
1. For each existing `.meta.yml`, read the `taxonomy_hash` field
2. Compare against the current hash of `ui-behavioral-taxonomy.md`
3. If mismatch, flag baseline as stale in audit output
4. Recommend: "Re-run with `--update-snapshots` to refresh stale baselines."

**Coexistence with manual tests (AC-015):** Visual state tests are appended to the feature's test file with a comment separator:

```typescript
// --- Visual State Tests (auto-generated from behavioral taxonomy) ---
```

---

## Phase 4 — Execute

Run the full resolved test suite in order:

1. **Type checker** (if resolved) — e.g., `npx tsc --noEmit`
2. **Linter** (if resolved) — e.g., `npx eslint src/`
3. **Unit tests** — e.g., `npx vitest run`
4. **Integration tests** (if resolved) — e.g., `npx vitest run tests/integration/`
5. **E2E tests** (if resolved) — e.g., `npx playwright test`

All commands come from `plan.md` or `.specs/testing/strategy.md` **Resolved Test Commands**. Never hardcode commands.

### Result Tracking

For each test, map back to the AC it covers:

| Test | AC | Result | Source | Notes |
|---|---|---|---|---|
| `"AC-001: returns unread count"` | AC-001 | ✅ Pass | Existing | |
| `"AC-002: marks as read on click"` | AC-002 | ✅ Pass | Existing | |
| `"AC-004: preference change"` | AC-004 | ❌ Fail | Generated | assertion: expected 0, got 3 |
| `"AC-005: mark all as read"` | AC-005 | ✅ Pass | Generated | |

### Failure Handling

- **Generated test fails (assertion):** Report as "Generated — Fail". Do NOT attempt to fix implementation code. This means the implementation is incomplete or buggy — `/spec.test` reveals the gap, `/spec.implement --resume` fixes it.
- **Existing test fails:** Report as "Regression". Not `/spec.test`'s responsibility to fix.
- **Test runner crashes or times out:** Report as "Blocked — [error message]". Suggest recovery command.
- **All tests pass:** Report as "✅ All passing".

---

## Phase 4.5 — Visual (UI features only)

**Only runs when ALL of these are true:**
- Feature's `spec.md` has a `## Screens` section
- Missing baselines detected in Phase 1 audit (or missing visual test files)
- Playwright (or resolved visual tool) is available
- `--no-visual` is NOT set

### 4.5.1 — Generate Missing Visual Test Files

**Skipped if `--no-generate` is set.** Only baselines for existing visual tests are captured (Phase 4.5.2).

#### Screens Table Format

The spec.md `## Screens` table may include optional `selector` and `aa_tolerance` columns:

```markdown
| Screen | Route | Mockup | selector | aa_tolerance |
|--------|-------|--------|----------|--------------|
| logo   | /     | logo.png | [data-testid='logo'] | false |
| hero   | /     | hero.png | | false |
```

- **`selector`** — CSS selector or data-testid for component-level capture. If empty or absent, fall back to full-page screenshot.
- **`aa_tolerance`** — if `true`, use `{ maxDiffPixels: 10 }` to allow minor antialiasing variance.

#### Generation Rules

For each screen in `spec.md` without a corresponding visual test file:

1. **Locate mockup reference:** Read mockup PNG from `.specs/design/screens/` (optional, for naming consistency)
2. **Read `selector` from Screens table**
3. **Generate test based on selector presence:**

   - **Selector defined** → component-level capture:
     ```typescript
     // @spec FR-001: component-level snapshot — .specs/features/NNN-feature-name/spec.md#fr-001
     test('Screen: {screen-name}', async ({ page }) => {
       await page.goto('{screen-route}')
       await page.waitForLoadState('networkidle')
       await page.locator("{selector}").toHaveScreenshot("{screen-name}.png")
     })
     ```

   - **No selector (or empty)** → full-page fallback with warning comment:
     ```typescript
     test('Screen: {screen-name}', async ({ page }) => {
       await page.goto('{screen-route}')
       await page.waitForLoadState('networkidle')
       // Full-page screenshot — add selector for component-level precision
       await page.toHaveScreenshot("{screen-name}.png")
     })
     ```

4. **`aa_tolerance: true` override:**
   Add `{ maxDiffPixels: 10 }` as toHaveScreenshot option:
   ```typescript
   await page.locator("{selector}").toHaveScreenshot("{screen-name}.png", { maxDiffPixels: 10 })
   ```

5. **Follow existing patterns:** Read 1-2 existing visual test files to match import style, fixture usage, and naming conventions
6. **Compilation gate:** Run the generated file in isolation. If compile error → fix and retry (max 3 iterations). If still broken → delete generated code, mark "Generation Failed"

### 4.5.2 — Capture Baselines

Run ONLY if Phase 4 (non-visual tests) passed.

**CRITICAL: `--update-snapshots` must NEVER be passed to Playwright.** Use `--reset-baselines` for intentional baseline updates.

#### Default behavior (comparison only)

When `--reset-baselines` is NOT set:
- Run existing visual tests to compare against current baselines
- Never delete, replace, or overwrite any existing baseline PNG
- Any diff triggers test failure — do NOT auto-update

#### `--reset-baselines` behavior

When `--reset-baselines` is set:

1. **CI guard:** If `CI` environment variable is set → exit immediately:
   ```
   Error: Baseline reset must run locally. Commit new baselines after approval.
   ```

2. **Delete existing baselines:**
   - `--reset-baselines` (no value): delete all baseline PNGs for the target feature
   - `--reset-baselines=<screen-name>`: delete only `baselines/<screen-name>.png`

3. **Capture fresh screenshots:** Run Playwright without `--update-snapshots`

4. **Baseline storage:** New screenshots saved to `.specs/features/NNN/baselines/`

5. **Retry on failure:** If capture fails → retry up to 2 times, then mark "Blocked — [error]"

**Prerequisites — frontend detection:** Before generating `docker-compose.visual.yml`, verify the project has a web frontend layer by checking for any of:
- Routes directory: `src/app/routes`, `app/routes`, `src/routes`, `src/pages`, `pages`, `frontend/app/routes`
- Config file: `frontend/playwright.config.ts`, `playwright.config.ts`, `cypress.config.ts`
- Pencil mockups: `.specs/design/screens/`
- `package.json` with a web framework dep: `react`, `vue`, `next`, `nuxt`, `svelte`, `@angular`, `astro`, `vite`, `webpack`, `remix`, `solid-js`

If no web frontend detected:
```
LOG: "No web frontend detected — docker-compose.visual.yml skipped."
SKIP docker-compose generation and continue to next step.
```

#### `docker-compose.visual.yml` generation

On first run (or if `docker-compose.visual.yml` is absent in the target project):
1. Generate `docker-compose.visual.yml` with pinned Playwright Docker image
2. Record Docker image version as metadata alongside baselines (e.g., in `baselines/.docker-version`)
3. Surface the run command:
   ```
   Visual test environment: docker-compose.visual.yml generated.
   Run baseline capture with: docker compose run visual-tests
   ```

**Template:**
```yaml
# Run baseline capture with: docker compose run visual-tests
# This ensures identical pixel output across macOS and CI (Linux + Chrome).
services:
  visual-tests:
    image: mcr.microsoft.com/playwright:v1.44.0-jammy
    volumes:
      - ./tests:/app/tests
      - ./.specs:/app/.specs
    command: npx playwright test tests/e2e/screens/
    working_dir: /app
```

**If `docker-compose.visual.yml` already exists:** skip generation, log: "docker-compose.visual.yml already exists — skipping generation"

**Docker baseline warning:** If baselines exist but no `baselines/.docker-version` metadata file is found, display:
```
Warning: Baselines captured outside Docker — pixel differences may be caused by render environment, not UI changes.
Run spec.test --reset-baselines inside Docker to recapture.
```

### 4.5.3 — Design Fidelity / Human Approval Gate

Runs after EVERY baseline capture (new or `--reset-baselines`). This phase is mandatory — baselines are NEVER committed without passing through it.

#### Step A: Compute diffs

For each newly captured baseline PNG:
1. Find corresponding mockup in `.specs/design/screens/{screen-name}.png`
2. Compute pixel diff using `compareDesign()` from `visual.ts`
3. Record: screen name, baseline path, mockup path (or "no mockup"), diff %

#### Step B: Interactive approval (non-`--auto` mode)

Display approval table:
```
| Screen   | Baseline captured | Diff vs mockup |
|----------|-------------------|----------------|
| logo     | ✅ baselines/logo.png | 2.1%         |
| dashboard | ✅ baselines/dashboard.png | 8.4%    |
| hero     | ✅ baselines/hero.png | (no mockup)   |

Approve baselines? [y/n/view <screen-name>]
```

- **`y`** → commit all captured PNGs, continue to Phase 5
- **`n`** → delete ALL captured PNGs, exit:
  ```
  Baselines rejected — fix the UI then run spec.test --reset-baselines
  ```
- **`n <screen-name>`** → delete only that screen's PNG, redisplay approval table
- **`view <screen-name>`** → print:
  ```
  Baseline: .specs/features/NNN/baselines/<screen-name>.png
  Mockup:   .specs/design/screens/<screen-name>.png
  ```
  Then redisplay approval prompt.

#### Step C: `--auto` mode (pipeline integration)

When running from `/spec.ship` or `/spec.feature` with `--auto`:

1. If **no mockups available** → auto-approve all baselines with warning:
   ```
   Warning: No mockups found — baselines auto-approved without fidelity check.
   ```

2. If **any baseline diff > 5%**:
   - Delete all captured PNGs
   - Exit with:
     ```
     SHIP_RESULT: BLOCKED
     Visual fidelity check failed:
     - dashboard: 8.4% diff (threshold: 5%)
     Fix the UI or update the mockup, then re-run spec.test --reset-baselines.
     ```

3. If **all diffs ≤ 5%** → auto-approve, commit baselines, add to test report:
   ```
   Baselines auto-approved (all diffs ≤ 5%)
   ```

#### Step D: Write provenance manifest (after approval — always)

<!-- @spec FR-001: Write baseline.manifest.yml after approval — .specs/features/004-visual-testing-governance/spec.md#fr-001 -->

After approval (Step B `y` or Step C auto-approve), write `baselines/baseline.manifest.yml`:

**Data collection per screen:**

| Field | Source |
|-------|--------|
| `capture_date` | Current timestamp (ISO 8601 UTC) |
| `approved_by` | `git config user.name` in interactive mode; `"auto (spec.ship)"` or `"auto (spec.feature)"` in `--auto` mode |
| `browser_version` | Parse from `playwright --version` output: `"Version 1.44.0"` → `"chromium/1.44"` |
| `os` | Platform name + version from system info (e.g., `"Linux 6.1"`, `"Darwin 25.2"`) |
| `mockup_version` | SHA-256 hex of mockup PNG binary at capture time. `"none"` if no mockup exists for this screen. |
| `docker_image` | Image field from `docker-compose.visual.yml` if it exists; otherwise `"none"` |

**Write sequence (order-dependent — write manifest AFTER PNGs committed):**

```
1. Commit PNGs (existing behavior)
2. Collect provenance data for all approved screens
3. Write baselines/baseline.manifest.yml (see system/schemas/baseline-manifest.md)
4. Log: "Provenance manifest written: baselines/baseline.manifest.yml"
```

**Manifest structure:** See `system/schemas/baseline-manifest.md` for the canonical YAML schema.

**Error handling:**
- If `playwright --version` fails → use `browser_version: "unknown"`
- If SHA-256 of mockup fails (file unreadable) → use `mockup_version: "none"`
- Manifest write failure is a WARNING, not an error — baselines are still valid

### Visual Thresholds

| Check type | Threshold | Scope | Owner |
|---|---|---|---|
| Design fidelity (baseline vs mockup) | 5% | New baselines only | `/spec.test` Phase 4.5 |
| Visual regression (baseline vs previous) | `maxDiffPixels: 0` | Existing baselines | `/spec.check` Step 8 |

#### Generated playwright.config.ts snippet

```typescript
// @spec FR-006: maxDiffPixels threshold — .specs/features/NNN/spec.md#fr-006
export default defineConfig({
  expect: {
    toHaveScreenshot: {
      maxDiffPixels: 0,    // Zero tolerance — any pixel diff is a regression
      // Per-test override: { maxDiffPixels: 10 } for aa_tolerance: true screens
    },
  },
})
```

**Never use `maxDiffPixelRatio`.** Use `maxDiffPixels: 0` for zero tolerance. Use `{ maxDiffPixels: 10 }` inline on `toHaveScreenshot()` for screens with `aa_tolerance: true`.

`/spec.test` does NOT evaluate visual regression (pixel-diff against previous baselines). It only performs design fidelity checks on **newly captured** baselines. Visual regression on existing baselines is `/spec.check`'s responsibility.

**If Playwright is not installed:** Skip entire phase, report:
```
Visual tests skipped — Playwright not installed.
Install: npm install -D @playwright/test && npx playwright install --with-deps
```

---

## Phase 5 — Report

### Test Report Structure

```markdown
## Test Report: NNN-feature-name

**Date:** YYYY-MM-DD
**Feature:** `.specs/features/NNN-feature-name/`
**Mode:** full | audit-only | no-generate

### AC Coverage

| AC | Description | Test | Result | Source | Notes |
|---|---|---|---|---|---|
| AC-001 | Unread count badge | `tests/api/notifications.test.ts` | ✅ Pass | Existing | |
| AC-002 | Click marks read | `tests/e2e/notifications.spec.ts` | ✅ Pass | Existing | |
| AC-003 | Disable email notifs | `tests/api/notifications.test.ts` | ⚠️ Partial | Existing | Missing edge cases |
| AC-004 | Immediate effect | `tests/e2e/notifications.spec.ts` | ❌ Fail | Generated | Impl incomplete |
| AC-005 | Mark all as read | `tests/e2e/notifications.spec.ts` | ✅ Pass | Generated | |

### Suite Results

| Suite | Command | Result | Duration |
|---|---|---|---|
| Types | `npx tsc --noEmit` | ✅ Pass | 2.1s |
| Lint | `npx eslint src/` | ✅ Pass | 1.4s |
| Unit | `npx vitest run` | ✅ 12/12 | 3.2s |
| E2E | `npx playwright test` | ⚠️ 7/8 | 18.4s |

### Visual Baselines (if applicable)

| Screen | Baseline | Mockup diff | Status |
|---|---|---|---|
| login | ✅ Existing | — | — |
| dashboard | ✅ Captured | 3.2% | ✅ Faithful |

### Generation Summary

| Metric | Value |
|---|---|
| Tests generated | 3 |
| Generation passed | 2 |
| Generation failed (impl bug) | 1 |
| Generation failed (compile) | 0 |

### Summary

- **AC coverage:** 4/5 (80%) — 1 fail (AC-004)
- **Test suite:** 19/20 passing
- **Visual:** 2/2 baselines present
- **Overall:** ⚠️ Needs attention — AC-004 implementation incomplete
```

### Persist

1. Save report to `.specs/features/NNN-feature-name/checks/YYYY-MM-DD-test.md`
2. Update `implementation.md` AC Mapping section with current test status (unless `--no-update`)
3. Add entry to feature `changelog.md`:

```markdown
### YYYY-MM-DD — Test: AC coverage validated

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** [list generated test files, if any]
- **Coverage:** N/M AC covered (X%), N generated, N passing
- **Report:** `checks/YYYY-MM-DD-test.md`
- **Author:** [tool name]
```

4. Add summary entry to `.specs/changelog.md` (global):
   `[Feature NNN] Test: X% AC covered (N/M), N tests generated`

---

## Multi-Feature Consolidated Report

When multiple features are tested in a single run, display after all individual reports:

```markdown
## Consolidated Test Report

| Feature | AC Coverage | Suite | Visual | Generated | Overall |
|---|---|---|---|---|---|
| 004-notifications | ⚠️ 80% (4/5) | ⚠️ 19/20 | ✅ 2/2 | 3 (2✅ 1❌) | ⚠️ |
| 001-user-auth | ✅ 100% (5/5) | ✅ 8/8 | N/A | 0 | ✅ |
| 003-messaging | ❌ 30% (2/7) | ❌ 3/10 | N/A | 5 (3✅ 2❌) | ❌ |

### Priorities

1. ❌ **003-messaging**: 70% of AC missing tests — 2 generated tests reveal impl bugs
2. ❌ **004-notifications AC-004**: implementation incomplete (generated test reveals bug)
3. ⚠️ **004-notifications AC-003**: partial test coverage — missing edge cases
```

---

## Flags

| Flag | Short | Behavior |
|---|---|---|
| `--audit-only` | `-a` | Only audit coverage (Phases 0-1), don't generate or execute |
| `--no-generate` | `-G` | Execute existing tests but don't generate missing ones. Skips Phase 3 (AC test generation) and Phase 4.5.1 (visual test file generation) |
| `--no-visual` | `-V` | Skip visual baseline capture and design fidelity check |
| `--all` | `-A` | Test all features with status `Implemented` or `In Progress` |
| `--auto` | | No confirmation prompts (for `/spec.feature` Phase 3.5 and `/spec.ship` integration) |
| `--update` | `-u` | Auto-update `implementation.md` without asking |
| `--no-update` | `-U` | Skip `implementation.md` update |
| `--no-behavioral` | | Skip behavioral coverage audit (sub-phase 1.5) |
| `--reset-baselines[=<screen>]` | | Delete existing baselines (all, or named screen only) then recapture. Triggers human approval gate. Use `--reset-baselines` for intentional UI changes — NEVER `--update-snapshots`. Blocked on CI. |
| `--regenerate-missing` | | Scan all features for missing tests. Combine with `--confirm` to generate or `--dry-run` to preview. See dedicated section below. |

---

## Iteration Limits

| Action | Max iterations | On limit reached |
|---|---|---|
| Generated test compilation fix | 3 per file | Delete generated code, mark "Generation Failed" |
| Visual capture retry | 2 | Skip, mark "Blocked — [reason]" |
| Approval gate view cycles | Unlimited | Continue displaying prompt until y/n/n \<screen\> |

---

## Integration Points

### /spec.feature pipeline

Added as **Phase 3.5** (after implement, before completion):

```
Phase 1: specify → Phase 1.5: spec review → Phase 2: plan → Phase 2.5: plan review → Phase 2.7: preflight → Phase 3: implement → Phase 3.5: TEST → Done
```

`/spec.test` generates missing tests that `/spec.implement`'s Phase 6 could not run because they didn't exist yet. It also captures visual baselines that may have been skipped during implement.

### /spec.ship

After each feature's implementation phase, the spawned agent runs `/spec.test <feature> --auto` before merge. If the test report shows ❌ failures in AC coverage → `SHIP_RESULT: BLOCKED`.

### /spec.check

`/spec.check` can reference the latest test report from `checks/YYYY-MM-DD-test.md` to include dynamic test results alongside its static alignment analysis.

---

## --regenerate-missing Flag

<!-- @spec FR-007: Scan for missing tests, FR-008: Batch generation, FR-009: Dry-run, FR-010: Never overwrite — .specs/features/009-visual-state-baselines/spec.md#fr-007 -->

**Trigger:** `/spec.test --regenerate-missing [--confirm] [--dry-run] [feature-name?]`

**Behavior:**

1. **Scan:** Walk `.specs/features/*/` directories
   - For each directory with a `spec.md` file:
     - If `tests/` subdirectory does NOT exist within the feature directory → flag as missing
     - If `tests/` exists → skip (EC-004 guard: never overwrite)
     - If `spec.md` does not exist → skip (no spec to generate from)
   - Include `status: Draft` specs in scan (EC-005: Draft specs need tests too)

2. **Report:**
   ```
   Scanning .specs/features/ for missing tests...

   Features missing tests (N):
     - 003-visual-testing-fidelity
     - 007-structured-signal-extraction
     - 010-api-auth-service

   Run with --confirm to generate tests.
   ```

3. **Guard (FR-010):** Features with existing `tests/` directories are NEVER included in the generation list. This is a hard guard — there is no `--force` override.

4. **Generation (--confirm):** For each feature in the list, run the same Phases 1-3 logic as normal `/spec.test`:
   - Phase 1: Build coverage matrix from spec.md
   - Phase 2: Plan test generation
   - Phase 3: Generate missing tests from Gherkin
   - Skip Phases 4-5 (execution and visual) — generation only

5. **Dry-run (--dry-run):** Display the list only, create no files, exit 0.

6. **No sub-flag:** Display the summary and prompt: "Run with `--confirm` to generate or `--dry-run` to preview."

7. **Empty result (EC-004):** If no features are missing tests:
   ```
   All features have tests. Nothing to regenerate.
   ```
   Exit 0.

**Example run:**
```
$ /spec.test --regenerate-missing --dry-run
Scanning .specs/features/ for missing tests...

Features missing tests (3):
  - 003-visual-testing-fidelity
  - 007-structured-signal-extraction
  - 010-api-auth-service

Run with --confirm to generate tests.
```

---

## Definition of Done (Command-Level)

`/spec.test` is complete only if all are true:

- [ ] Coverage matrix produced for all AC
- [ ] Missing tests generated (or `--audit-only` / `--no-generate`)
- [ ] Full test suite executed (or `--audit-only`)
- [ ] Visual baselines captured for missing screens (or `--no-visual` / non-UI feature)
- [ ] `baselines/baseline.manifest.yml` written after every baseline approval (or `--no-visual`)
- [ ] Test report saved to `checks/YYYY-MM-DD-test.md`
- [ ] `implementation.md` AC status updated (or `--no-update`)
- [ ] Feature `changelog.md` has test entry
- [ ] Global `.specs/changelog.md` has summary entry
- [ ] If multi-feature: consolidated report produced

---

*LiveSpec Command v1.0*
