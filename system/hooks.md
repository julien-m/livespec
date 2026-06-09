<!-- LiveSpec traceability anchors -->
<!-- @spec(FR-010) -->

# LiveSpec Hooks — Resolution Protocol

> **This file defines how lifecycle hooks work in LiveSpec.**
> Referenced by `spec-system.md`. All `/spec-*` commands follow this protocol.

---

## What Are Hooks?

Hooks are **Markdown files containing instructions in natural language** that are injected into the context of a LiveSpec command before or after its execution. They work like Claude Code rules — the AI reads them and follows the instructions.

Hooks allow customizing LiveSpec behavior **without modifying core commands**:
- Team conventions (code style, compliance rules, domain glossary)
- Personal preferences (TDD approach, verbose commits, external LLM review)
- Project-specific context (fintech compliance, security checklists)

---

## Hook Naming Convention

```
{before|after}-{command}.md
{before|after}-{command}.local.md
```

Where `{command}` matches the LiveSpec command name (without `spec.` prefix):
- `check`, `explain`, `feature`, `fix`, `hooks`, `implement`, `init`, `migrate`, `plan`, `play-coverage`, `preflight`, `propose`, `refine`, `refresh-conventions`, `ship`, `specify`, `stack`, `status`, `test`, `verify-output`

**Step-level hooks** for `/spec-implement`:
- `before-implement-step.md` — injected before EACH implementation step
- `after-implement-step.md` — injected after EACH implementation step

Examples:
```
before-plan.md           # Injected before /spec-plan
after-plan.md            # Injected after /spec-plan
before-implement.md      # Injected before /spec-implement (once, at start)
after-implement.md       # Injected after /spec-implement (once, at end)
before-implement-step.md # Injected before EACH step during implement
after-implement-step.md  # Injected after EACH step during implement
before-feature.md        # Injected before /spec-feature (the full pipeline)
```

---

## Resolution Levels (4 levels)

Hooks are resolved from 4 locations, in order:

```
Level 0: User Integrations  ~/.config/livespec/*.md                      (user-level, frontmatter-targeted)
Level 1: Global             ~/.claude/livespec/hooks/{before|after}-{command}.md
Level 2: Project             .specs/hooks/{before|after}-{command}.md     (committed — team conventions)
Level 3: Local               .specs/hooks/{before|after}-{command}.local.md (gitignored — personal prefs)
```

| Level | Location | Committed? | Scope |
|-------|----------|------------|-------|
| User Integrations | `~/.config/livespec/*.md` | N/A (user config) | Selected commands per file frontmatter |
| Global | `~/.claude/livespec/hooks/` | N/A (user home) | All LiveSpec projects |
| Project | `.specs/hooks/` | Yes | This project (team-shared) |
| Local | `.specs/hooks/*.local.md` | No (gitignored) | This project (personal) |

The distinction between committed and local is the `.local.md` suffix — exactly like `.env` vs `.env.local`.

### Level 0 — User Integrations

Files in `~/.config/livespec/*.md` are **user-level integrations**: markdown
instructions injected into the LLM context of selected LiveSpec commands,
targeted by their YAML frontmatter (not by filename).

Frontmatter schema (BOTH `integration:` and `commands:` are required to
identify the file as an integration):

```yaml
---
integration: <name>           # REQUIRED — logical name (any non-empty string)
commands: [<cmd>, ...]        # REQUIRED — matched against .agent-sync/skills/spec-* registry
phase: before | after         # default: before
mode: extend | override       # default: extend
order: <int>                  # default: 100 (lower = injected earlier)
---
```

**Single eligibility rule:** a file is treated as an integration if and
only if its frontmatter contains BOTH the `integration:` key AND the
`commands:` key. Otherwise (no frontmatter, missing either key) the file
is **silently ignored** — free `.md` notes can coexist without noise. A
file that DOES declare itself an integration but is malformed (unknown
command, invalid mode, invalid types, broken YAML) emits a single
stderr warning and is skipped.

**Read** [`integrations.md`](integrations.md) for the full semantics, runtime
algorithm, ordering rules, and override scope.

---

## Inheritance Model

Each `.local.md` hook declares in its YAML frontmatter how it combines with parent levels:

```yaml
---
mode: extend    # default — load parent hooks THEN this one
---
```

```yaml
---
mode: override  # replace the entire hook chain for this event
---
```

### Mode: `extend` (default)

All levels are loaded in order. Instructions accumulate:

```
Global before-plan.md → Project before-plan.md → Local before-plan.local.md → COMMAND → after hooks...
```

If a hook file has no frontmatter or no `mode` field, `extend` is assumed.

### Mode: `override`

Only the overriding hook is loaded. All parent levels are skipped:

```
Local before-plan.local.md (alone) → COMMAND → after hooks...
```

`override` replaces **the entire chain** for that specific event. Use it when you need full control.

**Important:** `override` only affects the hook that declares it. A `before-plan.local.md` with `mode: override` does not affect `after-plan` hooks.

