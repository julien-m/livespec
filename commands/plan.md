---
description: "Generate technical plan with sequence, state, and ER diagrams"
argument-hint: "<feature-name>"
---

# Command: /spec.plan

> Generate a technical plan with sequence, state, and ER diagrams from a feature spec.

---

## Overview

`/spec.plan [feature-name]`

Reads the spec.md and generates a complete `plan.md` with:
- Technical context (stack-aware)
- Mermaid sequence, state, and ER diagrams
- File-by-file implementation plan
- Testing strategy

---

## Steps

### Step 1 — Resolve Feature

1. If feature name provided: find `.specs/features/NNN-feature-name/`
2. If no feature name: use current git branch (parse NNN from branch name)
3. Verify `spec.md` exists — if not, prompt user to run `/spec.specify` first

### Step 2 — Read Context Files

Read ALL of these before generating anything:

```
.specs/features/NNN-feature-name/spec.md   ← WHAT to build
.specs/constitution.md                      ← Architectural constraints
.specs/stacks/_default.md                   ← Tech stack choices
.specs/testing/strategy.md                  ← How to test
.specs/project.md                           ← Project context (users, scale)
```

### Step 3 — Analyze Requirements

From the spec, extract:
- All Functional Requirements (FR-001, FR-002, ...)
- All Acceptance Criteria (AC-001, AC-002, ...)
- Key Entities (for ER diagram)
- User Stories with API interactions (for sequence diagrams)
- Entities with states/lifecycle (for state diagrams)

### Step 3.5 — Scope Sizing (Avoid Over-Planning)

Classify feature size before generating artifacts:

- **S (small):** <= 3 FR, no new entity, single API route
- **M (medium):** 4-8 FR, 1-2 entities, multiple interactions
- **L (large):** > 8 FR, cross-domain dependencies, migration risk

Apply output budget:

- S: 1 sequence diagram max, no ER unless new entity exists
- M: 1-2 sequence + state if lifecycle exists + ER if needed
- L: full set + explicit risk section with phased delivery

### Step 4 — Generate Technical Context

Auto-fill from `.specs/stacks/_default.md`:

```markdown
| Aspect | Choice | Reason |
|---|---|---|
| Language | TypeScript | From project stack |
| Framework | Next.js 14 | From stack preset |
| Database | Supabase PostgreSQL | From stack preset |
| Real-time | Supabase Realtime | Feature requires WebSocket |
| Testing | Vitest + Playwright | From testing strategy |
```

### Step 5 — Constitution Check

For each principle in `.specs/constitution.md`, verify the planned approach:
- Simplicity: is this the simplest solution?
- Separation: are UI, logic, and data properly separated?
- Testing: are all business logic functions unit-testable?
- Naming: do proposed file names follow conventions?

Mark each gate as ✅ or add a note if deviation is needed.

### Step 6 — Generate Mermaid Diagrams

#### Decision: Which diagrams to generate?

| Condition | Diagram to Generate |
|---|---|
| Feature has API calls or service interactions | ✅ Sequence diagram (MANDATORY) |
| Feature has an entity with multiple states | ✅ State diagram (MANDATORY) |
| Feature introduces new database tables | ✅ ER diagram (MANDATORY) |
| Feature is UI-only with no state or API | Only flowchart in spec (already done) |

#### Sequence Diagrams
- Map out every API call in the feature
- Show happy path first, then error paths with `alt` blocks
- Include all participants: User, Client, API, Database, external services
- Show real-time events separately if applicable

#### State Diagrams
- Identify all states an entity can be in
- Map transitions between states (what triggers each transition?)
- Add notes explaining business rules for key states
- Use `stateDiagram-v2` syntax

