---
description: "Verify spec vs code alignment and produce gap report"
argument-hint: "<feature-name>"
---

<!-- Anti-drift block injected via @import (Chantier 1, AUDIT.md). See system/anti-drift-block.md for the canonical 6-field step shape, ERROR/BLOCKED line formats, and timeout/retry policy. -->
<!-- @import system/anti-drift-block.md -->


# Command: /spec.check

> Compare spec vs actual code — find gaps, verify AC coverage, detect visual drift.
> Validate `.specs/` tree structure, spec quality gates, and multi-feature alignment.

---

## Overview

```
/spec.check                       → Steps 1-2 → [per feature: Steps 3-10] → Step 11
/spec.check feature-name          → Step 1 → Steps 3-10
/spec.check --tree-only           → Step 1 only
/spec.check --quality feature     → Step 1 → Steps 3-4 only
/spec.check feature --show-provenance  → Step 1 → Step 3 → Step 3.1 (provenance table) → exit
/spec.check --visual-status       → Step 8.5 (governance dashboard) → exit
/spec.check --surfaces            → Step 1 → Step 1.5 (surface drift detection) → exit
```

```mermaid
flowchart TD
    START(["/spec.check"]) --> TREE["Step 1\nValidate tree\n(system files,\nnaming, completeness)"]
    TREE --> FEAT{"Feature\nspecified?"}
    FEAT -->|"yes"| RESOLVE["Resolve\nfeature"]
    FEAT -->|"no"| SELECT["Step 2\nList features\n→ user selects"]
    SELECT --> RESOLVE

    RESOLVE --> QUALITY["Steps 3-4\nSpec quality gates\n(Gherkin, Mermaid,\nAC, FR mapping)"]
    QUALITY --> READ["Steps 5-6\nRead requirements\n+ implementation map"]
    READ --> VERIFY["Step 7\nVerify each FR/AC\nvs actual code"]
    VERIFY --> VISUAL{"UI +\nbaselines?"}
    VISUAL -->|"yes"| DRIFT["Step 8\nVisual drift\ndetection"]
    VISUAL -->|"no"| REPORT
    DRIFT --> REPORT["Step 9\nGap report\n(FR/AC/visual tables)"]
    REPORT --> SAVE["Step 10\nSave report +\nupdate changelogs"]
    SAVE --> MULTI{"Multiple\nfeatures?"}
    MULTI -->|"yes"| CONSOL["Step 11\nConsolidated report\n(cross-feature)"]
    MULTI -->|"no"| DONE(["Done"])
    CONSOL --> DONE

    style START fill:#e8f4f8,stroke:#2196F3
    style VERIFY fill:#fff3e0,stroke:#FF9800
    style REPORT fill:#fff3e0,stroke:#FF9800
    style DONE fill:#e8f5e9,stroke:#4CAF50
```

---

> **Hooks — before starting:** **Read** `before-check` hooks from all 3 levels (skip missing files):
> 1. `~/.claude/livespec/hooks/before-check.md`
> 2. `.specs/hooks/before-check.md`
> 3. `.specs/hooks/before-check.local.md` (if `mode: override` → use only this one)
>
> **Hooks — after completing:** Same resolution with `after-check` at all 3 levels.

## Steps

### Step 1 — Validate Tree Structure

Always executed first (unless `--skip-tree`).

#### A. System Files

Verify existence of required system files in `.specs/`:

| File | Required | Rule |
|---|---|---|
| `spec-system.md` | ✅ | Must exist |
| `constitution.md` | ✅ | Must exist |
| `project.md` | ✅ | Must exist |
| `README.md` | ✅ | Must exist |
| `changelog.md` | ✅ | Must exist |
| `stacks/_default.md` | ✅ | Must exist and contain no `[TBD]` markers |
| `testing/strategy.md` | ✅ | Must exist |
| `stacks/decisions/*.md` | ✅ | At least 1 ADR must exist |

#### B. Feature Naming

Each directory in `features/` must match: `^\d{3}-[a-z0-9]+(-[a-z0-9]+)*$`

- **ERROR**: Directory name doesn't match pattern
- **WARNING**: Gap in numbering sequence (e.g., 001, 002, 005)
- **ERROR**: Duplicate feature number (e.g., two `003-*` directories)