**Invalid mode values:** If `mode` has an unrecognized value (anything other than `extend` or `override`), treat it as `extend` and emit a warning in stderr (e.g., `⚠ Unknown hook mode "merge" in before-plan.local.md — falling back to "extend"`).

**Override scope:** `mode: override` is only honored on `.local.md` hooks. Project-level hooks (`.specs/hooks/{before|after}-{command}.md`) always extend global hooks — they cannot override them. This keeps team conventions additive and predictable. Personal overrides via `.local.md` cover the primary use case: a developer needing full control over a specific hook event.

---

## Resolution Algorithm

For each hook event (e.g., `before-plan`):

```
1. Collect Level 0 candidates:
   For each ~/.config/livespec/*.md:
     parse YAML frontmatter
     keep iff "integration" AND "commands" both present
                                AND <cmd> ∈ commands
                                AND (phase == event OR phase absent and event == "before")
   Sort kept files by (order ASC, basename ASC).
   If ≥2 files have mode == "override" → error "Multiple override integrations".
   If exactly 1 file has mode == "override" → L0 = [that file] (others discarded).
   Else L0 = sorted list.

2. Collect Level 1/2/3 candidates:
   global  = ~/.claude/livespec/hooks/{event}-{cmd}.md     (if exists)
   project = .specs/hooks/{event}-{cmd}.md                  (if exists)
   local   = .specs/hooks/{event}-{cmd}.local.md            (if exists)

3. Check local hook mode (unchanged):
   - If local exists AND mode == "override":
     → higher_chain = [local]    (Level 0 is NOT affected)
   - Otherwise:
     → higher_chain = [global, project, local] (existing ones)

4. Inject (L0 ∥ higher_chain) into the command context, after template variable substitution.
```

Note: a `mode: override` at Level 3 (`.local.md`) does NOT strip Level 0 — and
symmetrically, a `mode: override` at Level 0 does NOT strip Levels 1/2/3.
The override scope is strictly bounded to the level that declares it.

If no hooks exist for an event, nothing is injected — the command runs as normal.

---

## Commit Hook

The `commit` hook is a special hook type that controls how LiveSpec performs git commits during auto-commit pipelines. Unlike lifecycle hooks (before/after), it defines the commit action itself.

### Naming

```
commit.md           # team-shared (committed)
commit.local.md     # personal (gitignored)
```

No `before-`/`after-` prefix — this hook IS the action.

### Resolution (3 levels)

```
Level 1: ~/.claude/livespec/hooks/commit.md     (global — all projects)
Level 2: .specs/hooks/commit.md                 (project — committed)
Level 3: .specs/hooks/commit.local.md           (personal — gitignored)
```

Same inheritance model as all other hooks (`mode: extend` or `mode: override` in frontmatter).

### Template Variables

| Variable | Resolved value |
|---|---|
| `{{spec_path}}` | Absolute path to `spec.md` for the current feature |
| `{{plan_path}}` | Absolute path to `plan.md` for the current feature |
| `{{adr_paths}}` | Comma-separated absolute paths matching `.specs/stacks/decisions/ADR-*.md` (empty string if none) |
| `{{feature_name}}` | Full kebab directory name (e.g., `003-notifications`) |
| `{{feature_number}}` | Numeric prefix only (e.g., `003`) |

`{{adr_paths}}` glob root: `{project_root}/.specs/stacks/decisions/`

### Fallback

If no `commit.md` exists at any level → invoke `/git.commit` without `--intent`.

**Never use bare `git commit`** — blocked by `commit-via-skill.md`.

### Example Global Hook (`~/.claude/livespec/hooks/commit.md`)

```markdown
---
mode: override
---

Use `/git.commit "feat({{feature_name}}): <message>" --intent "implements {{feature_name}} — spec: {{spec_path}}, plan: {{plan_path}}, ADRs: {{adr_paths}}"` to commit.

If {{adr_paths}} is empty, use: `/git.commit "feat({{feature_name}}): <message>" --intent "implements {{feature_name}} — spec: {{spec_path}}, plan: {{plan_path}}"`
```

### Gitignore

`.specs/hooks/commit.local.md` is already covered by the existing `.specs/hooks/*.local.md` pattern.

`.specs/hooks/.commit-context.json` is auto-generated at commit time by `livespec commit-context write` and must be gitignored. Add to `.gitignore`:

```
.specs/hooks/.commit-context.json
```

---

## Template Variables

