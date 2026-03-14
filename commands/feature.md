---
description: "Full feature pipeline: specify → plan → review → implement"
argument-hint: "<feature description>"
---

# Command: /spec.feature

> End-to-end feature pipeline — chains specify, plan, plan review, and implement with validation gates between each phase.

---

## Overview

`/spec.feature [feature description]`

Runs the full LiveSpec pipeline in a single command:

```
Phase 1: Specify     →  Phase 1.5: Spec Review (verifier)
                     →  Gate: user validates spec + review
Phase 2: Plan        →  Phase 2.5: Plan Review (verifier)
                     →  Gate: user validates plan + review
Phase 3: Implement
```

---

## Flags

| Flag | What it does |
|------|-------------|
| `--auto` | Skip gates after plan and implement. The gate after specify is **always active** (the spec must be validated). If plan review is BLOCKING → re-generates the plan (max 2 iterations), then aborts if still blocking |
| `--resume` | Resume the pipeline where it stopped (reads `pipeline.md`). Also passed to implement for step-level resume via `progress.md` |
| `--branch` | Create a git branch `feature/NNN-name` automatically after spec creation (no question asked) |
| `--no-branch` | Skip the branch proposal entirely |
| `--priority P1\|P2\|P3` | Force all user stories in the spec to the given priority (P1=critical/MVP, P2=important, P3=nice-to-have) |
| `--mono` | Use a single agent for implementation instead of the 4 specialized agents (implementer, verifier, tester, documenter) |
| `--economy` | No sub-agents, direct tools only — uses fewer tokens but slower |
| `--step` | Pause after each implementation step for manual validation |

> **Note:** Flags like `--no-review`, `--no-visual`, `--no-save`, and `--no-contracts` are intentionally **not** available on `/spec.feature`. This pipeline enforces all safety gates. These flags remain available on their respective sub-commands (`/spec.plan --no-contracts`, `/spec.implement --no-visual`, etc.) for power users running manual flows.

---

## State Tracking

Create `.specs/features/NNN-feature-name/pipeline.md` to track pipeline state.

This file is **distinct from `progress.md`** (which tracks individual implementation steps).

**Template:**

```markdown
# Pipeline — [Feature Name]

**Started:** YYYY-MM-DD HH:MM
**Flags:** `--auto --mono` (or `none`)

| Phase | Status | Completed At |
|-------|--------|--------------|
| Specify | Pending | — |
| Spec Review | Pending | — |
| Plan | Pending | — |
| Plan Review | Pending | — |
| Implement | Pending | — |
```

**Status values:** `Pending` → `In Progress` → `Done` or `Skipped`

Update the status and timestamp after each phase completes.

---

## Phase 1 — Specify

1. Update `pipeline.md`: Specify → `In Progress`
2. Execute the steps described in `commands/specify.md`, passing:
   - The feature description from the user
   - `--priority` if provided
3. Update `pipeline.md`: Specify → `Done` with timestamp

### Branch proposal

After the spec is created, determine whether a git branch is needed:

- **`--branch` provided:** Create `feature/NNN-name` immediately, no question asked.
- **`--no-branch` provided:** Skip entirely, no proposal.
- **Neither flag (default):** Analyze the generated spec's scope. Only propose a branch when the feature clearly warrants one (multi-file changes, new feature, breaking change). If the scope is small (single-file fix, documentation-only, minor tweak), do not propose — proceed without a branch.

> **When proposing:**
> [One sentence explaining why a branch is needed for this feature.]
> Create branch `feature/NNN-name`? (yes / no)

---

## Phase 1.5 — Spec Review

1. Update `pipeline.md`: Spec Review → `In Progress`
2. Dispatch the **livespec-verifier** agent in `spec-review` mode with:
   - Path to `spec.md`
   - Path to `.specs/constitution.md`
   - Path to `.specs/project.md`
   - Path to the stack file (e.g., `.specs/stacks/_default.md`)
3. Collect the Spec Review Report

The review findings are **embedded in the specify gate prompt** — the user sees both the spec and the review at once.

**Gate (always active, even with `--auto`):**