#### C. Feature Completeness

For each feature directory in `features/`:

| File | Condition | Severity |
|---|---|---|
| `spec.md` | Always required | ❌ BLOCKING |
| `changelog.md` | Always expected | ⚠️ WARNING |
| `implementation.md` | Required if status is `Implemented` or `In Progress` | ❌ BLOCKING |
| `plan.md` | Required if status is `Planned` or beyond | ❌ BLOCKING |

#### D. Orphan Files

Detect any files or directories directly under `features/` that are not inside a `NNN-*` directory. Report as warnings.

#### E. README Sync

Compare the Features table in `.specs/README.md` with actual directories on disk:

- Features on disk but missing from README
- Features in README but not on disk
- Status mismatch between README and `spec.md`

#### Output

```markdown
## Tree Validation

| Check | Status | Details |
|---|---|---|
| System files | ✅ Pass | All 7 system files present |
| Stack config | ✅ Pass | `_default.md` has no [TBD] |
| ADRs | ✅ Pass | 3 ADRs found |
| Feature naming | ⚠️ Warning | Gap: 001, 002, 005 (missing 003-004) |
| 001-user-auth | ✅ Pass | spec.md, plan.md, implementation.md present |
| 004-notifications | ⚠️ Warning | Missing changelog.md |
| Orphan files | ✅ Pass | No orphans detected |
| README sync | ❌ Fail | 005-search on disk but not in README |
```

### Step 1.5 — Surface Drift Detection (`--surfaces` only)

**Runs only when:** `--surfaces` flag is passed. Exits after this step.

**Purpose:** Compare `.specs/surfaces.yaml` against actual project filesystem to detect drift — surfaces that exist on disk but are not configured, or configured surfaces whose paths no longer exist.

#### Procedure

1. **Read `.specs/surfaces.yaml`**
   - If absent: display `No surfaces configured. Run /spec.migrate to generate .specs/surfaces.yaml.` and exit.
   - If parse error: display `FATAL: surfaces.yaml is malformed` with error details and exit.

2. **Validate configured surfaces:**
   - For each surface: check `path` exists on disk
   - Check for duplicate `id` or `testDir` values
   - Check `testDir` is under `path` (or at project root for `path: .`)
   - Check `runnerConfig` file exists if specified

3. **Scan filesystem for unconfigured surfaces:**
   - Scan `apps/*/`, `packages/*/`, `frontend/`, `web/`, `client/` for directories with web markers (package.json with web framework deps, routes directories, Playwright config)
   - Report any app directory with web markers that is NOT in `surfaces.yaml`

4. **Report:**

```markdown
## Surface Drift Report

| Surface | Status | Details |
|---|---|---|
| web (apps/web) | ✅ Configured | runner: playwright, testDir: apps/web/tests/e2e |
| mobile (apps/mobile) | ✅ Configured | runner: manual |
| apps/dashboard | ⚠️ Not configured | Has web deps (react), not in surfaces.yaml |
| watch (apps/watch) | ⚠️ Path missing | Configured but apps/watch/ does not exist |
```

**Exit:** After displaying the report. Does not proceed to Step 2+.

If `--tree-only`, stop here. Otherwise continue.

---

### Step 2 — Multi-Spec Selection (no argument only)

Only when `/spec.check` is invoked without a feature name argument.

1. Scan all `features/NNN-*` directories
2. For each feature, collect:
   - **Name**: from the `# ` header in `spec.md`, or directory name as fallback
   - **Status**: from `spec.md` metadata
   - **Last modified**: `git log -1 --format="%ai" -- .specs/features/NNN-*/`
3. **Sort by last modification date, most recent first**
4. Present selection table:

```
| # | Feature              | Status      | Last Modified |
|---|----------------------|-------------|---------------|
| 1 | 004-notifications    | Implemented | 2026-03-12    |
| 2 | 001-user-auth        | Implemented | 2026-03-10    |
| 3 | 003-messaging        | Approved    | 2026-03-05    |
| 4 | 002-job-listings     | Draft       | 2026-02-28    |

Selection: numbers (1,3), range (1-3), combined (1,3-5), or "all"
Enter = most recent feature only
```

