# Plan: `/spec.test` — Test validation command

## Summary

Create a single command file `commands/spec-test.md` that defines the `/spec.test` command, following the same structure as existing commands (check.md, implement.md). Then update integration points in `implement.md`, `feature.md`, `ship.md`, `system/spec-system.md`, `README.md`, and `system/testing/test-protocol.md`. Finally link globally via `/link`.

**Key distinction with /spec.implement Phase 6:** implement runs EXISTING tests as a validation gate during coding. /spec.test AUDITS coverage against AC, GENERATES missing tests from Gherkin, EXECUTES the full suite, and produces a standalone REPORT. It catches AC with no test at all and generates them.

## Technical Context

- **Language:** Markdown (command definition files, no executable code)
- **Framework:** LiveSpec command system (`.md` files in `commands/`)
- **Testing:** LiveSpec's own Python validator (structural + coherence rules)
- **Project type:** Spec framework — commands are instructions for AI agents, not executable code

## Implementation Plan

### Step 1: Create `commands/spec-test.md`

**File:** `commands/spec-test.md` (CREATE)

Write the full command definition following the pattern established by `check.md` and `implement.md`:

- YAML frontmatter: `description`, `argument-hint`
- Overview with Mermaid flowchart
- Hooks resolution protocol (before-test / after-test)
- Feature resolution (same pattern as check.md Step 2-3)
- Phase 0: Resolve & Preflight
- Phase 1: Audit (coverage matrix from check report or spec/implementation)
- Phase 2: Plan (display what will be generated, confirmation gate)
- Phase 3: Generate (Gherkin→test translation, pattern matching, overwrite protection, compilation gate)
- Phase 4: Execute (run resolved test commands in order)
- Phase 4.5: Visual (capture missing baselines, design fidelity)
- Phase 5: Report (test report, persist, update implementation.md)
- Multi-feature consolidated report
- Flags table
- Iteration limits
- Integration points (feature, ship, check)
- Definition of Done

**Source:** Design spec at `docs/superpowers/specs/2026-04-06-spec-test-command-design.md`

### Step 2: Update `commands/spec-implement.md` — Add /spec.test reference

**File:** `commands/spec-implement.md` (MODIFY)

In the Phase 6 (Validate) section, add a note that `/spec.test` can be run standalone for more thorough test validation:

```markdown
> **Note:** For standalone test validation with generation of missing tests, use `/spec.test`.
```

### Step 3: Update `commands/spec-feature.md` — Add Phase 4.5

**File:** `commands/spec-feature.md` (MODIFY)

Add `/spec.test` as Phase 4.5 in the pipeline (after implement, before final audit). The feature pipeline becomes: specify → plan review → plan → implement → **test** → audit → commit.

Clarify in the Phase 4.5 description: "/spec.test generates missing tests that implement's Phase 6 could not run because they didn't exist yet. It also captures visual baselines that may have been skipped during implement (--no-visual or tool unavailable)."

### Step 4: Update `commands/spec-ship.md` — Add test gate

**File:** `commands/spec-ship.md` (MODIFY)

In the Per Feature Loop, after the agent completes implementation, add a test validation step before merge. The spawned agent should run `/spec.test <feature> --auto` and include results in SHIP_RESULT.

### Step 5: Update `system/spec-system.md` — Add /spec.test to intent classification

**File:** `system/spec-system.md` (MODIFY)

Update ALL relevant sections:
- **Intent classification table:** add "run tests", "check test coverage", "generate missing tests", "validate tests"
- **Hook table:** add before-test / after-test row
- **Command count** in discovery paragraph: 15 → 16
- **Quality Gates section:** add "Before test validation is complete" gate
- **Lifecycle position:** implement → **test** → check → ship

### Step 5.5: Update `README.md`

**File:** `README.md` (MODIFY)

- Add `/spec.test` to the command table
- Update Mermaid pipeline flowchart (implement → test → check)
- Add usage example section
- Update comparison table
- Update command count

### Step 6: Update `system/testing/test-protocol.md` — Reference /spec.test

**File:** `system/testing/test-protocol.md` (MODIFY)

Add `/spec.test` to the modules table as the command that orchestrates test discovery, generation, and execution.

### Step 7: Run validator

Execute the LiveSpec Python validator to ensure the new command file passes structural validation:

```bash
cd /Users/julienm/projects/livespec && python -m validator.cli validate .
```

### Step 8: Link globally

Run `/link` to symlink the new command globally. Verify with `cc-hub command list | grep spec.test`.

## Files

| Step | File | Action |
|---|---|---|
| 1 | `commands/spec-test.md` | CREATE |
| 2 | `commands/spec-implement.md` | MODIFY (add reference) |
| 3 | `commands/spec-feature.md` | MODIFY (add Phase 4.5 + clarification) |
| 4 | `commands/spec-ship.md` | MODIFY (add test gate) |
| 5 | `system/spec-system.md` | MODIFY (intent, hooks, count, quality gates) |
| 5.5 | `README.md` | MODIFY (table, flowchart, examples, count) |
| 6 | `system/testing/test-protocol.md` | MODIFY (add reference) |
| 7 | — | RUN validator |
| 8 | — | RUN /link |

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Validator rejects new command format | Low | Medium | Follow exact same frontmatter as check.md |
| feature.md pipeline changes conflict with recent commits | Low | Low | Read latest version before editing |

---

*LiveSpec Plan v1.0 — 2026-04-06*