> Phase 1 complete. Review the generated spec:
> `.specs/features/NNN-feature-name/spec.md`
>
> ### Spec Review Findings
> [Verifier report inserted here — findings table with severity]
>
> N BLOCKING, N WARNING, N INFO finding(s).
> Type **continue** to proceed to planning, or describe changes needed.

4. Update `pipeline.md`: Spec Review → `Done` with timestamp

**If verdict is BLOCKING:**

- The user sees the BLOCKING findings in the gate prompt. They can:
  1. **Fix** — describe changes, the spec is regenerated and re-reviewed
  2. **Override** — proceed to planning despite blocking findings
  3. **Abort** — stop the pipeline

The specify gate is **always active**. The spec is the functional contract — it must be validated before launching plan + implement. `--auto` takes effect starting from Phase 2 (plan → review → implement without pause).

---

## Phase 2 — Plan

1. Update `pipeline.md`: Plan → `In Progress`
2. Execute the steps described in `commands/plan.md`, passing:
   - The resolved feature name
3. Update `pipeline.md`: Plan → `Done` with timestamp

---

## Phase 2.5 — Plan Review

1. Update `pipeline.md`: Plan Review → `In Progress`
2. Dispatch the **livespec-verifier** agent in `plan-review` mode with:
   - Path to `spec.md`
   - Path to `plan.md`
   - Path to `.specs/constitution.md`
3. Present the Plan Review Report to the user
4. Update `pipeline.md`: Plan Review → `Done` with timestamp

**If verdict is BLOCKING:**

- **Interactive mode:** Present findings and ask user how to proceed:
  > Plan review found N BLOCKING issue(s). Options:
  > 1. **Fix** — I'll regenerate the plan addressing the findings
  > 2. **Override** — proceed to implementation despite blocking findings
  > 3. **Abort** — stop the pipeline

- **`--auto` mode:** Automatically regenerate the plan (go back to Phase 2) with the review findings as additional context. Maximum 2 re-generation attempts. If still BLOCKING after 2 attempts, abort the pipeline with error.

**Gate (interactive mode, verdict PASS):**

> Plan review passed. Review the plan:
> `.specs/features/NNN-feature-name/plan.md`
>
> Type **continue** to proceed to implementation, or describe changes needed.

In `--auto` mode: skip gate, proceed immediately.

---

## Phase 3 — Implement

1. Update `pipeline.md`: Implement → `In Progress`
2. Execute the steps described in `commands/implement.md`, passing:
   - The resolved feature name
   - `--mono` if provided
   - `--economy` if provided
   - `--step` if provided
   - `--resume` if provided (implement uses `progress.md` for its own resume)
3. Update `pipeline.md`: Implement → `Done` with timestamp

---

## Resume (`--resume`)

When `--resume` is provided:

1. Read `.specs/features/NNN-feature-name/pipeline.md`
2. Find the first phase with status != `Done` and != `Skipped`
3. Resume execution from that phase
4. If pipeline.md doesn't exist, start from Phase 1

**Feature resolution for resume:** If no feature description is provided with `--resume`, look for the most recently modified `pipeline.md` across all feature directories.

---

## Completion

When all phases are done, display:

> **Pipeline complete!**
>
> - Spec: `.specs/features/NNN-feature-name/spec.md`
> - Plan: `.specs/features/NNN-feature-name/plan.md`
> - Review: PASS (or SKIPPED)
> - Implementation: Done
>
> **Next:**
> - Verify: `/spec.check NNN-feature-name`
> - Next feature: `/spec.propose`

---

## Error Handling

If any phase fails:

1. Update `pipeline.md` with current status (the failed phase stays `In Progress`)
2. Display error with recovery instructions:
   > Phase N failed: [reason]
   >
   > Resume with: `/spec.feature --resume [feature-name]`
3. Do **not** continue to subsequent phases

---

## Examples

```bash
# Full pipeline — interactive (recommended for first use)
/spec.feature "User can filter search results by date range"

# Full pipeline — automatic, no pauses
/spec.feature "Add CSV export to reports" --auto

# Resume an interrupted pipeline
/spec.feature --resume csv-export

# Pipeline with single-agent implementation
/spec.feature "Real-time notifications" --mono

# Pipeline with specify flags
/spec.feature "Payment processing" --branch --priority P1
```

---

*LiveSpec Command v1.0*
