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

### Step 8 — Generate Testing Strategy

Based on `.specs/testing/strategy.md`, map each test type to specific files:

```markdown
| Test Type | What | File | FR/AC |
|---|---|---|---|
| Unit | getUnreadNotifications() | src/data/notifications.test.ts | FR-001 |
| Integration | GET /api/notifications | tests/api/notifications.test.ts | AC-001 |
| E2E | Full notification flow | tests/e2e/notifications.spec.ts | AC-001, AC-002 |
| Visual | Notification panel states | tests/e2e/notifications.spec.ts | SC-004 |
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

*LiveSpec Command v1.0*
