---
name: livespec
description: >
  LiveSpec specification-driven development framework. Activate when the project
  contains a .specs/ directory, when the user mentions specs/livespec, or when
  working with feature specifications.
---

# LiveSpec — Spec-Driven Development

## Mandatory Rules

**ALWAYS read `.specs/spec-system.md` before any spec command or code modification.**

1. **No implementation without spec** — create one first with `/spec.specify`
2. **Specs are the source of truth** — code is wrong if it doesn't match spec
3. **Mermaid diagrams are mandatory** in every spec.md and plan.md
4. **Update implementation.md** after every code change (FR/AC → @spec mapping)
5. **Update changelog.md** after every change
6. **Specs are living** — update when behavior changes

## Available Commands

| Command | Purpose |
|---|---|
| `/spec.init` | Initialize LiveSpec: 3-phase brainstorm → .specs/ structure + CLAUDE.md |
| `/spec.specify` | Create feature spec with stories, Mermaid, AC, FR |
| `/spec.plan` | Generate technical plan with sequence/state/ER diagrams |
| `/spec.implement` | Auto-pipeline: code → test → baselines → spec mapping |
| `/spec.check` | Verify spec vs code, produce gap report |
| `/spec.explain` | Living documentation with diagrams and history |
| `/spec.stack` | View/evolve tech stack, create ADRs |

## CLAUDE.md Template

When `/spec.init` runs, add this section to the project's CLAUDE.md
(idempotent via `<!-- livespec:start -->` / `<!-- livespec:end -->` markers):

<!-- livespec:start -->
## LiveSpec — Spec-Driven Development

This project uses [LiveSpec](https://github.com/julien-m/livespec).

### MANDATORY RULES

1. **Read `.specs/spec-system.md` FIRST** before any code modification or feature work.
2. **No implementation without a spec.** Create one first with `/spec.specify`.
3. **Specs are the source of truth.** If spec and code disagree, the code is wrong.
4. **Mermaid diagrams are mandatory** in every spec.md and plan.md.
5. **Update implementation.md** after every code change (FR/AC → `@spec` anchor mapping).
6. **Update changelog.md** after every change.

### Available Commands

`/spec.init` · `/spec.specify` · `/spec.plan` · `/spec.implement` · `/spec.check` · `/spec.explain` · `/spec.stack`

### Key Files

- `.specs/spec-system.md` — Complete rules (READ FIRST)
- `.specs/constitution.md` — Architecture principles
- `.specs/project.md` — Project vision and constraints
- `.specs/stacks/_default.md` — Tech stack decisions
<!-- livespec:end -->

## Execution Guardrails (Deterministic)

Before acting, run this mini-protocol:

1. **Classify intent**
   - New feature request -> `/spec.specify`
   - Existing feature technical design -> `/spec.plan`
   - Code/build task for an approved feature -> `/spec.implement`
   - Audit/spec-code alignment -> `/spec.check`
   - Understanding/history/"why" question -> `/spec.explain`
   - Stack or ADR change -> `/spec.stack`

2. **Resolve ambiguity first (max 2 questions)**
   If request maps to multiple features, asks both bugfix+feature, or references missing context, ask concise disambiguation questions before writing files.

3. **Fail safe on missing prerequisites**
   - Missing `.specs/` -> run `/spec.init`
   - Missing feature `spec.md` -> run `/spec.specify`
   - Missing `plan.md` before implementation -> run `/spec.plan`

4. **Definition of done (every command run)**
   - Output files are explicitly listed
   - Next command is suggested
   - If blocked, report exact blocker and minimal recovery step
