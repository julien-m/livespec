# LiveSpec Skill — Claude Code / APEX

> APEX-compatible skill file for Claude Code.
> Registers all `/spec.*` commands following the APEX skill format.
>
> **Installation:** This file is installed to `CLAUDE.md` at project root by `/spec.link claude-code`
> or globally to `~/.claude/skills/livespec.md` with `/spec.link claude-code --global`.

---

## Skill Metadata

```yaml
name: livespec
version: 1.0.0
description: >
  Specification-driven development with living docs, Mermaid diagrams,
  and spec-to-code traceability. Universal framework for AI-driven development.
author: LiveSpec
requires:
  - file_read
  - file_write
  - bash
  - browser (for Playwright visual tests)
```

---

## Initialization

**ALWAYS read `.specs/spec-system.md` before executing any spec command.**

This file contains the complete rules for how specs work in this project.
All commands below build on those rules.

---

## Commands

---

### `/spec.init` — Initialize LiveSpec

**Description:** 3-phase conversational brainstorm to set up LiveSpec in a project.

**Steps:**

```
STEP 1 — Phase A: Brainstorm
  1.1 Ask: "What are you building? (describe like explaining to a friend)"
  1.2 Ask: "WHO uses it? (roles and access levels)"
  1.3 Ask: "WHERE do they use it? (desktop/mobile/both)"
  1.4 Ask: "WHAT needs to be real-time? (live updates, messaging, etc.)"
  1.5 Ask: "WHERE are your users? (geography → impacts infra)"
  1.6 Ask: "What's your budget and scale expectation?"
  1.7 Summarize into PROJECT PROFILE box
  1.8 Ask for confirmation before proceeding

STEP 2 — Phase B: Stack Decisions
  2.1 Generate infrastructure decision tree as Mermaid flowchart
  2.2 Present recommended stack table with reasons
  2.3 Allow user to adjust choices
  2.4 Define testing strategy based on project type and stack
  2.5 Generate Architecture Decision Records (ADR) for key choices

STEP 3 — Phase C: Installation
  3.1 Create .specs/ directory structure
  3.2 Copy spec-system.md (verbatim from LiveSpec system/)
  3.3 Generate constitution.md from conversation context
  3.4 Generate project.md from Phase A answers
  3.5 Generate stacks/_default.md from Phase B decisions
  3.6 Write ADRs to stacks/decisions/
  3.7 Generate testing/strategy.md tailored to project
  3.8 Create empty features/ directory
  3.9 Create global changelog.md with initial entry
  3.10 Report: list all created files with descriptions
```

**Reference:** `.specs/commands/init.md` (or `commands/init.md` in the LiveSpec repository)

---

### `/spec.specify` — Create Feature Spec

**Description:** Generate a complete spec.md with user stories, Mermaid flowcharts, AC, and FR.

**Steps:**

```
STEP 1 — Setup
  1.1 Parse feature name from user input
  1.2 Scan .specs/features/ for highest existing NNN number
  1.3 Increment to get next NNN (zero-padded to 3 digits)
  1.4 Create directory: .specs/features/NNN-feature-name/

STEP 2 — Read Context
  2.1 Read .specs/project.md (users, roles, constraints)
  2.2 Read .specs/constitution.md (architecture principles)
  2.3 Read .specs/stacks/_default.md (tech stack)

STEP 3 — Generate spec.md
  3.1 Write header (name, branch, date, status, input)
  3.2 Write User Scenarios (3-5 stories with P1/P2/P3 priorities)
  3.3 For each story: write Given/When/Then acceptance scenarios
  3.4 For each story: generate Mermaid flowchart (MANDATORY — do not skip)
  3.5 Write Acceptance Criteria (AC-001, AC-002, ...)
  3.6 Write Functional Requirements (FR-001, FR-002, ...)
  3.7 Write Key Entities section
  3.8 Write Edge Cases section
  3.9 Write Success Criteria section

STEP 4 — Quality Check
  4.1 Verify every user story has a Mermaid flowchart
  4.2 Verify all AC are testable
  4.3 Verify all FR reference at least one AC
  4.4 Verify max 3 [NEEDS CLARIFICATION] markers
  4.5 Fix any issues before presenting

STEP 5 — Report
  5.1 Show summary: N stories, N AC, N FR, N diagrams
  5.2 Offer to create git branch
  5.3 Suggest next: /spec.plan [feature]
```

