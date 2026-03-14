---
description: "Analyze project context and propose the next feature(s) to build"
---

# Command: /spec.propose

> Analyze the full project context — vision, users, roles, existing features, and optional roadmap — and intelligently propose the next feature(s) to build, with priority reasoning.

---

## Overview

`/spec.propose [flags]`

A **read-only** command. No files are created or modified.

Use cases:
- After `/spec.init` — propose the first feature to build
- After completing a feature — propose what's next
- Manual invocation anytime — reassess priorities

---

## Steps

### Step 1 — Read Project Context

Read all available project-level artifacts:

1. `.specs/project.md` — vision, users, roles, constraints, scale
2. `.specs/constitution.md` — architecture principles
3. `.specs/stacks/_default.md` — chosen stack and rationale
4. `.specs/stacks/decisions/ADR-*.md` — architecture decision records

If `.specs/` does not exist, stop and suggest `/spec.init`.

### Step 2 — Scan Existing Features

Scan `.specs/features/*/spec.md` and extract for each feature:

- Feature name and number
- Status (Draft / Review / Approved / Implemented / Deprecated)
- User roles served (which roles appear in user stories)
- Key entities introduced
- Dependencies on other features (explicit or inferred)
- Priority distribution (P1/P2/P3 breakdown)

Build a **feature inventory** summary:

```
Feature Inventory:
  001-user-auth       [Implemented]  Roles: All         Entities: User, Session
  002-job-listings    [Implemented]  Roles: Client       Entities: Job, Category
  003-messaging       [Draft]        Roles: Designer, Client  Entities: Message, Thread
```

### Step 3 — Read Roadmap (Optional)

Check for `.specs/roadmap.md`. If present:

- Parse priority tiers (MVP / Post-MVP / Future)
- Identify unchecked items (not yet specified)
- Cross-reference with existing features to find gaps

If absent, skip and rely on AI inference in Step 4.

### Step 4 — Analyze Gaps

Perform gap analysis across five dimensions:

#### 4.1 — Role Coverage

Which user roles defined in `project.md` have no or few features?

```
Role Coverage:
  Designer  → 2 features (auth, messaging)
  Client    → 3 features (auth, job-listings, messaging)
  Admin     → 0 features ← GAP
```

#### 4.2 — Domain Coverage

Based on the project type and vision, what core capabilities are expected but missing? Consider:
- Authentication and authorization
- Core CRUD for primary entities
- Search and discovery
- Communication (messaging, notifications)
- Payments and billing
- Settings and preferences
- Admin and moderation tools
- Reporting and analytics

#### 4.3 — Dependency Analysis

Are there prerequisite features that should be built first to unblock others? Look for:
- Features referencing entities that don't exist yet
- Features that assume capabilities not yet implemented
- Natural build order (e.g., auth before profile, profile before messaging)

#### 4.4 — Status Gaps

Are there features stuck in intermediate states?
- Draft specs needing plans → suggest `/spec.plan`
- Planned features needing implementation → suggest `/spec.implement`
- Features needing verification → suggest `/spec.check`

#### 4.5 — MVP Critical Path

What is the minimum set of features for a working product? Identify features that are:
- Required for the core value proposition
- Required for any user role to complete their primary workflow
- Required before the product can be tested by real users

### Step 5 — Rank Candidates

Rank proposed features using this priority order:

1. **MVP criticality** — Is it required for a working product?
2. **Dependency unblocking** — Does it unblock other features?
3. **Role coverage** — Does it serve an underserved role?
4. **Scope fit** — Is it appropriately sized (prefer S/M over L)?
5. **Roadmap alignment** — Is it on the roadmap (if one exists)?

### Step 6 — Present Proposal(s)

Present the top N proposals (default: 1, configurable via `--count`).

**Single proposal format:**

> ### Proposed Next Feature
>
> **Feature:** [Feature name]
> **Description:** [1-2 sentence description of what the feature does]
> **User roles:** [Which roles benefit]
> **Why next:** [2-3 sentences explaining why this is the highest priority]
> **Dependencies:** [Features this depends on, or "None"]
> **Estimated scope:** [S / M / L]
>
> ```
> /spec.specify "[Feature description]"
> ```
>
> Or run the full pipeline:
> ```
> /spec.feature "[Feature description]"
> ```

**Multiple proposals format (when `--count > 1`):**

> ### Proposed Features (ranked)
>
> | # | Feature | Roles | Why | Scope |
> |---|---------|-------|-----|-------|
> | 1 | [Name] | [Roles] | [Short reason] | S/M/L |
> | 2 | [Name] | [Roles] | [Short reason] | S/M/L |
> | 3 | [Name] | [Roles] | [Short reason] | S/M/L |
>
> **Top pick — [Feature 1 name]:**
> [Detailed reasoning for #1]
>
> Quick start:
> ```
> /spec.specify "[Feature 1 description]"
> ```

### Step 7 — Offer Actions

Unless `--auto` is provided, end with actionable next steps:

> **Actions:**
> - Create this feature: `/spec.specify "[description]"`
> - Full pipeline: `/spec.feature "[description]"`
> - See more proposals: `/spec.propose --count 3`
> - Focus on a role: `/spec.propose --role admin`

With `--auto`: display the proposal(s) and exit — no action prompt.

---

## Flags

| Flag | Behavior |
|------|----------|
| `--count N` | Number of proposals to generate (default: 1, max: 5) |
| `--role [name]` | Focus proposals on a specific user role |
| `--mvp` | Only propose MVP-critical features |
| `--auto` | Display proposals and exit (no action prompt) |

---

## Edge Cases

### No features yet (post-init)

When `.specs/features/` is empty or doesn't exist:

- Focus on foundational features (auth, core entity CRUD, primary user workflow)
- Reference `project.md` heavily for guidance
- Suggest the feature that delivers the first end-to-end user value

> No features exist yet. Based on your project profile, here's where to start:

### All MVP features done

When all roles have coverage and core workflows are complete:

- Shift to enhancement proposals (search, filtering, analytics, notifications)
- Suggest quality-of-life improvements
- Reference the roadmap's Post-MVP tier if available

> Core MVP features are in place. Here are enhancement opportunities:

### Roadmap exists

When `.specs/roadmap.md` is present:

- Prioritize unchecked items from the MVP tier
- Cross-reference with feature inventory to avoid suggesting already-specified features
- If all MVP items are checked, move to Post-MVP tier

### Status gaps detected

When features are stuck in intermediate states:

- Mention blocked features before proposing new ones
- Suggest completing in-progress work first

> **Note:** 1 feature has a spec but no plan. Consider completing it first:
> - `/spec.plan 003-messaging`

---

## Examples

```bash
# Propose the next feature to build
/spec.propose

# Propose 3 features ranked by priority
/spec.propose --count 3

# Focus on admin role features
/spec.propose --role admin

# Only MVP-critical suggestions
/spec.propose --mvp

# Display and exit (no action prompt)
/spec.propose --auto

# Combine flags
/spec.propose --count 3 --mvp --auto
```

---

## Definition of Done (Command-Level)

`/spec.propose` is complete only if all are true:

- [ ] Project context was read (project.md, constitution.md, stack)
- [ ] Feature inventory was scanned (or confirmed empty)
- [ ] Roadmap was checked (present or absent noted)
- [ ] Gap analysis was performed across all 5 dimensions
- [ ] At least 1 proposal was presented with: description, roles, reasoning, dependencies, scope
- [ ] Actionable `/spec.specify` or `/spec.feature` command was provided
- [ ] No files were created or modified (read-only command)

---

*LiveSpec Command v1.0*