5. Execute Steps 3–10 for each selected feature
6. Then Step 11 (consolidated report) if multiple features selected

---

### Step 3 — Resolve Feature

1. If feature name provided: find `.specs/features/NNN-feature-name/`
2. If no feature name: detect from current git branch (`feature/NNN-feature-name`)
3. If still ambiguous: list all features and ask user to choose

#### Step 3.1 — `--show-provenance` early exit

<!-- @spec FR-002: show-provenance flag reads and displays manifest — .specs/features/004-visual-testing-governance/spec.md#fr-002 -->

If `--show-provenance` is set, execute this block after resolving the feature, then exit (skip Steps 4–10):

1. Look for `baselines/baseline.manifest.yml` in the resolved feature directory
2. **If manifest absent:**
   ```
   No baseline manifest found for <feature-name>.
   Run spec.test --reset-baselines to capture baselines and generate provenance.
   ```
3. **If manifest present but unparseable:** treat as absent (same message above)
4. **If manifest present and parseable:** render provenance table:
   ```markdown
   ## Baseline Provenance: <feature-name>

   | Screen | Capture Date | Approved By | Mockup Version | Browser | OS | Docker Image |
   |--------|-------------|-------------|----------------|---------|-----|--------------|
   | logo   | 2026-04-14T10:28Z | julienm | sha256:e3b0c4… | chromium/1.44 | Linux 6.1 | playwright:v1.44.0-jammy |
   | dashboard | 2026-04-14T10:29Z | auto (spec.ship) | sha256:abc987… | chromium/1.44 | Linux 6.1 | playwright:v1.44.0-jammy |
   ```
   - Truncate `mockup_version` to first 8 chars of the hex after `sha256:` for display
   - Truncate `docker_image` to just the tag part (e.g., `playwright:v1.44.0-jammy`)
   - Print manifest `generated_at` timestamp above the table

### Step 4 — Validate Spec Quality

Applies quality gates from `spec-system.md` to the resolved feature.

#### spec.md Quality Gates

| Gate | Rule |
|---|---|
| Gherkin scenarios | Every acceptance scenario uses ```gherkin blocks |
| Flowcharts | Every user story has a Mermaid flowchart |
| Gherkin↔Mermaid | Gherkin scenarios and Mermaid flowcharts describe the same flow |
| AC format | All Acceptance Criteria use Given/When/Then format |
| FR→AC mapping | Every FR references at least 1 AC |
| Clarification markers | No more than 3 `[NEEDS CLARIFICATION]` markers |

#### plan.md Quality Gates (if file exists)

| Gate | Rule |
|---|---|
| Sequence diagrams | API interactions have sequence diagrams |
| State diagrams | Stateful entities have state diagrams |
| ER diagrams | New data models have ER diagrams |
| Constitution Check | Section is filled (not empty/placeholder) |
| FR coverage | All FR from spec.md are covered in the plan |

#### Implementation Quality Gates (if applicable)

| Gate | Rule |
|---|---|
| `implementation.md` | Exists with status for each FR/AC |
| `changelog.md` | Has at least one entry |
| `progress.md` | Exists if status is `Implemented` |

#### Output

```markdown
## Spec Quality: 004-notifications

