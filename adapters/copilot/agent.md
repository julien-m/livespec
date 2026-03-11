# GitHub Copilot Agent — LiveSpec

> This file configures GitHub Copilot as a LiveSpec-aware agent.
> It registers all `/spec.*` commands and instructs the agent to follow the spec system.
>
> **Installation:** This file is installed to `.github/copilot-instructions.md` by `/spec.link copilot`
> or `bash scripts/link.sh --tool copilot`.

---

## Agent Configuration

**Agent Name:** LiveSpec
**Description:** Specification-driven development with living docs and Mermaid diagrams

---

## Initialization Rule

**ALWAYS read `.specs/spec-system.md` before taking any action in this project.**

This file contains the rules for how specs work in this project. Every decision, every code change, and every new feature must follow those rules.

If `.specs/spec-system.md` does not exist, suggest running `bash <(curl -s https://raw.githubusercontent.com/julien-m/livespec/main/scripts/init.sh)` or `/spec.init` to initialize LiveSpec.

---

## Registered Commands

### `/spec.init`

**Description:** Initialize LiveSpec in this project through a 3-phase conversational brainstorm.

**Full instructions:** See `.specs/commands/init.md` in this project (or `commands/init.md` in the LiveSpec repository).

**Summary:**
1. Phase A — Ask 6 questions to understand the project (conversational)
2. Phase B — Recommend stack with Mermaid decision tree
3. Phase C — Create `.specs/` directory structure

**When to suggest:** When `.specs/` directory does not exist in the project.

---

### `/spec.specify`

**Description:** Create a new feature spec with user stories, Mermaid flowcharts, AC, and FR.

**Full instructions:** See `.specs/commands/specify.md` in this project.

**Summary:**
1. Parse feature description
2. Auto-number the feature (NNN)
3. Read context (project.md, constitution.md, stack)
4. Generate `spec.md` with Mermaid flowcharts for EVERY user story
5. Validate quality (flowcharts present, AC testable, no more than 3 unclear markers)

**Usage:** `/spec.specify "User can receive real-time notifications"`

---

### `/spec.plan`

**Description:** Generate technical plan with sequence, state, and ER diagrams.

**Full instructions:** See `.specs/commands/plan.md` in this project.

**Summary:**
1. Read spec.md + constitution.md + stack + testing strategy
2. Generate `plan.md` with Mermaid sequence/state/ER diagrams
3. Create file-by-file implementation plan
4. Generate API contracts if applicable

**Usage:** `/spec.plan notifications`

---

### `/spec.implement`

**Description:** APEX-style auto-pipeline: implement → test → visual baselines → map to spec.

**Full instructions:** See `.specs/commands/implement.md` in this project.

**Summary:**
1. Analyze codebase and read plan.md
2. Execute implementation file-by-file
3. Run tests (max 3 iterations for unit, 5 for visual)
4. Capture Playwright visual baselines
5. Create/update `implementation.md` with FR/AC → `@spec` anchor mapping
6. Update `changelog.md`

**Usage:** `/spec.implement notifications`

---

### `/spec.check`

**Description:** Compare spec vs actual code — find gaps, verify AC coverage, detect visual drift.

**Full instructions:** See `.specs/commands/check.md` in this project.

**Summary:**
1. Read spec.md (extract all AC and FR)
2. Read implementation.md (find mapped files and `@spec` anchors)
3. Read actual code — verify each requirement
4. Compare screenshots with Playwright baselines
5. Produce gap report with ✅ ⚠️ ❌ 🔄 status

**Usage:** `/spec.check notifications`

---

### `/spec.explain`

**Description:** Living documentation — understand how a feature works without reading code.

**Full instructions:** See `.specs/commands/explain.md` in this project.

**Summary:**
1. Accept feature name or natural language question
2. Read spec.md (user flows), plan.md (diagrams), implementation.md (code locations)
3. Read changelog.md (history) and ADRs (why decisions were made)
4. Produce visual summary with all Mermaid diagrams

**Usage:**
- `/spec.explain notifications`
- `/spec.explain "how do notifications work?"`
- `/spec.explain "why did we choose Supabase?"`

---

### `/spec.stack`

**Description:** Evolve your stack and analyze impact on existing features.

**Full instructions:** See `.specs/commands/stack.md` in this project.

**Summary:**
1. Show current stack (from `.specs/stacks/_default.md`)
2. Analyze impact of proposed changes on all features
3. Present impact table (before → after → effort per feature)
4. Create ADR documenting the decision
5. Update `_default.md`
6. Optionally generate migration specs

**Usage:**
- `/spec.stack` — show current stack
- `/spec.stack change "we need Edge deployment"`
- `/spec.stack decisions` — list all ADRs

---

### `/spec.link`

**Description:** Install AI tool adapters and make LiveSpec commands discoverable in your project.

**Full instructions:** See `.specs/commands/link.md` in this project.

**Summary:**
1. Copy all command docs to `.specs/commands/` so the AI can read them locally
2. Install the adapter for the specified tool (copilot, claude-code, cursor, or all)
3. Auto-detect which tools are present if no tool specified

**Usage:**
- `/spec.link` — auto-detect and link all found tools
- `/spec.link copilot`
- `/spec.link all --force`

---

## Agent Behavior Rules

### Before any code change:
1. Read `.specs/spec-system.md`
2. Find the relevant feature spec in `.specs/features/`
3. Verify the change conforms to the AC in `spec.md`
4. If behavior changes: update `spec.md` first

### After any code change:
1. Update `implementation.md` with new/changed `@spec` anchor references
2. Add entry to `changelog.md` with type, description, files changed, AC impacted

### When debugging:
1. Read `spec.md` to understand expected behavior
2. Read `implementation.md` to find relevant files
3. Compare spec vs code to identify the gap

### For new features:
1. Always create spec first with `/spec.specify`
2. Then plan with `/spec.plan`
3. Then implement with `/spec.implement`
4. Verify with `/spec.check`

---

*LiveSpec Copilot Adapter v1.0*
