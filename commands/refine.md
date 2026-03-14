---
description: "Refine existing spec artifacts through guided conversation"
argument-hint: "<target>"
---

# Command: /spec.refine

> Iteratively refine existing LiveSpec artifacts (project, feature spec, or plan) through guided conversation — without risking downstream inconsistencies.

---

## Overview

```
/spec.refine                       → Interactive menu (scan .specs/, select target)
/spec.refine project               → Refine project-level artifacts
/spec.refine NNN                   → Refine feature spec (by number)
/spec.refine feature-name          → Refine feature spec (by name)
/spec.refine NNN plan              → Refine feature plan
/spec.refine feature-name plan     → Refine feature plan
```

---

## Refine Eligibility Rules

Not all artifacts can be refined. Once an artifact has been consumed by the next pipeline stage, modifying it upstream would create inconsistencies with existing code.

### Feature Spec (`spec.md`)

| Status | Refine allowed? | Reason |
|---|---|---|
| Draft | ✅ Yes | Not yet planned |
| Review | ✅ Yes | Not yet planned |
| Approved | ✅ Yes | Not yet planned |
| Planned | ⚠️ Yes, with warning | A plan exists — it will need regeneration |
| In Progress | ❌ No | Code exists — spec modification would break traceability |
| Implemented | ❌ No | Code exists — spec modification would break traceability |
| Deprecated | ❌ No | Feature abandoned |

### Plan (`plan.md`)

| Condition | Refine allowed? |
|---|---|
| `plan.md` exists, no `implementation.md` | ✅ Yes |
| `implementation.md` exists (even partial) | ❌ No — code already follows this plan |

### Project (project.md, constitution.md, testing/strategy.md)

| Condition | Refine allowed? |
|---|---|
| Always | ✅ Yes — project-level artifacts evolve continuously |

### Blocked Message Format

When refine is not allowed, display:

```
✗ Cannot refine this artifact.

  Feature "NNN-feature-name" has status: [status]
  Modifying the [spec/plan] would create inconsistencies with existing code.

  Options:
  → /spec.feature "description"  — create a new feature for the changes
  → /spec.check NNN              — verify current spec ↔ code alignment
```

---

## Steps

### Step 0 — Interactive Menu (no argument)

If `/spec.refine` is called without argument:

1. Scan `.specs/` for existing artifacts
2. For each feature in `.specs/features/NNN-*/`:
   - Read `spec.md` header to extract Status
   - Check if `plan.md` exists
   - Check if `implementation.md` exists
3. Present the menu:

```
What would you like to refine?

1. Project
   ├── Project profile (project.md)
   ├── Constitution (constitution.md)
   └── Testing strategy (testing/strategy.md)

2. Feature spec
   ├── 001-user-auth          [Draft]
   ├── 002-job-listings       [Planned]     ⚠️ plan exists
   ├── 003-notifications      [Implemented] 🔒 locked
   └── 004-search             [Draft]

3. Plan
   ├── 001-user-auth          [plan.md ✓]
   ├── 002-job-listings       [plan.md ✓]   🔒 implementation.md exists
   └── 003-notifications      [plan.md ✓]   🔒 implementation.md exists
   (only features with plan.md are listed)
```

Features with status In Progress/Implemented/Deprecated show `🔒 locked`.
Plans with `implementation.md` show `🔒 implementation.md exists`.

The user selects a target → enter the corresponding flow.

If an argument is provided, skip this menu and enter the flow directly.

---

## Flow: Project (`/spec.refine project`)

### Step 1 — Read Current State

Read all project-level artifacts:
- `.specs/project.md`
- `.specs/constitution.md`
- `.specs/stacks/_default.md`
- `.specs/testing/strategy.md`

### Step 2 — Present Summary

```
## Current Project Profile

- Vision: [extracted from project.md]
- Users: N roles defined
- Stack: [from _default.md]
- Architecture principles: N
- ADRs: N decisions recorded
- Testing strategy: [summary]

What would you like to refine?
1. Users, roles, or constraints (project.md)
2. Architecture principles (constitution.md)
3. Testing strategy (testing/strategy.md)
4. Describe your change freely
```

### Step 3 — Targeted Conversation

Unlike `/spec.init` which asks 6 sequential questions, refine asks **1-3 targeted questions** based on the selected area:

- If adding a user role → ask: role name, permissions, key scenarios
- If modifying a principle → ask: which principle, what's the new constraint, why
- If updating testing → ask: what changed, new tool or strategy shift

**Max 2 clarifying questions** (same ambiguity cap as all commands).

### Step 4 — Modification by Diff

**CRITICAL: Never regenerate a file from scratch.**

1. Read the current file content
2. Identify the specific sections to modify
3. Present a before/after diff to the user:

```
## Proposed Changes to project.md

### Section: User Roles

- Before: 3 roles (Admin, Designer, Client)
+ After: 4 roles (Admin, Designer, Client, **Reviewer**)
+   - Reviewer: read-only access, can leave comments on deliverables

Apply these changes? (yes / no / modify)
```

4. Apply only after confirmation (unless `--auto`)

### Step 4.5 — Stack Change Redirect

If the change is clearly a stack change (adding/replacing a technology, framework swap, database migration), redirect:

```
This looks like a stack change. Redirecting to /spec.stack which has dedicated
impact analysis and ADR creation logic.

→ /spec.stack change "description of the change"
```

### Step 5 — Apply and Record

1. Apply the approved changes
2. Add entry to `.specs/changelog.md`:
   `[Project] Refined: [description of change]`
3. Update the `Last updated` date in `.specs/README.md`

---

## Flow: Feature Spec (`/spec.refine NNN`)

### Step 1 — Resolve Feature

Same resolution logic as `/spec.check`:
1. If NNN provided: find `.specs/features/NNN-*/`
2. If name provided: match against feature directory names
3. If ambiguous: list features and ask user to choose

### Step 2 — Eligibility Check

Read Status from `spec.md` header. Apply eligibility rules:

- **Draft / Review / Approved**: proceed
- **Planned**: proceed with warning:
  ```
  ⚠️ Feature 002-job-listings has status: Planned
  A plan.md already exists. Changes to the spec may require regenerating the plan.

  After this refinement, run: /spec.plan 002

  Continue? (yes / no)
  ```
- **In Progress / Implemented / Deprecated**: block (see Blocked Message Format above)

### Step 3 — Read Spec + Context

- Read `.specs/features/NNN-*/spec.md`
- Read `.specs/project.md`, `.specs/constitution.md`, `.specs/stacks/_default.md` (context)

### Step 4 — Present Current State

```
## Feature: Job Listings (002)

- Status: Draft
- Stories: 3 (1×P1, 1×P2, 1×P3)
- Acceptance Criteria: 5 (AC-001 → AC-005)
- Functional Requirements: 6 (FR-001 → FR-006)
- Edge Cases: 3
- Success Criteria: 2

What would you like to refine?
1. Add or modify user stories
2. Refine acceptance criteria
3. Add edge cases
4. Modify functional requirements
5. Change priorities
6. Describe your change
```

### Step 5 — Targeted Conversation + Generation

Based on user selection:

- **Adding a story** → generate with Mermaid flowchart (MANDATORY), Given/When/Then scenarios, and associated AC/FR
- **Modifying AC** → show the current AC, present diff
- **Adding edge cases** → propose associated AC/FR if relevant
- **Changing priorities** → show current priority distribution, confirm impact

**Max 2 clarifying questions.**

### Step 6 — Numbering Rule (CRITICAL)

**NEVER renumber existing items.**

- New AC take the next number after the highest existing: if AC-005 exists, new ones start at AC-006
- New FR take the next number after the highest existing: if FR-006 exists, new ones start at FR-007
- Existing numbers NEVER change, even if an item is removed
- Gaps in numbering are explicitly acceptable

**Why:** `@spec AC-003` anchors exist in source code and in `implementation.md`. Renumbering would silently break all traceability links.

### Step 7 — Quality Gates

Same quality gates as `/spec.specify` Step 6:

- [ ] Every user story has a Mermaid flowchart
- [ ] All AC are in Given/When/Then format
- [ ] All FR reference at least one AC
- [ ] No more than 3 `[NEEDS CLARIFICATION]` markers

If validation fails, fix before applying.

### Step 8 — Downstream Warning

If `plan.md` exists, display:

```
⚠️ Downstream Impact

- plan.md exists → new FR may need implementation steps
  → Run /spec.plan NNN to regenerate the plan
```

### Step 9 — Apply and Record

1. Apply changes to `spec.md`
2. Add entry to `.specs/features/NNN-*/changelog.md`:

```markdown
### YYYY-MM-DD — Spec Update: [description]

- **Type:** Spec Update
- **Spec modified:** Yes (sections: [list modified sections])
- **Code modified:** None
- **AC impacted:** [list new/modified AC]
- **Author:** [tool name]
```

3. Add summary to `.specs/changelog.md`:
   `[Feature NNN] Spec refined: [description] — [details: +N AC, +N FR, etc.]`
4. Update the `Last updated` date in `.specs/README.md`

### Step 10 — Loop or End

```
Continue refining? (yes / no)

If done → Next action: /spec.plan NNN (if plan needs update) or /spec.check NNN
```

---

## Flow: Plan (`/spec.refine NNN plan`)

### Step 1 — Resolve Feature

Same resolution logic as feature flow.

### Step 2 — Eligibility Check

1. Verify `plan.md` exists — if not, redirect to `/spec.plan NNN`
2. Check if `implementation.md` exists:
   - **No**: proceed
   - **Yes**: block:
     ```
     ✗ Cannot refine the plan for feature NNN-feature-name.

       implementation.md exists — code has already been written following this plan.
       Modifying the plan would create inconsistencies with existing implementation.

       Options:
       → /spec.feature "description"  — create a new feature for the changes
       → /spec.check NNN              — verify current plan ↔ code alignment
     ```

### Step 3 — Read Plan + Spec

- Read `.specs/features/NNN-*/plan.md`
- Read `.specs/features/NNN-*/spec.md` (plan must stay coherent with spec)

### Step 4 — Present Current State

```
## Plan: Job Listings (002)

- Implementation steps: N
- Diagrams: sequence ✓, state ✓, ER ✗
- Constitution check: ✓
- Test commands resolved: ✓
- FR coverage: N/N

What would you like to refine?
1. Add or modify implementation steps
2. Add/modify a diagram (sequence, state, ER)
3. Modify the technical approach
4. Describe your change
```

### Step 5 — Targeted Conversation + Diff

Same principle as feature flow:
- Targeted questions based on selection
- Present before/after diff
- Confirm before applying

### Step 6 — Re-validation

After applying changes:
- Verify all FR from `spec.md` are still covered in the plan
- Verify Constitution Check section is still valid
- Verify Resolved Test Commands are still accurate

Report any new gaps.

### Step 7 — Apply and Record

1. Apply changes to `plan.md`
2. Add entry to `.specs/features/NNN-*/changelog.md`:

```markdown
### YYYY-MM-DD — Plan Update: [description]

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None (plan.md updated)
- **AC impacted:** None (pre-implementation)
- **Author:** [tool name]
```

3. Add summary to `.specs/changelog.md`:
   `[Feature NNN] Plan refined: [description]`
4. Update the `Last updated` date in `.specs/README.md`

---

## Edge Cases

### Recent `/spec.check` report

If a `checks/YYYY-MM-DD.md` file exists from the last 7 days, read it and use identified gaps as refinement suggestions:

```
ℹ️ Recent check report found (YYYY-MM-DD)
  Identified gaps: AC-004 missing Given/When/Then, FR-006 not covered in plan

  Would you like to address these gaps? (yes / no)
```

### Session without changes

If the user explores but makes no modifications, exit cleanly:

```
No changes applied. Exiting refine.
```

No changelog entry is created.

### Stack change detected

If the project refinement involves adding/replacing a technology, redirect to `/spec.stack change` which has dedicated impact analysis and ADR creation.

---

## Flags

| Flag | Behavior |
|---|---|
| `--auto` | Apply changes without confirmation prompts |
| `--dry-run` | Show proposed changes without applying them |

---

## Definition of Done (Command-Level)

`/spec.refine` is complete only if all are true:

- [ ] Eligibility check passed (artifact is refinable)
- [ ] Changes presented as diff (before/after)
- [ ] Changes applied to target file(s)
- [ ] Existing numbering preserved (no renumbering of AC/FR/SC)
- [ ] Quality gates pass after refinement
- [ ] Feature `changelog.md` has a refinement entry (if feature/plan flow)
- [ ] Global `.specs/changelog.md` has a summary entry
- [ ] `.specs/README.md` Last updated date refreshed
- [ ] Downstream warnings displayed when applicable
- [ ] Next action proposed

If no changes were made during the session, none of the above are required.

---

*LiveSpec Command v1.0*