| Gate | Status | Details |
|---|---|---|
| User story flowcharts | ✅ Pass | 3/3 stories have flowcharts |
| AC Given/When/Then | ⚠️ Partial | AC-004 missing Given/When/Then |
| FR→AC mapping | ✅ Pass | All 6 FR reference at least 1 AC |
| Clarification markers | ✅ Pass | 0 markers found |
| Sequence diagrams | ✅ Pass | 2 API interactions covered |
| State diagrams | ⚠️ N/A | No stateful entities identified |
| ER diagrams | ✅ Pass | NOTIFICATION entity diagrammed |
| Constitution Check | ✅ Pass | Section filled |
| Plan FR coverage | ✅ Pass | 6/6 FR covered |
| implementation.md | ✅ Pass | All FR/AC have status |
| changelog.md | ✅ Pass | 4 entries |
| progress.md | ❌ Missing | Required for Implemented status |
```

If `--quality`, stop here. Otherwise continue.

---

### Step 5 — Read Spec Requirements

From `.specs/features/NNN-feature-name/spec.md`, extract:
- All Acceptance Criteria (AC-001, AC-002, ...)
- All Functional Requirements (FR-001, FR-002, ...)
- All Success Criteria (SC-001, SC-002, ...)

### Step 6 — Read Implementation Map

From `.specs/features/NNN-feature-name/implementation.md`, get:
- FR → `@spec` anchor mappings
- AC → test file mappings
- Visual baselines list
- Known gaps from last check

### Step 6.5 — Mapping Recovery Mode

If `implementation.md` is missing or incomplete:

1. Build a temporary mapping by searching `@spec FR-*` and `@spec AC-*` anchors in source files. Extract descriptions from the `@spec ID: description` format when present.
2. Infer AC coverage from test names/assertions and test metadata.
3. Mark inferred links as `~ Inferred` (never as fully verified mapping).
4. Recommend updating `implementation.md` at end of run.

### Evidence Standard (No Guessing)

A requirement can be marked ✅ only if at least one of these is present:

- Direct code evidence at mapped location + behavior alignment
- Passing test explicitly tied to the AC/FR
- Explicit `@spec` anchor and coherent implementation

If evidence is weak, use ⚠️ Partial with a short reason.

### Step 7 — Verify Implementation

For each FR and AC:

1. **Find the mapped file** from `implementation.md`
2. **Read the actual code** at the specified lines
3. **Verify it satisfies the requirement:**
   - Does the code implement what the FR describes?
   - Does the code produce the outcome the AC specifies?
   - Is there a test that verifies the AC?
4. **Assign status:**
   - ✅ Verified — code clearly satisfies the requirement
   - ⚠️ Partial — code exists but doesn't fully satisfy the requirement
   - ❌ Missing — no implementation found at mapped location or mapping is absent
   - 🔄 Drifted — code changed but implementation.md not updated

### Step 8 — Detect Visual Drift (UI features)

**Prerequisite:** Feature's `spec.md` has a `## Screens` section AND baselines exist in `.specs/features/NNN-feature-name/baselines/`. Skip entire step if either is absent.

<!-- @spec FR-007: maxDiffPixels for regression — .specs/features/003-visual-testing-fidelity/spec.md#fr-007 -->

#### Step 8.0 — Staleness Gate (runs BEFORE pixel comparison)

<!-- @spec FR-003: staleness check before comparison, FR-004: mockup hash detection, FR-005: browser version detection — .specs/features/004-visual-testing-governance/spec.md#fr-003 -->

Before running any pixel comparison, classify each baseline's staleness state:

**1. Read manifest:**

```
Look for baselines/baseline.manifest.yml in the feature directory.
```

- **If manifest absent:** emit WARNING for all screens:
  ```
  Warning: Baselines exist but provenance manifest is missing.
  Run spec.test --reset-baselines to capture baselines and generate provenance.
  ```
  Skip pixel comparison for this feature. Continue to Step 9 with STALE=NO-MANIFEST for all screens.

- **If manifest present but YAML parse fails:** treat as absent (same warning above).

**2. Browser version check (FR-005, AC-008, AC-009):**

- Run `playwright --version` to get the current browser version tag (e.g., `"chromium/1.44"`)
- If Playwright is not installed: log `"Playwright not installed — browser version check skipped"`, skip browser check only
- Compare current tag against `browser_version` from the manifest (any screen entry — they all share the same browser)
- If **mismatch:** mark ALL screens for this feature as `STALE-BROWSER`
  - Log: `"Browser version changed: <old> → <new> — all baselines require reset"`
  - Suggest: `spec.test --all --reset-baselines`
  - Skip ALL pixel comparisons for this feature

**3. Per-screen mockup hash check (FR-004, AC-005):**

- Only runs if browser version matches (not STALE-BROWSER)
- For each screen in the manifest:
  - Find the mockup PNG at `.specs/design/screens/<screen>.png`
  - If mockup is absent: mark screen `STALE-MOCKUP` with reason `mockup_deleted` — skip its comparison
  - Compute SHA-256 of current mockup binary → compare against `manifest.screens[screen].mockup_version`
  - If **mismatch:** mark screen `STALE-MOCKUP`
    - Log: `"Mockup updated after baseline capture — baseline may no longer reflect current design"`
    - Skip comparison for this screen
  - If **match:** classify as `VALID` → proceed to pixel comparison