Hooks can use template variables that are resolved at execution time:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{feature_name}}` | Current feature name (kebab-case) | `notification-preferences` |
| `{{feature_path}}` | Full path to feature directory | `.specs/features/004-notifications/` |
| `{{feature_number}}` | Zero-padded feature number | `004` |
| `{{stack}}` | Primary stack from `_default.md` | `Next.js + Supabase` |
| `{{command}}` | Current command being executed | `plan` |
| `{{project_name}}` | Project name (from directory or `project.md`) | `my-marketplace` |

Variables are replaced with their values before the hook content is injected. If a variable cannot be resolved (e.g., `{{feature_name}}` when no feature is in context), it is left as-is with no error.

---

## Hook Content Guidelines

Hooks contain **natural language instructions** — the same format as Claude Code rules or system prompts.

### What to put in hooks

- Load additional context files (conventions, glossaries, compliance rules)
- Set behavioral preferences (TDD, verbose commits, review steps)
- Run external commands (lint, typecheck, LLM review)
- Add project-specific checklists or gates
- Inject domain knowledge or constraints

### What NOT to put in hooks

- Command logic that modifies the core pipeline (use command flags instead)
- Secrets or credentials (use `creds` CLI)
- Large code blocks (keep hooks focused on instructions)

### Example: Global `before-implement.md`

```markdown
---
mode: extend
---

## Code Conventions
Before implementing, load and apply code conventions:
- Read code conventions from the project's CLAUDE.md references
- Always follow TDD: write tests first, then implementation
- Run `npm run typecheck` after each implementation step
```

### Example: Project `before-plan.md`

```markdown
---
mode: extend
---

## Domain Context
- This is a fintech project. Always consider PCI-DSS compliance in plans.
- Load the domain glossary from `.specs/glossary.md` before planning.
- Plans must include a "Security Considerations" section.
```

### Example: Local `before-plan.local.md`

```markdown
---
mode: extend
---

## External Plan Review
After generating the plan, challenge its coherence by running:
`cc-hub ask "Review this plan for logical gaps, missing edge cases, and over-engineering" -f {{feature_path}}/plan.md --model google/gemini-2.5-pro`
Incorporate any valid feedback before finalizing.
```

### Example: Local `before-implement-step.md`

```markdown
---
mode: extend
---

## Pre-Step Gate
Before starting each implementation step:
1. Verify that all tests from the previous step still pass
2. Run `npm run typecheck` on all modified files
3. If any check fails, fix before proceeding
```

---

## Integration with Commands

**All `/spec-*` commands automatically resolve hooks.** The resolution happens at two points:

1. **Before the command starts** — resolve and inject `before-{command}` hooks
2. **After the command completes** — resolve and inject `after-{command}` hooks

For `/spec-implement`, two additional hook points exist:
3. **Before each step** — resolve and inject `before-implement-step` hooks
4. **After each step** — resolve and inject `after-implement-step` hooks

**Level 0 (user integrations)** participate in the same injection points as
Levels 1–3. They are resolved first and prepended to the chain. The set of
commands a Level 0 file applies to is determined by its `commands:` frontmatter
field, not by filename — multiple commands can share one integration file.

For `/spec-feature`, hooks are resolved for each sub-command in the pipeline:
- `before-feature` / `after-feature` — wraps the entire pipeline
- `before-specify` / `after-specify` — wraps the specify phase
- `before-plan` / `after-plan` — wraps the plan phase
- `before-implement` / `after-implement` — wraps the implement phase
- `before-implement-step` / `after-implement-step` — wraps each implementation step

---

## File System Layout

### Project hooks directory

```
.specs/hooks/
├── before-plan.md                 # team — committed
├── before-plan.local.md           # personal — gitignored
├── after-plan.md
├── before-implement.md
├── before-implement.local.md
├── after-implement.md
├── before-implement-step.md
├── after-implement-step.local.md
├── before-specify.md
├── before-feature.md
├── after-feature.md
└── ...
```

### Global hooks directory

```
~/.claude/livespec/hooks/
├── before-implement.md            # global — all projects
├── before-plan.md
└── ...
```

### Gitignore

The following pattern must be present in the project's `.gitignore` (added by `/spec-init`):

```
.specs/hooks/*.local.md
```

---

## Discovery

Use `/spec-hooks [command]` to see which hooks would be loaded for a given command, including Level 0 user integrations (path, name, order, mode), or `--create`/`--edit` to manage levels 1–3. See [`.agent-sync/skills/spec-hooks/SKILL.md`](../.agent-sync/skills/spec-hooks/SKILL.md) for details. Level 0 integrations are managed by simply creating, editing, or deleting files in `~/.config/livespec/`.

Canonical command names are `spec-check`, `spec-doctor`, `spec-explain`, `spec-feature`, `spec-fix`, `spec-hooks`, `spec-implement`, `spec-init`, `spec-journey`, `spec-migrate`, `spec-plan`, `spec-play-coverage`, `spec-preflight`, `spec-propose`, `spec-refine`, `spec-refresh-conventions`, `spec-refresh-from-brainstorm`, `spec-ship`, `spec-specify`, `spec-stack`, `spec-status`, `spec-test`, and `spec-verify-output`. Dotted aliases such as `/spec.check` are accepted only as compatibility inputs and are normalized before hook resolution.

---

*LiveSpec Hooks Protocol v1.1 — adds Level 0 user integrations*