#### ER Diagrams
- Include all new tables introduced by the feature
- Include existing tables that are JOINed or referenced
- Show primary keys (PK), foreign keys (FK), and important fields
- Show relationships with cardinality (||, |{, etc.)

### Step 7 — Generate File-by-File Implementation Plan

For each FR, map to specific files:

1. **Database layer** — migrations, schema changes
2. **Data access layer** — query functions
3. **Business logic layer** — services
4. **API layer** — routes, handlers
5. **UI layer** — components, pages, hooks
6. **Test files** — unit, integration, E2E

For each file:
- State whether it's new or modified
- List the functions/components to create
- Reference which FR it satisfies

### Step 7.5 — Test Resolution

Before generating the testing strategy, resolve the project's test infrastructure:

1. **Read `.specs/testing/strategy.md`** — check if test commands are already resolved
2. **If not resolved**, follow the discovery procedure in `system/testing/test-protocol.md` Section 1:
   - Detect language/runtime
   - Detect test runners, linters, type checkers, visual testing tools
3. **Verify availability** of detected tools
4. **Record** resolved commands in the plan:

| Action | Command | Tool | Status |
|---|---|---|---|
| Unit tests | `[resolved]` | `[resolved]` | Verified / Not verified |
| Integration tests | `[resolved]` | `[resolved]` | Verified / Not verified |
| E2E tests | `[resolved]` | `[resolved]` | Verified / Not available |
| Visual tests | `[resolved]` | `[resolved]` | Verified / Not available |
| Type check | `[resolved]` | `[resolved]` | Verified / N/A |
| Lint | `[resolved]` | `[resolved]` | Verified / Not verified |
| Full suite | `[resolved]` | `[resolved]` | Verified / Not verified |

5. If a tool is missing → mark `[TOOL NEEDED: install command]` in the plan

### Step 8 — Generate Testing Strategy

Using the commands resolved in Step 7.5, map each test type to specific files based on `.specs/testing/strategy.md`:

```markdown
| Test Type | What | File | Command | FR/AC |
|---|---|---|---|---|
| Unit | getUnreadNotifications() | src/data/notifications.test.ts | `[resolved unit command] -- src/data/notifications.test.ts` | FR-001 |
| Integration | GET /api/notifications | tests/api/notifications.test.ts | `[resolved integration command] -- tests/api/notifications.test.ts` | AC-001 |
| E2E | Full notification flow | tests/e2e/notifications.spec.ts | `[resolved E2E command]` | AC-001, AC-002 |
| Visual | Notification panel states | tests/e2e/notifications.spec.ts | `[resolved visual command]` | SC-004 |
```

### Step 9 — Generate API Contracts (if applicable)

If the feature introduces new API endpoints:
1. Create `.specs/features/NNN-feature-name/contracts/` directory
2. Generate `openapi.yaml` with endpoint specifications
3. Include request/response schemas based on the ER diagram

### Step 10 — Present for Approval

> ✅ **Plan generated:** `.specs/features/004-notifications/plan.md`
>
> **Summary:**
> - 2 sequence diagrams (notification fetch, mark as read)
> - 1 state diagram (notification lifecycle)
> - 1 ER diagram (2 new tables: notifications, notification_preferences)
> - 7 implementation steps across 9 files
> - API contract: `contracts/openapi.yaml`
>
> **Constitution check:** All gates ✅
>
> Ready to implement? Run: `/spec.implement notifications`
> Or review the plan first in `.specs/features/004-notifications/plan.md`

---

## Output

```
.specs/features/004-notifications/
├── spec.md          ← Existing (read-only during plan)
├── plan.md          ← Generated now
└── contracts/
    └── openapi.yaml ← Generated if API endpoints exist
```

---

## Flags

| Flag | Behavior |
|---|---|
| `--auto` | Skip confirmation, generate plan silently |
| `--no-contracts` | Skip API contract generation |
| `--diagram-only` | Regenerate only the Mermaid diagrams in an existing plan |

---

## Definition of Done (Command-Level)

`/spec.plan` is complete only if all are true:

- [ ] `plan.md` generated in target feature directory
- [ ] Every FR appears in implementation plan mapping
- [ ] Diagram set matches feature size and real needs (not boilerplate)
- [ ] Constitution check contains explicit pass/deviation notes
- [ ] Test commands are resolved (Resolved Test Commands table filled)
- [ ] Testing strategy maps AC/FR to concrete test files
- [ ] Next action is proposed (`/spec.implement [feature]`)

If a requirement cannot be planned safely, mark it `[DECISION NEEDED]` with owner and unblock options.

---

*LiveSpec Command v1.0*
