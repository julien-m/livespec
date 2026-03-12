---
description: "Auto-implement from plan: analyze, code, test, map"
argument-hint: "<feature-name>"
---

# Command: /spec.implement

> APEX-style auto-pipeline: implement → test → visual baselines → map to spec.

---

## Overview

`/spec.implement [feature-name]`

Executes a full implementation pipeline from `plan.md` to working, tested, documented code.

---

## Pipeline Phases

### Phase 1 — Analyze

**Read everything before writing anything:**

1. `.specs/features/NNN-feature-name/spec.md` — requirements and acceptance criteria
2. `.specs/features/NNN-feature-name/plan.md` — implementation plan and diagrams
3. `.specs/constitution.md` — architectural rules
4. `.specs/stacks/_default.md` — stack and patterns to follow
5. `.specs/testing/strategy.md` — testing requirements

**Explore the codebase:**
- Find existing patterns matching what needs to be built
- Identify files that will need modification
- Locate test utilities and fixtures to reuse
- Understand naming conventions from existing code

**Verify prerequisites:**
- Does the plan.md exist? If not, prompt to run `/spec.plan` first
- Are there any `[DECISION NEEDED]` markers in the plan? Surface them before starting

### Phase 2 — Plan Execution

Create an ordered todo list from `plan.md`:

```
[ ] Step 1: Create database migration
[ ] Step 2: Create data access functions
[ ] Step 3: Create API endpoints
[ ] Step 4: Create UI components
[ ] Step 5: Create real-time subscription hook
[ ] Step 6: Write unit tests
[ ] Step 7: Write integration tests
[ ] Step 8: Write E2E tests
[ ] Step 9: Capture visual baselines
[ ] Step 10: Update implementation.md
[ ] Step 11: Update changelog.md
```

### Phase 3 — Execute

Work through each step:

1. **Read before write** — always read the target file before modifying it
2. **One step at a time** — complete each step fully before moving to next
3. **Follow existing patterns** — match the style and structure of surrounding code
4. **Track todos** — mark each step complete as it's done
5. **Constitution check** — verify each file follows constitution rules

**File naming and structure:**
- Follow conventions from `.specs/constitution.md`
- Match patterns from existing code (read similar files first)
- Never create God files — split at 300 lines

### Phase 4 — Test

After each implementation step, run the relevant tests immediately:

```bash
# After data layer
npm run test -- src/data/notifications.test.ts

# After API layer
npm run test -- tests/api/notifications.test.ts

# After UI components
npm run test -- src/components/notifications

# Full suite before proceeding to visual tests
npm run test
```

**On test failure:**
- Read the error message carefully
- Check if the spec/AC covers this case
- Fix the issue
- Re-run tests
- Max 3 iterations for unit/integration tests → then flag for human review

### Phase 5 — Visual Baselines (UI features only)

For features with UI components specified in the spec:

1. Run the Playwright E2E tests
2. On first run, Playwright captures screenshots as baselines:
   - Empty states
   - Loaded states with data
   - Interactive states (hover, open, etc.)
   - Error states
3. Baselines are saved to `.specs/features/NNN-feature-name/baselines/`
4. Commit baselines with the implementation

```bash
# Capture baselines
npx playwright test tests/e2e/notifications.spec.ts --update-snapshots

# On subsequent runs, compare against baselines
npx playwright test tests/e2e/notifications.spec.ts
```

**Max 5 iterations** for visual tests — then flag for human review with diff images.

### Phase 6 — Validate

Before declaring implementation complete:

```bash
# Type check
npx tsc --noEmit

# Lint
npx eslint src/ tests/

# All tests
npm run test

# E2E
npx playwright test
```

All must pass. Fix any issues found.

### Phase 7 — Update implementation.md

Create or update `.specs/features/NNN-feature-name/implementation.md`:

For every FR and AC, fill in:

```markdown
| FR-001 | src/data/notifications.ts | `@spec FR-001` | ✅ Implemented | 2024-03-15 |
| FR-002 | src/hooks/useNotificationSubscription.ts | `@spec FR-002` | ✅ Implemented | 2024-03-15 |
```

For every visual baseline:

```markdown
| panel-empty.png | .specs/features/004-notifications/baselines/ | 2024-03-15 | ✅ Active |
```

List all files created or modified.

### Phase 8 — Update changelog.md

Add an entry to `.specs/features/NNN-feature-name/changelog.md`:

```markdown
### 2024-03-15 — Feature: Initial implementation of notification system

- **Type:** Feature
- **Spec modified:** No
- **Code modified:** [list all files created/modified]
- **AC impacted:** [list ACs now satisfied]
- **Author:** [tool name, e.g., claude-code]
```

Also add a summary entry to `.specs/changelog.md` (global).

---

## Output

```
.specs/features/004-notifications/
├── spec.md              ← Unchanged
├── plan.md              ← Unchanged
├── implementation.md    ← Created/updated with FR→@spec mapping
├── changelog.md         ← Updated with new entry
└── baselines/           ← Playwright screenshots (if UI feature)
    ├── panel-empty.png
    ├── panel-unread.png
    └── bell-badge.png

src/                     ← New/modified source files
tests/                   ← New/modified test files
db/migrations/           ← New migration files
```

---

## Flags

| Flag | Behavior |
|---|---|
| `--auto` | Skip all confirmation prompts, full automatic pipeline |
| `--save` | Save execution logs to `.specs/features/NNN/logs/YYYY-MM-DD.md` |
| `--economy` | No subagents, direct tools only (slower but uses less tokens) |
| `--resume` | Resume an interrupted implementation (reads last todo checkpoint) |
| `--no-visual` | Skip visual baseline capture even if UI components are created |
| `--step [N]` | Start from step N (skip earlier steps, useful for partial re-runs) |

---

## Iteration Limits

| Test Type | Max Iterations | On Limit Exceeded |
|---|---|---|
| Unit tests | 3 | Stop, report failure with context, ask human |
| Integration tests | 3 | Stop, report failure with context, ask human |
| E2E tests | 5 | Stop, report failure with diffs, ask human |
| Visual tests | 5 | Stop, report diff images, ask human to review |
| TypeScript errors | 3 | Stop, show errors, ask human |

---

## Error Reporting Format

When max iterations are exceeded:

> ⛔ **Max iterations reached for [test type]**
>
> **Feature:** 004-notifications
> **Step:** Phase 4 — Test
> **Test:** `tests/api/notifications.test.ts:42`
>
> **Failing test:** `"AC-003: updates email notification preference"`
>
> **Error:**
> ```
> AssertionError: expected 200, received 422
> Response body: { error: "Invalid preference value" }
> ```
>
> **What I tried:**
> 1. Iteration 1: Added Zod validation schema
> 2. Iteration 2: Fixed schema to accept boolean values
> 3. Iteration 3: Added request body parsing middleware
>
> **Likely cause:** The API route doesn't have the body parser middleware applied.
>
> **Suggested fix:** Apply `express.json()` middleware before the preferences route.
>
> **Action needed:** Please review and fix, then run `/spec.implement notifications --resume`

---

*LiveSpec Command v1.0*
