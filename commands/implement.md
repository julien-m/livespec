---
description: "Auto-implement from plan: analyze, code, test, map"
argument-hint: "<feature-name>"
---

# Command: /spec.implement

> APEX-style auto-pipeline: implement → test → visual baselines → map to spec.

---

## Overview

`/spec.implement [feature-name]`

Executes a full implementation pipeline from `plan.md` to working, tested, documented code. By default, uses multi-agent orchestration (supervisor + superpowers + documenter). Use `--mono` for single-agent mode.

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

## Preflight Safety Contract

Before Phase 1, run a preflight check and stop early on blockers:

- [ ] Target feature directory exists
- [ ] `spec.md` exists and status is not Deprecated
- [ ] `plan.md` exists and contains no unresolved `[DECISION NEEDED]`
- [ ] Project test commands are resolved in plan.md Resolved Test Commands (use `system/testing/discovery.md` if not)
- [ ] Required tooling is available for chosen steps (verified during test discovery)
- [ ] If plan has "Infrastructure Setup" section: infrastructure provisioning tools are available (e.g., `wrangler` for Cloudflare, `aws` CLI for AWS)

If one check fails, do not start implementation. Report blocker + minimal recovery command.

### Environment Failure Protocol

When tooling is broken (install failure, missing binary, config crash):

1. Stop code edits after current safe checkpoint.
2. Record `Blocked by Environment` section in execution output.
3. Provide minimal unblock plan with exact commands.
4. Offer `/spec.implement [feature] --resume` once unblocked.

### Change Scope Guard

To avoid large accidental edits:

- Maximum initial touch set: 12 files.
- If plan requires more, split into phases and ask for confirmation.
- For each phase, list exact files before editing.

### Phase 0.5 — Preflight Check (Light)

After verifying spec/plan files exist (Preflight Safety Contract), run a light preflight check to verify tools and access are ready:

1. If `.specs/preflight.md` does not exist → log warning: "No preflight manifest found. Run `/spec.preflight --regenerate` to create one." and continue to Phase 2
2. Run `/spec.preflight --light` with the current feature name as context
3. Gate behavior:
   - Any `critical` check failed → **STOP**. Write `preflight-report.md` with BLOCKED verdict. Report blocker + recovery command. Do not start implementation.
   - Only `warning` checks failed → write `preflight-report.md` with WARNINGS verdict, display warning, continue to Phase 2
   - All pass → write `preflight-report.md` with READY verdict, continue to Phase 2

This phase ensures tools, OAuth sessions, and API tokens are available before autonomous work begins. It runs AFTER the Preflight Safety Contract (which checks spec/plan file existence) and BEFORE the Infrastructure Gate (Phase 2 Step 0, which checks cloud resource existence).

### Phase 2 — Plan Execution

Create an ordered todo list from `plan.md`:

```
[ ] Step 0: Infrastructure setup (provision, bind, verify) — only if plan has Infrastructure Setup
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

### Step Gate (Blocking) — obligatoire avant passage au step suivant

Règle globale: un step ne peut passer à `Done` que si ses vérifications sont vertes (ou `Blocked` documenté).

> **MANDATORY: `progress.md` must be created at Step 1 and updated after EVERY step.**
> This file is the only mechanism enabling `--resume`. Skipping it is NOT allowed.
> If the implementation is interrupted without `progress.md`, all progress is lost.

Pour chaque `Step N`:

1. Exécuter les checks ciblés du step (tests unitaires/intégration/E2E selon le scope).
2. Exécuter les checks transverses impactés (au minimum lint/typecheck sur fichiers touchés).
3. Si échec: corriger et re-tester dans les limites d'itération.
4. Si limite atteinte: marquer `Blocked`, enregistrer le contexte, arrêter la progression.
5. **Écrire le checkpoint dans `.specs/features/NNN-feature-name/progress.md` (BLOCKING — do NOT proceed without writing this).**
6. Passer au `Step N+1` uniquement si statut `Done`.

#### Statuts autorisés par step

- `Todo`
- `In Progress`
- `Done`
- `Blocked`

#### Format de checkpoint (persistant, utilisé par `--resume`)

| Step | Status | Files | Tests run | Result | Updated at |
|---|---|---|---|---|---|
| 1 | Done | `db/migrations/2026xxxx.sql` | [resolved test command] | Pass | 2026-03-12 10:42 |
| 2 | Blocked | `src/data/notifications.ts` | [resolved test command] | Fail (3/3) | 2026-03-12 11:03 |

#### Règle `--resume`

`--resume` lit `.specs/features/NNN-feature-name/progress.md` et reprend au premier step non `Done`.

### Phase 3 — Convert & Dispatch (Superpowers Bridge)

Instead of coding directly, construct a **Task Payload** for the current step and dispatch it to Superpowers.

#### 3.1 — Build the Task Payload

For each step, assemble the following payload:

**1. Context**
- Functional Requirements (FR) and Acceptance Criteria (AC) from `spec.md` that are addressed by this step.
- A summary of how this step fits into the overall plan (reference `plan.md` step description and diagrams).

**2. Implementation Instructions**
- Exact step description from `plan.md` (files to create/modify, patterns to follow, exact code structure if specified).
- Relevant rules from `.specs/constitution.md` that apply to the files being touched.
- Stack and patterns from `.specs/stacks/_default.md`.

**3. LiveSpec Mandatory Rules**
- Every source file that implements a FR **must** contain an inline `@spec` anchor comment with a deep-link to the spec:
  ```
  // @spec FR-NNN: <description> — .specs/features/NNN-feature-name/spec.md#fr-nnn   ← JS/TS/C-style
  # @spec FR-NNN: <description> — .specs/features/NNN-feature-name/spec.md#fr-nnn     ← Python/Ruby/Shell
  -- @spec FR-NNN: <description> — .specs/features/NNN-feature-name/spec.md#fr-nnn    ← SQL
  <!-- @spec FR-NNN: <description> — .specs/features/NNN-feature-name/spec.md#fr-nnn --> ← HTML/XML
  ```
  Use the comment syntax appropriate to the target language.
- Description must be < 50 chars, extracted from the FR text in `spec.md`.
- When a single block implements multiple FRs, combine them: `// @spec FR-001: Fetch count, FR-003: Mark read — .specs/features/NNN-feature-name/spec.md#fr-001`
- These anchors are **non-negotiable** — the Spec Reviewer must verify their presence and deep-link before approving.
- Anchors must be placed on the line immediately above the function, class, or block that implements the requirement.

