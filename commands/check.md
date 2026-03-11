# Command: /spec.check

> Compare spec vs actual code — find gaps, verify AC coverage, detect visual drift.

---

## Overview

`/spec.check [feature-name]`

Reads the spec, reads the code, and produces a gap report showing what's implemented, what's missing, and what has drifted.

This is the "living document" enforcement command — it keeps specs and code in sync.

---

## Steps

### Step 1 — Resolve Feature

1. If feature name provided: find `.specs/features/NNN-feature-name/`
2. If no feature name: detect from current git branch (`feature/NNN-feature-name`)
3. If still ambiguous: list all features and ask user to choose

### Step 2 — Read Spec Requirements

From `.specs/features/NNN-feature-name/spec.md`, extract:
- All Acceptance Criteria (AC-001, AC-002, ...)
- All Functional Requirements (FR-001, FR-002, ...)
- All Success Criteria (SC-001, SC-002, ...)

### Step 3 — Read Implementation Map

From `.specs/features/NNN-feature-name/implementation.md`, get:
- FR → file:line mappings
- AC → test file mappings
- Visual baselines list
- Known gaps from last check

### Step 4 — Verify Implementation

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

### Step 5 — Detect Visual Drift (UI features)

For each baseline in `.specs/features/NNN-feature-name/baselines/`:

1. Run Playwright to capture current screenshots
2. Compare with stored baselines using pixel diff
3. Report:
   - ✅ Match — within threshold (< 2% diff)
   - 🖼️ Drift — exceeds threshold, show diff percentage
   - ❌ Missing — baseline file not found (capture needed)

```bash
# Run visual comparison
npx playwright test tests/e2e/notifications.spec.ts --reporter=html
```

### Step 6 — Produce Gap Report

Output a structured gap report:

```markdown
## Gap Report: notifications (004)

**Checked:** 2024-03-20
**Feature:** `.specs/features/004-notifications/`

### Functional Requirements

| FR | Description | Status | Location | Notes |
|---|---|---|---|---|
| FR-001 | Fetch unread notification count | ✅ Verified | `src/data/notifications.ts:12-34` | |
| FR-002 | Real-time count updates | ✅ Verified | `src/hooks/useNotificationSubscription.ts:8-52` | |
| FR-003 | Mark notification as read | ✅ Verified | `src/data/notifications.ts:36-48` | |
| FR-004 | Navigate to notification target | ⚠️ Partial | `src/components/notifications/NotificationItem.tsx:22-31` | No fallback for missing target_url |
| FR-005 | Notification preferences endpoint | 🔄 Drifted | `src/api/notifications/route.ts:78-112` | Added new fields not in spec |
| FR-006 | Mark all notifications as read | ❌ Missing | — | Not implemented |

### Acceptance Criteria

| AC | Description | Status | Test | Notes |
|---|---|---|---|---|
| AC-001 | Unread count displays as badge | ✅ Verified | `tests/api/notifications.test.ts:18` | |
| AC-002 | Click marks as read and navigates | ✅ Verified | `tests/e2e/notifications.spec.ts:34` | |
| AC-003 | User can disable email notifications | ⚠️ Partial | `tests/api/notifications.test.ts:67` | Test exists but doesn't cover all cases |
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

### Step 7 — Suggest Fixes

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

**If intentional:** Run `npx playwright test --update-snapshots` to update the baseline, then commit.
**If unintentional:** Revert the CSS change in `NotificationBell.tsx`.
```

### Step 8 — Update implementation.md (optional)

> Would you like me to update `implementation.md` with the current status from this check?
> This will mark drifted/partial items accurately.
>
> Type **yes** to update, **no** to skip.

---

## Output

```
Gap report printed to console.

Optionally updated:
.specs/features/004-notifications/implementation.md  ← Status updated
```

---

## Flags

| Flag | Behavior |
|---|---|
| `--update` | Automatically update `implementation.md` without asking |
| `--no-visual` | Skip visual diff comparison |
| `--fix` | After reporting, attempt to fix ❌ Missing items automatically |
| `--report [path]` | Save gap report to specified file instead of printing |
| `--ci` | Exit with non-zero code if any ❌ or 🖼️ found (for CI use) |

---

## CI Integration

Add to your CI pipeline to prevent spec drift:

```yaml
# .github/workflows/spec-check.yml
name: Spec Check
on: [pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: /spec.check --ci --no-visual
```

---

*LiveSpec Command v1.0*
