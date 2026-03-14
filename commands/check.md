---
description: "Verify spec vs code alignment and produce gap report"
argument-hint: "<feature-name>"
---

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
```

---

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

### Step 4 — Validate Spec Quality

Applies quality gates from `spec-system.md` to the resolved feature.

#### spec.md Quality Gates

| Gate | Rule |
|---|---|
| Flowcharts | Every user story has a Mermaid flowchart |
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

For each baseline in `.specs/features/NNN-feature-name/baselines/`:

1. Run the visual test command from `.specs/testing/strategy.md` or `plan.md` **Resolved Test Commands**
2. If no visual testing tool is resolved → skip and report: "Visual drift detection skipped — no visual testing tool resolved"
3. Compare with stored baselines using pixel diff
4. Report:
   - ✅ Match — within threshold (< 2% diff)
   - 🖼️ Drift — exceeds threshold, show diff percentage
   - ❌ Missing — baseline file not found (capture needed)

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

| Feature | Spec Quality | Code Alignment | Visual | Overall |
|---|---|---|---|---|
| 004-notifications | ⚠️ 8/10 | ⚠️ 50% verified | 🖼️ 1 drift | ⚠️ Needs attention |
| 001-user-auth | ✅ 10/10 | ✅ 95% verified | ✅ All match | ✅ Healthy |
| 003-messaging | ✅ 9/10 | ❌ 30% verified | N/A | ❌ Critical |
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
| `--update` | Automatically update `implementation.md` without asking |
| `--no-visual` | Skip visual diff comparison |
| `--fix` | After reporting, attempt to fix ❌ Missing items automatically |
| `--report [path]` | Save gap report to specified file instead of printing |
| `--tree-only` | Only validate tree structure, skip per-feature checks |
| `--skip-tree` | Skip tree validation (for quick single-feature check) |
| `--quality` | Only validate spec quality gates, skip code alignment |
| `--all` | Check all features without prompting for selection |
| `--summary` | Multi-spec: only display the consolidated report |

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