**4. Strict TDD Protocol**
- Tests **must** be written before production code (RED → GREEN → REFACTOR).
- The following **Resolved Test Commands** from `plan.md` must be executed to validate the step:
  - (List the exact commands — e.g. `npx vitest run src/...`, `npx playwright test`, `npm run lint`, `npm run typecheck`)
- For UI/visual steps: `npx playwright test` (or the resolved visual test command) is **mandatory**.
- Visual baselines must be saved to `.specs/features/NNN-feature-name/baselines/`.
- All commands must pass before the step can be declared `Done`.

**5. Definition of Done (for Superpowers reviewers)**

The **Spec Reviewer** must confirm:
- [ ] All FR/AC assigned to this step are implemented
- [ ] Every implemented FR has a `@spec FR-NNN: description — path/to/spec.md#fr-nnn` anchor (with deep-link) in the source file
- [ ] No FR from `spec.md` is implemented partially (all-or-nothing per FR)

The **Code Quality Reviewer** must confirm:
- [ ] All resolved test commands pass (unit, integration, E2E, visual as applicable)
- [ ] Lint and typecheck pass on all touched files
- [ ] No God files (max 300 lines per file)
- [ ] No function exceeds 50 lines
- [ ] Code follows existing patterns and constitution rules
- [ ] No SQL/XSS/command injection risks
- [ ] No secrets or credentials in code
- [ ] No sensitive data in logs or error messages
- [ ] Input validation on user-facing boundaries

#### 3.2 — Dispatch to Superpowers

Spawn a subagent with the following instruction, passing the Task Payload assembled in 3.1:

```
Spawn subagent with prompt:
  "Use the `superpowers:subagent-driven-development` skill to implement the following task.

   <Task Payload from 3.1>"
```

The subagent will auto-activate the `superpowers:subagent-driven-development` skill, which will:
1. Spin up a fresh **Implementer** subagent to write code and tests (TDD, context-isolated).
2. Spin up a **Spec Reviewer** subagent to verify FR/AC compliance and `@spec` anchors.
3. Spin up a **Code Quality Reviewer** subagent to verify test passage and code quality.
4. Loop back to the Implementer if either review fails (with findings).
5. Apply `systematic-debugging` if tests fail after the implementation loop.

**On Superpowers completion:** receive the list of files created/modified, FR/AC addressed, and test results. Feed these into the Step Gate (Phase 2) to write the `progress.md` checkpoint.

**Execution logs:** By default, a detailed execution log is saved to `.specs/features/NNN-feature-name/logs/YYYY-MM-DD.md` after completion. Use `--no-save` to disable.

### Phase 5 — Visual Baselines (UI features only)

For features with UI components specified in the spec:

- Follow the visual baselines protocol in `system/testing/visual-baselines.md`
- Use the visual test command from `plan.md` **Resolved Test Commands**
- If no visual testing tool is available → skip and log: "Visual baselines skipped — no visual testing tool resolved"
- Baselines are saved to `.specs/features/NNN-feature-name/baselines/` and committed with the implementation

### Phase 6 — Validate

Before declaring implementation complete:

- Execute the final validation sequence from `system/testing/execution-rules.md`
- All commands come from `plan.md` **Resolved Test Commands** — no hardcoded commands
- All checks must pass. Fix any issues found within iteration limits.

### Phase 7 — Update implementation.md

Create or update `.specs/features/NNN-feature-name/implementation.md`:

For every FR and AC, fill in:

```markdown
| [FR-001: Fetch unread count](spec.md#fr-001) | src/data/notifications.ts | `@spec FR-001: Fetch unread count — .specs/features/004-notifications/spec.md#fr-001` | ✅ Implemented | 2024-03-15 |
| [FR-002: Real-time count updates](spec.md#fr-002) | src/hooks/useNotificationSubscription.ts | `@spec FR-002: Real-time count updates — .specs/features/004-notifications/spec.md#fr-002` | ✅ Implemented | 2024-03-15 |
```

The `@spec` anchor in source code must include `: description` extracted from the FR text in `spec.md`. The Requirement column deep-links to `spec.md#fr-nnn` for direct navigation.

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

### Phase 8.5 — Update README.md

1. Update the feature row in `.specs/README.md`:
   - If all steps completed successfully: set Status to `Implemented`
   - If blocked or partial: set Status to `In Progress`
   - Update the `Updated` date to today

2. Regenerate the Recent Activity section:
   - Read `.specs/changelog.md`
   - Extract the last 10 entries (most recent first)
   - Rewrite the content between `<!-- readme:activity:start -->` and `<!-- readme:activity:end -->`

3. Update the `Last updated` date in the header.

If `.specs/README.md` does not exist, create it by scanning existing artifacts (see spec-system.md README.md Recovery).

---

## Output

```
.specs/features/004-notifications/
├── spec.md              ← Unchanged
├── plan.md              ← Unchanged
├── progress.md          ← Step-by-step checkpoint (used by --resume)
├── implementation.md    ← Created/updated with FR→@spec mapping
├── changelog.md         ← Updated with new entry
├── logs/                ← Execution logs (default, use --no-save to disable)
│   └── YYYY-MM-DD.md
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
| `--no-save` | Do not save execution logs (by default, logs are saved to `.specs/features/NNN/logs/YYYY-MM-DD.md`) |
| `--mono` | Single-agent mode — no orchestration, all phases executed directly (original APEX pipeline) |
| `--economy` | No subagents, direct tools only (slower but uses less tokens) |
| `--resume` | Resume an interrupted implementation (reads `progress.md`, restarts at first non-`Done` step) |
| `--no-visual` | Skip visual baseline capture even if UI components are created |
| `--step [N]` | Start from step N (skip earlier steps, useful for partial re-runs) |

---

## Multi-Agent Mode (default)

By default, the pipeline is orchestrated by a **supervisor agent** acting as **Orchestrator/Translator**. The supervisor no longer writes code or runs tests itself — it delegates all execution to Superpowers' isolated subagents.

```
Supervisor (Orchestrator/Translator — never codes, never tests)
  │
  ├── [Per step] superpowers:subagent-driven-development
  │     ├── Implementer subagent  (writes code + tests, places @spec anchors)
  │     ├── Spec Reviewer subagent (verifies FR/AC compliance + @spec presence)
  │     └── Code Quality Reviewer subagent (verifies tests pass + code quality)
  │
  └── Documenter (updates progress.md, implementation.md, changelogs, README)
```

**Per-step cycle:**
1. Supervisor builds the Task Payload (FR/AC, instructions, TDD commands, Definition of Done)
2. Supervisor dispatches to `superpowers:subagent-driven-development`
3. Superpowers executes: Implementer → Spec Review → Quality Review (with fix loops)
4. Supervisor receives results, updates `progress.md` via Documenter

**Final phase:**
1. Supervisor dispatches a Final Validation to Superpowers (full test suite regression check)
2. Supervisor spawns Documenter to finalize `implementation.md`, changelogs, and README

> **Note:** The `livespec-implementer` agent is only used for infrastructure provisioning (Phase 0). The `livespec-verifier` agent is only used for spec/plan review in `/spec.feature`. All feature code implementation, testing, and code review are handled by Superpowers' isolated subagents. The `livespec-documenter` agent is retained for post-implementation traceability.

All existing flags (`--resume`, `--auto`, `--no-save`, `--no-visual`, `--step`) work in multi-agent mode.

Use `--mono` to disable orchestration and run all phases directly in a single agent (original APEX pipeline).

Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: 1` in settings.

---

## Iteration Limits

See `system/testing/failure-handling.md` for iteration limits per test type.

---

## Definition of Done (Command-Level)

`/spec.implement` is complete only if all are true:

- [ ] `progress.md` exists with a checkpoint row for every step executed
- [ ] Planned FR scope for this run is implemented or explicitly deferred
- [ ] Relevant tests pass for touched scope (or blocker documented)
- [ ] `implementation.md` updated with FR/AC -> `@spec` mappings
- [ ] Feature `changelog.md` updated
- [ ] Global `.specs/changelog.md` updated
- [ ] `.specs/README.md` feature row Status updated (Implemented or In Progress)
- [ ] `.specs/README.md` Recent Activity regenerated from changelog
- [ ] Execution log saved to `logs/YYYY-MM-DD.md` (unless `--no-save`)
- [ ] Resume point is saved when incomplete work remains

If not complete, return a resumable status report instead of a success message.

---

## Error Reporting Format

See `system/testing/failure-handling.md` for the structured error reporting template.

---

*LiveSpec Command v1.0*
