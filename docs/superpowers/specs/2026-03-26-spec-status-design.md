# Design: /spec.status — Factual Status Overview

> **Date:** 2026-03-26
> **Status:** Draft
> **Scope:** 1 command created + 3 files updated (spec-system.md, init.md, README.md)

---

## Problem

LiveSpec has no quick way to see the factual state of a project's spec system. `/spec.propose` gives intelligent recommendations but is slow (full gap analysis) and ephemeral (nothing saved). The user needs a fast, factual snapshot: what's in the roadmap, what's the status of each feature, and what action should come next.

---

## Design

### 1. New Command: `/spec.status`

A **read-only** command that displays a factual overview of the project's spec system.

```
/spec.status                  → Full status (roadmap + features)
/spec.status --roadmap        → Roadmap only
/spec.status --features       → Features only
/spec.status --json           → Machine-readable JSON output
```

### 2. Output Format

#### Summary Header

```
📊 LiveSpec Status — [Project Name]

  Roadmap:  12 items (4 ✅ specified, 8 ⬜ pending) · 2 deferred
  Features: 4 specs (1 Implemented, 1 In Progress, 1 Planned, 1 Draft)
```

#### Roadmap Section (skipped if no `roadmap.md`)

```
## Roadmap

### MVP (5 items — 3 ✅, 2 ⬜)
  ✅ User auth → 001-user-auth [Implemented]
  ✅ Job listings → 002-job-listings [Planned]
  ✅ Designer profiles → 003-designer-profiles [Draft]
  ⬜ Bidding system · Scope: L · Deps: job-listings, profiles
  ⬜ Messaging · Scope: L · Deps: auth

### Post-MVP (4 items — 1 ✅, 3 ⬜)
  ✅ Notifications → 004-notifications [Draft]
  ⬜ Payments · Scope: L · Deps: bidding
  ⬜ Admin dashboard · Scope: L · Deps: auth
  ⬜ Search & discovery · Scope: M

### Future (3 items — 0 ✅, 3 ⬜)
  ⬜ Reviews & ratings · Scope: S
  ⬜ Analytics · Scope: M
  ⬜ i18n · Scope: M

### Deferred (2 items)
  Audit trail (from "auth + audit") · Scope: S · Added: 2026-03-20
  Role management (from "auth + roles") · Scope: M · Added: 2026-03-22
```

For checked items: show the feature link and its current status.
For unchecked items: show scope and dependencies.

#### Features Section

```
## Features

| # | Feature | Status | Plan | Impl | Next action |
|---|---------|--------|------|------|-------------|
| 001 | user-auth | Implemented | ✓ | ✓ | /spec.check 001 |
| 002 | job-listings | Planned | ✓ | — | /spec.implement 002 |
| 003 | designer-profiles | Draft | — | — | /spec.plan 003 |
| 004 | notifications | Draft | — | — | /spec.plan 004 |
```

**Next action logic:**

| Status | Has plan? | Has implementation? | Next action |
|--------|-----------|-------------------|-------------|
| Draft | No | No | `/spec.plan NNN` |
| Draft | Yes | No | `/spec.implement NNN` |
| Review | No | No | `/spec.plan NNN` |
| Approved | No | No | `/spec.plan NNN` |
| Planned | Yes | No | `/spec.implement NNN` |
| In Progress | Yes | Partial | `/spec.implement NNN --resume` |
| Implemented | Yes | Yes | `/spec.check NNN` |
| Deprecated | — | — | — (no action) |

#### Status Gaps (only if gaps detected)

```
## Attention

  ⚠ 1 feature has a spec but no plan — consider: /spec.plan 003
  ⚠ 2 deferred items pending — consider: /spec.propose
  ⚠ 1 feature stuck in Draft for >7 days — 003-designer-profiles (created 2026-03-18)
```

Only shown when there are actionable gaps. Silent if everything is progressing normally.

### 3. Steps

#### Step 1 — Read Project Context

1. Read `.specs/project.md` — extract project name
2. If `.specs/` does not exist, stop and suggest `/spec.init`

#### Step 2 — Read Roadmap (optional)

1. Read `.specs/roadmap.md` (if it exists)
2. Parse all tier sections — count checked/unchecked per tier
3. Parse Deferred section — count items
4. If `--features` flag is set, skip this step