**4. Staleness classification summary:**

| Classification | Meaning | Pixel comparison |
|---|---|---|
| `VALID` | Browser + mockup match manifest | Runs normally |
| `STALE-MOCKUP` | Mockup SHA-256 changed | Skipped |
| `STALE-BROWSER` | Playwright version changed | Skipped (all screens) |
| `NO-MANIFEST` | No manifest file | Skipped (all screens) |

**Exit code for stale baselines:** WARNING (not ERROR). Stale baselines do NOT fail the build — they are informational.

#### Visual Regression Detection

Use `compareRegression()` helper from the test directory's `helpers/visual.ts` to detect pixel drift. Resolve the test directory from `.specs/surfaces.yaml` (first surface with `runner: playwright`) or default to `tests/e2e/`:

1. **Check resolved visual test tool** from `.specs/testing/strategy.md` or `plan.md` **Resolved Test Commands**
   - If absent → skip step, report: "Visual drift detection skipped — no visual testing tool resolved"
2. **For each baseline PNG in `baselines/` classified as VALID by the Staleness Gate:**
   - Locate the most recent Playwright test output for that screen
   - Run pixel diff: `compareRegression(baseline, currentScreenshot, maxDiffPixels: 0)`
3. **Report per baseline:**
   - ✅ **Match** — 0 pixel difference (no visual regression detected)
   - 🖼️ **Drift** — any pixel difference detected (show pixel count and changed regions)
   - ❌ **Missing baseline** — baseline file not found (capture required from spec.test Phase 4.5)

**Threshold:** `maxDiffPixels: 0` — zero tolerance. Any pixel difference is a regression. Screens with `aa_tolerance: true` in the spec use `maxDiffPixels: 10` as the per-test override.

**Report format in gap report (extended with staleness):**
```markdown
### Visual Tests (Regression Detection)

| Screenshot | Staleness | Status | Diff (px) | Notes |
|---|---|---|---|---|
| `login.png` | VALID | ✅ Match | 0 px | |
| `dashboard.png` | STALE-MOCKUP | ⚠️ Skipped | — | Mockup updated 2026-04-14 |
| `nav.png` | STALE-BROWSER | ⚠️ Skipped | — | chromium/1.42→1.44 |
| `settings.png` | NO-MANIFEST | ⚠️ Skipped | — | Run spec.test --reset-baselines |
| `header.png` | VALID | 🖼️ Drift | 312 px | Badge color changed |
```

#### Design Fidelity Check (UI features with mockups)

If the feature's `spec.md` contains a `## Screens` section:

1. For each referenced screen:
   a. Look for a Playwright baseline in `baselines/` matching the screen name
   b. If baseline exists → compare baseline vs mockup PNG from `.specs/design/screens/`
   c. Report fidelity status:
      - ✅ Faithful — implementation matches mockup (< 5% diff)
      - 🎨 Diverged — implementation differs from mockup (> 5% diff)
      - ❌ No baseline — cannot compare (Playwright screenshot not captured)

2. Add to gap report after Visual Tests section:

```markdown
### Design Fidelity

| Screen | Mockup | Baseline | Diff | Status |
|--------|--------|----------|------|--------|
| login | [mockup](../../design/screens/login.png) | [baseline](baselines/login.png) | 2.1% | ✅ Faithful |
| dashboard | [mockup](../../design/screens/dashboard.png) | [baseline](baselines/dashboard.png) | 8.4% | 🎨 Diverged |
```

**Threshold distinction:**
- Visual regression (code vs previous code): `maxDiffPixels: 0` — zero tolerance, any pixel diff is a regression
- Design fidelity (code vs mockup): 5% — allows minor implementation differences while catching major layout drift

#### Theme Token Compliance (UI features with theme)

If `.specs/design/theme.css` exists:

1. Read `theme.css` to extract all defined CSS custom properties (e.g., `--primary`, `--background`, `--secondary`)
2. For each source file mapped in `implementation.md` that contains CSS/styling:
   a. Scan for hardcoded color values (hex `#xxx`, `rgb()`, `hsl()`, `oklch()`) that match or approximate a theme token
   b. Scan for hardcoded spacing values that could use theme tokens (if theme defines spacing variables)