**Reference:** `.specs/commands/specify.md` (or `commands/specify.md` in the LiveSpec repository)

---

### `/spec.plan` — Generate Technical Plan

**Description:** Generate plan.md with sequence/state/ER diagrams and file-by-file implementation plan.

**Steps:**

```
STEP 1 — Read Context
  1.1 Read .specs/features/NNN-feature-name/spec.md
  1.2 Read .specs/constitution.md
  1.3 Read .specs/stacks/_default.md
  1.4 Read .specs/testing/strategy.md
  1.5 Read .specs/project.md

STEP 2 — Generate Technical Context
  2.1 Auto-fill from stack: language, framework, database, testing tools
  2.2 Fill Technical Context table

STEP 3 — Constitution Check
  3.1 For each principle in constitution.md: verify plan conforms
  3.2 Mark ✅ for each passing gate
  3.3 Note any deviations

STEP 4 — Generate Diagrams
  4.1 If feature has API calls → generate sequenceDiagram (MANDATORY)
  4.2 If entity has lifecycle states → generate stateDiagram-v2 (MANDATORY)
  4.3 If new database tables → generate erDiagram (MANDATORY)

STEP 5 — Implementation Plan
  5.1 For each FR: identify which files satisfy it
  5.2 Order steps: DB → data layer → API → UI → tests
  5.3 Write file-by-file plan with function signatures

STEP 6 — Testing Plan
  5.1 Map each test type to specific files
  5.2 Reference FR and AC for each test
  5.3 Include visual test plan if UI components involved

STEP 7 — API Contracts (if applicable)
  7.1 Create contracts/ directory
  7.2 Generate openapi.yaml for new endpoints

STEP 8 — Report
  8.1 List diagrams generated
  8.2 List implementation steps
  8.3 Suggest next: /spec.implement [feature]
```

**Reference:** `.specs/commands/plan.md` (or `commands/plan.md` in the LiveSpec repository)

---

### `/spec.implement` — Auto Implementation Pipeline

**Description:** Full APEX-style pipeline: analyze → implement → test → visual baselines → map.

**Steps:**

```
STEP 1 — Analyze
  1.1 Read spec.md, plan.md, constitution.md, stack, testing strategy
  1.2 Explore codebase for existing patterns
  1.3 Identify files to create/modify
  1.4 Create ordered todo list from plan.md

STEP 2 — Execute (file by file)
  2.1 Read target file before modifying
  2.2 Implement each step from plan
  2.3 Match existing code patterns and naming conventions
  2.4 Mark todo as complete after each step

STEP 3 — Test
  3.1 After each layer: run relevant tests
  3.2 On failure: fix and re-run (max 3 iterations for unit/integration)
  3.3 If max iterations exceeded: STOP and report to human

STEP 4 — Visual Baselines
  4.1 For UI features: run Playwright tests
  4.2 Capture baseline screenshots
  4.3 Save to .specs/features/NNN/baselines/
  4.4 Max 5 iterations for visual tests

STEP 5 — Validate
  5.1 npx tsc --noEmit
  5.2 npx eslint (if configured)
  5.3 npm run test (all tests)
  5.4 npx playwright test (if applicable)

STEP 6 — Document
  6.1 Create/update implementation.md with FR/AC → @spec anchor mapping
  6.2 Add changelog entry with type, files, AC impacted, author

STEP 7 — Report
  7.1 Summary: files created, tests passing, AC satisfied
  7.2 Suggest: /spec.check [feature] to verify
```

**Reference:** `.specs/commands/implement.md` (or `commands/implement.md` in the LiveSpec repository)

---

### `/spec.check` — Verify Spec vs Code

**Description:** Compare spec requirements against actual code and produce gap report.

**Steps:**

```
STEP 1 — Resolve Feature
  1.1 Find feature directory from name or current branch

STEP 2 — Extract Requirements
  2.1 Read spec.md → extract all AC and FR
  2.2 Read implementation.md → get @spec anchor mappings

STEP 3 — Verify Implementation
  3.1 For each FR: read mapped code, verify it satisfies the requirement
  3.2 For each AC: find test, verify test covers the criterion
  3.3 Assign status: ✅ Verified | ⚠️ Partial | ❌ Missing | 🔄 Drifted

STEP 4 — Visual Verification (if UI)
  4.1 Run Playwright to capture current screenshots
  4.2 Compare with baselines in .specs/features/NNN/baselines/
  4.3 Report: ✅ Match | 🖼️ Drift | ❌ Missing

STEP 5 — Report
  5.1 Print gap report table
  5.2 Suggest fixes for each gap
  5.3 Ask if implementation.md should be updated with current status
```