#### Step 3 — Scan Features

1. Scan `.specs/features/*/spec.md` — extract name, status, creation date
2. For each feature, check if `plan.md` exists
3. For each feature, check if `implementation.md` exists
4. Compute next action based on status + plan + implementation presence
5. If `--roadmap` flag is set, skip this step

#### Step 4 — Detect Status Gaps

1. Features with Draft status and no plan for >7 days → flag as stuck
2. Features with Planned status and no implementation → flag as ready to implement
3. Deferred items count > 0 → suggest `/spec.propose`
4. Features with spec but no plan → suggest `/spec.plan`

#### Step 5 — Present Output

1. Display summary header with counts
2. Display roadmap section (if not `--features`)
3. Display features table (if not `--roadmap`)
4. Display attention section (if gaps detected)

#### Step 6 — JSON Output (if `--json`)

Instead of formatted text, output a JSON structure:

```json
{
  "project": "Project Name",
  "roadmap": {
    "mvp": { "total": 5, "specified": 3, "items": [...] },
    "postMvp": { "total": 4, "specified": 1, "items": [...] },
    "future": { "total": 3, "specified": 0, "items": [...] },
    "deferred": [...]
  },
  "features": [
    { "number": "001", "name": "user-auth", "status": "Implemented", "hasPlan": true, "hasImpl": true, "nextAction": "/spec.check 001" }
  ],
  "gaps": [
    { "type": "no_plan", "feature": "003", "suggestion": "/spec.plan 003" }
  ]
}
```

### 4. Flags

| Flag | Behavior |
|------|----------|
| `--roadmap` | Show roadmap section only |
| `--features` | Show features section only |
| `--json` | Output as JSON (machine-readable) |

### 5. Definition of Done

`/spec.status` is complete only if all are true:

- [ ] Project context was read (project.md exists)
- [ ] Roadmap was parsed (if exists and not `--features`)
- [ ] Feature inventory was scanned (if not `--roadmap`)
- [ ] Summary header displays correct counts
- [ ] Next action is computed for each feature based on status/plan/impl matrix
- [ ] Status gaps detected and displayed (if any)
- [ ] No files were created or modified (read-only command)

### 6. Integration Updates

#### spec-system.md

Add to command discovery list (line ~229):
- Add `/spec.status` to the 14 available commands list

Add to README.md update rules:
```
- `/spec.status` does not modify any files (read-only command)
```

#### init.md

Update command count references:
- Phase C CLAUDE.md section: add `/spec.status` to the command list
- Update "13 commands" → "14 commands" where referenced

#### README.md

Add to the commands table:
```markdown
| `/spec.status` | Display factual status overview of roadmap and features |
```

Update "The 13 Commands" → "The 14 Commands"

Add to Command Reference section:

```markdown
### `/spec.status`

Factual status overview — roadmap items, feature statuses, next actions. Read-only.

\`\`\`bash
/spec.status                  # Full status
/spec.status --roadmap        # Roadmap only
/spec.status --features       # Features only
/spec.status --json           # Machine-readable output
\`\`\`

Key flags: `--roadmap`, `--features`, `--json`
```

### 7. Edge Cases

| Case | Behavior |
|------|----------|
| No `.specs/` directory | Stop with: "LiveSpec not initialized. Run `/spec.init` first." |
| No roadmap.md | Skip roadmap section, show features only (no error) |
| No features yet | Show empty features table with hint: "No features yet. Run `/spec.specify` to create one." |
| No roadmap AND no features | Show minimal output: project name + "No roadmap or features yet." |
| `--roadmap` + no roadmap.md | Show: "No roadmap found. Run `/spec.init` to generate one." |
| `--json` + other flags | Combinable: `--json --roadmap` outputs roadmap JSON only |

### 8. Files Modified

| File | Change |
|------|--------|
| `commands/status.md` | **New file** — full command definition |
| `system/spec-system.md` | Add to command list (14 commands), add read-only rule |
| `commands/init.md` | Add `/spec.status` to CLAUDE.md command list |
| `README.md` | Add to commands table, command reference, update count 13→14 |

### 9. What This Does NOT Change

- No changes to any existing command behavior
- No changes to roadmap.md format
- No changes to feature spec format
- `/spec.propose` remains the intelligent recommendation engine — `/spec.status` is the factual dashboard