3. Report compliance:

```markdown
### Theme Token Compliance

| File | Hardcoded Value | Expected Token | Status |
|------|----------------|----------------|--------|
| src/components/Badge.tsx | `#EF4444` | `var(--destructive)` | 🎨 Hardcoded |
| src/components/Panel.tsx | — | — | ✅ Compliant |
```

- ✅ Compliant — all color/spacing values use theme CSS variables
- 🎨 Hardcoded — found hardcoded values that should use theme tokens

If `.specs/design/theme.css` does not exist → skip this check silently.

### Step 8.5 — Visual Governance Dashboard (`--visual-status` flag)

<!-- @spec FR-006: visual-status flag scans all features and classifies baselines — .specs/features/004-visual-testing-governance/spec.md#fr-006 -->

**Only runs when `--visual-status` is set.** Exits after display — does not run Steps 9–10.

This handler can be invoked without a feature argument: `spec.check --visual-status` scans ALL features.

#### Scan all features

1. Find all directories matching `.specs/features/*/baselines/`
2. For each feature with a `baselines/` directory:
   a. Read `baselines/baseline.manifest.yml` (if present)
   b. Get current browser version from `playwright --version` (or `"unknown"` if not installed)
   c. For each screen:
      - If no manifest: classify `NO-MANIFEST`
      - If browser version mismatch: classify `STALE-BROWSER`
      - If mockup hash mismatch or mockup deleted: classify `STALE-MOCKUP`
      - Otherwise: classify `VALID`
3. Render governance table:

```markdown
## Visual Governance Dashboard

**Checked:** 2026-04-14
**Features scanned:** 3

| Feature | Screen | Status | Last Approved | Reason |
|---------|--------|--------|---------------|--------|
| 003-visual-testing-fidelity | logo | ✅ VALID | 2026-04-14 julienm | — |
| 003-visual-testing-fidelity | dashboard | ⚠️ STALE-MOCKUP | 2026-04-14 julienm | Mockup updated after capture |
| 004-visual-testing-governance | hero | ⚠️ NO-MANIFEST | — | Run spec.test --reset-baselines |
| 002-layer-3-cli-surface | nav | ⚠️ STALE-BROWSER | 2026-04-13 julienm | chromium/1.42 → chromium/1.44 |
```

4. Print action summary if any STALE/NO-MANIFEST entries exist:

```markdown
### Action Required

| Feature | Issue | Command |
|---------|-------|---------|
| 003-visual-testing-fidelity | STALE-MOCKUP (dashboard) | `spec.test 003-visual-testing-fidelity --reset-baselines=dashboard` |
| 004-visual-testing-governance | NO-MANIFEST (hero) | `spec.test 004-visual-testing-governance --reset-baselines` |
| 002-layer-3-cli-surface | STALE-BROWSER (all) | `spec.test 002-layer-3-cli-surface --reset-baselines` |
```

5. If all baselines are VALID:
   ```
   All baselines valid — no action needed.
   ```

6. If no features have `baselines/` directories:
   ```
   No visual baselines found in this project.
   ```

### Step 9 — Produce Gap Report

Output a structured gap report. When spec quality was validated (Step 4), include a **Spec Quality** section before the FR/AC/Visual tables.

```markdown
## Gap Report: notifications (004)

**Checked:** 2024-03-20
**Feature:** `.specs/features/004-notifications/`

### Spec Quality

| Gate | Status | Details |
|---|---|---|
| User story flowcharts | ✅ Pass | 3/3 |
| AC Given/When/Then | ⚠️ Partial | AC-004 missing format |
| FR→AC mapping | ✅ Pass | 6/6 |
| Clarification markers | ✅ Pass | 0 found |

### Functional Requirements

| FR | Description | Status | Location | Notes |
|---|---|---|---|---|
| [FR-001](spec.md#fr-001) | Fetch unread notification count | ✅ Verified | `src/data/notifications.ts` (`@spec FR-001: Fetch unread count`) | |
| [FR-002](spec.md#fr-002) | Real-time count updates | ✅ Verified | `src/hooks/useNotificationSubscription.ts` (`@spec FR-002: Real-time count updates`) | |
| [FR-003](spec.md#fr-003) | Mark notification as read | ✅ Verified | `src/data/notifications.ts` (`@spec FR-003: Mark as read on click`) | |
| [FR-004](spec.md#fr-004) | Navigate to notification target | ⚠️ Partial | `src/components/notifications/NotificationItem.tsx` (`@spec FR-004: Navigate to target`) | No fallback for missing target_url |
| [FR-005](spec.md#fr-005) | Notification preferences endpoint | 🔄 Drifted | `src/api/notifications/route.ts` (`@spec FR-005: Update preferences`) | Added new fields not in spec |
| [FR-006](spec.md#fr-006) | Mark all notifications as read | ❌ Missing | — | Not implemented |

### Acceptance Criteria

| AC | Description | Status | Test | Notes |
|---|---|---|---|---|
| AC-001 | Unread count displays as badge | ✅ Verified | `tests/api/notifications.test.ts` | |
| AC-002 | Click marks as read and navigates | ✅ Verified | `tests/e2e/notifications.spec.ts` | |
| AC-003 | User can disable email notifications | ⚠️ Partial | `tests/api/notifications.test.ts` | Test exists but doesn't cover all cases |
| AC-004 | Preference change takes effect immediately | ❌ Missing | — | No test found |
| AC-005 | Mark all as read in single action | ❌ Missing | — | FR-006 missing |

### Visual Tests

| Screenshot | Status | Diff | Notes |
|---|---|---|---|
| `panel-empty.png` | ✅ Match | 0.3% | |
| `panel-unread.png` | 🖼️ Drift | 4.2% | Badge color changed from #EF4444 to #DC2626 |
| `bell-badge.png` | ✅ Match | 0.8% | |
| `bell-no-badge.png` | ❌ Missing | — | Baseline not captured |

### Theme Token Compliance

| File | Hardcoded Value | Expected Token | Status |
|------|----------------|----------------|--------|
| `src/components/NotificationBell.tsx` | — | — | ✅ Compliant |
| `src/components/NotificationPanel.tsx` | `#DC2626` | `var(--destructive)` | 🎨 Hardcoded |

> *Only shown when `.specs/design/theme.css` exists. Omit section otherwise.*

### Summary

- ✅ Verified: 5/10 (50%)
- ⚠️ Partial: 2/10 (20%)
- 🔄 Drifted: 1/10 (10%)
- ❌ Missing: 2/10 (20%)

**Overall health:** ⚠️ Needs attention
```

#### Persist Gap Report

Save the gap report to `.specs/features/NNN-feature-name/checks/YYYY-MM-DD.md`.

If the `checks/` directory does not exist, create it.

This enables historical comparison: "did the gap get worse or better since last check?"

### Step 9.5 — Update Changelog

Add an entry to `.specs/features/NNN-feature-name/changelog.md`:

```markdown
### YYYY-MM-DD — Check: Spec-code alignment verified

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None
- **Coverage:** N/M verified (X%), N partial, N missing
- **Report:** `checks/YYYY-MM-DD.md`
- **Author:** [tool name]
```

Also add a summary entry to `.specs/changelog.md` (global):
`[Feature NNN] Check: X% verified (N/M FR, N/M AC)`

### Step 10 — Suggest Fixes + Update implementation.md

For each gap, provide a specific, actionable suggestion:

```markdown
## Suggested Fixes

### ❌ FR-006: Mark all notifications as read

**What to implement:**
- Add endpoint: `POST /api/notifications/mark-all-read`
- Add data function: `markAllNotificationsRead(userId: string)`
- Add UI button in `NotificationPanel.tsx`
- Add E2E test for AC-005

**Files to create/modify:**
- `src/data/notifications.ts` — add `markAllNotificationsRead()`
- `src/api/notifications/route.ts` — add `POST /mark-all-read` handler
- `src/components/notifications/NotificationPanel.tsx` — add button
- `tests/e2e/notifications.spec.ts` — add AC-005 test

To implement: `/spec.implement notifications --step 6`

---

### 🖼️ panel-unread.png: Visual drift (4.2%)

**Detected change:** Badge background color changed from `#EF4444` to `#DC2626`

**If intentional:** Run the baseline update command from Resolved Test Commands to update the baseline, then commit.
**If unintentional:** Revert the CSS change in `NotificationBell.tsx`.

---

→ To auto-fix these gaps: `/spec.fix [feature-name]`
→ To fix visual only: `/spec.fix [feature-name] --visual`
→ To fix a specific FR: `/spec.fix [feature-name] --fr FR-NNN`
```

#### Update implementation.md (optional)

> Would you like me to update `implementation.md` with the current status from this check?
> This will mark drifted/partial items accurately.
>
> Type **yes** to update, **no** to skip.

---

### Step 11 — Consolidated Multi-Spec Report

Only produced when multiple features are checked in a single run. Displayed after all individual feature checks complete.

#### 1. Health per Feature

```markdown
## Consolidated Report

### Feature Health

| Feature | Spec Quality | Code Alignment | Visual | Design | Overall |
|---|---|---|---|---|---|
| 004-notifications | ⚠️ 8/10 | ⚠️ 50% verified | 🖼️ 1 drift | 🎨 1 diverged | ⚠️ Needs attention |
| 001-user-auth | ✅ 10/10 | ✅ 95% verified | ✅ All match | ✅ Faithful | ✅ Healthy |
| 003-messaging | ✅ 9/10 | ❌ 30% verified | N/A | N/A | ❌ Critical |
```

#### 2. Cross-Feature Dependencies

Detect source files referenced in multiple `implementation.md` files. Signal coupling:

```markdown
### Cross-Feature Dependencies

| File | Referenced by | Risk |
|---|---|---|
| `src/data/notifications.ts` | 004-notifications, 001-user-auth | ⚠️ Shared module |
| `src/lib/auth.ts` | 001-user-auth, 003-messaging | ⚠️ Shared module |
```

#### 3. Aggregated Stats

```markdown
### Stats

- **Quality gates**: 27/30 passing (90%)
- **Requirements verified**: 18/25 (72%)
- **Visual baselines**: 8/10 matching (80%)
```

#### 4. Priorities

Ordered list of the most urgent actions across all checked features:

```markdown
### Priorities

1. ❌ **003-messaging**: 70% of requirements missing — needs implementation
2. ❌ **004-notifications**: FR-006 not implemented, AC-004/AC-005 untested
3. ⚠️ **004-notifications**: AC-004 missing Given/When/Then format in spec
4. 🖼️ **004-notifications**: `panel-unread.png` visual drift (4.2%)
```

---

## Output

```
.specs/features/004-notifications/
├── checks/
│   └── 2024-03-20.md   ← Gap report saved
└── implementation.md    ← Status updated (if --update)
```

---

## Flags

| Flag | Behavior |
|---|---|
| `--update`, `-u` | Automatically update `implementation.md` without asking |
| `--no-visual`, `-V` | Skip visual diff comparison |
| `--fix`, `-x` | After reporting, attempt to fix ❌ Missing items automatically |
| `--report`, `-R` `[path]` | Save gap report to specified file instead of printing |
| `--tree-only`, `-t` | Only validate tree structure, skip per-feature checks |
| `--skip-tree`, `-T` | Skip tree validation (for quick single-feature check) |
| `--quality`, `-q` | Only validate spec quality gates, skip code alignment |
| `--all`, `-A` | Check all features without prompting for selection |
| `--summary`, `-S` | Multi-spec: only display the consolidated report |
| `--show-provenance` | Display baseline provenance table for the resolved feature (Step 3.1). Exits after display — does not run Steps 4–10. |
| `--visual-status` | Scan all features and display the visual governance dashboard (Step 8.5). Exits after display. |

---

## Definition of Done (Command-Level)

`/spec.check` is complete only if all are true:

- [ ] Tree validation passed (or `--skip-tree`)
- [ ] Spec quality gates evaluated (per feature)
- [ ] Gap report produced and displayed
- [ ] Gap report saved to `checks/YYYY-MM-DD.md`
- [ ] Feature `changelog.md` has a check entry
- [ ] Global `.specs/changelog.md` has a summary entry
- [ ] If `--update`: `implementation.md` status values refreshed
- [ ] If multi-spec: consolidated report produced

---

*LiveSpec Command v1.1*