**Reference:** `.specs/commands/check.md` (or `commands/check.md` in the LiveSpec repository)

---

### `/spec.explain` — Living Documentation

**Description:** Understand how a feature works through visual diagrams and history.

**Steps:**

```
STEP 1 — Resolve Input
  1.1 Parse feature name or natural language question
  1.2 Find matching feature directory
  1.3 If question → search specs for keywords

STEP 2 — Read Sources
  2.1 spec.md → user flows and Mermaid flowcharts
  2.2 plan.md → sequence, state, ER diagrams
  2.3 implementation.md → code locations
  2.4 changelog.md → history
  2.5 stacks/decisions/ → why choices were made

STEP 3 — Generate Summary
  3.1 What it does (user-facing description)
  3.2 Who uses it (roles table)
  3.3 User flow (Mermaid flowchart from spec)
  3.4 How it works (sequence diagram from plan)
  3.5 Entity lifecycle (state diagram if applicable)
  3.6 Data model (ER diagram if applicable)
  3.7 Where in code (key files from implementation.md)
  3.8 Why built this way (ADR references)
  3.9 History (recent changelog entries)
```

**Reference:** `.specs/commands/explain.md` (or `commands/explain.md` in the LiveSpec repository)

---

### `/spec.stack` — Evolve Infrastructure

**Description:** Show current stack, analyze impact of changes, create ADRs.

**Steps:**

```
STEP 1 — Show (if no change requested)
  1.1 Read .specs/stacks/_default.md
  1.2 Read all ADRs in stacks/decisions/
  1.3 Display stack table and decision history

STEP 2 — Change (if change requested)
  2.1 Parse the requested change (which layer, from → to)
  2.2 Ask clarifying questions if needed
  2.3 Read all feature implementation.md files
  2.4 Identify which features are affected and how
  2.5 Present impact table with effort estimates

STEP 3 — Confirm and Execute
  3.1 Wait for human confirmation
  3.2 Create ADR in stacks/decisions/ADR-NNN-*.md
  3.3 Update stacks/_default.md
  3.4 Optionally generate migration specs for affected features
```

**Reference:** `.specs/commands/stack.md` (or `commands/stack.md` in the LiveSpec repository)

---

### `/spec.link` — Install AI Tool Adapters

**Description:** Copy command docs to `.specs/commands/` and install the adapter for the specified AI tool.

**Steps:**

```
STEP 1 — Determine Tool(s)
  1.1 If tool argument provided: use it (copilot | claude-code | cursor | all)
  1.2 If no argument: auto-detect from project files
      - .github/ present → include copilot
      - CLAUDE.md present → include claude-code
      - .cursorrules present → include cursor

STEP 2 — Copy Command Files
  2.1 Create .specs/commands/ directory
  2.2 Copy all 8 command docs (init, specify, plan, implement, check, explain, stack, link)
  2.3 Skip files that already exist unless --force passed

STEP 3 — Install Adapter
  3.1 copilot: create .github/copilot-instructions.md from adapters/copilot/agent.md
  3.2 claude-code: create CLAUDE.md from adapters/claude-code/SKILL.md
               OR with --global: symlink ~/.claude/skills/livespec.md
  3.3 cursor: copy/append adapters/cursor/.cursorrules to .cursorrules

STEP 4 — Report
  4.1 Print summary of files created, updated, or skipped
```

**Reference:** `.specs/commands/link.md` (or `commands/link.md` in the LiveSpec repository)

---

## Global Rules (applied to every command)

1. **Read spec-system.md first** — always
2. **No implementation without spec** — if no spec exists, create one first
3. **Mermaid is mandatory** — every user story must have a flowchart
4. **Update implementation.md** — after every code change
5. **Update changelog.md** — after every change (implementation, bugfix, refactor, spec update)
6. **Specs are living** — update spec.md when behavior changes, not just code

---

*LiveSpec Claude Code Adapter v1.0*
