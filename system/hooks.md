# LiveSpec Hooks — Resolution Protocol

> **This file defines how lifecycle hooks work in LiveSpec.**
> Referenced by `spec-system.md`. All `/spec.*` commands follow this protocol.

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
- `init`, `propose`, `specify`, `plan`, `implement`, `check`, `explain`, `stack`, `feature`, `refine`, `preflight`, `play-coverage`

**Step-level hooks** for `/spec.implement`:
- `before-implement-step.md` — injected before EACH implementation step
- `after-implement-step.md` — injected after EACH implementation step

Examples:
```
before-plan.md           # Injected before /spec.plan
after-plan.md            # Injected after /spec.plan
before-implement.md      # Injected before /spec.implement (once, at start)
after-implement.md       # Injected after /spec.implement (once, at end)
before-implement-step.md # Injected before EACH step during implement
after-implement-step.md  # Injected after EACH step during implement
before-feature.md        # Injected before /spec.feature (the full pipeline)
```

---

## Resolution Levels (3 levels)

Hooks are resolved from 3 locations, in order:

```
Level 1: Global     ~/.claude/livespec/hooks/{before|after}-{command}.md
Level 2: Project    .specs/hooks/{before|after}-{command}.md              (committed — team conventions)
Level 3: Local      .specs/hooks/{before|after}-{command}.local.md        (gitignored — personal prefs)
```

| Level | Location | Committed? | Scope |
|-------|----------|------------|-------|
| Global | `~/.claude/livespec/hooks/` | N/A (user home) | All LiveSpec projects |
| Project | `.specs/hooks/` | Yes | This project (team-shared) |
| Local | `.specs/hooks/*.local.md` | No (gitignored) | This project (personal) |

The distinction between committed and local is the `.local.md` suffix — exactly like `.env` vs `.env.local`.

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
1. Collect candidates:
   global  = ~/.claude/livespec/hooks/before-plan.md      (if exists)
   project = .specs/hooks/before-plan.md                   (if exists)
   local   = .specs/hooks/before-plan.local.md             (if exists)

2. Check local hook mode:
   - If local exists AND mode == "override":
     → Use ONLY the local hook. Skip global and project.
   - Otherwise (extend or no local):
     → Load all existing hooks in order: global → project → local

3. Inject the combined content into the command context.
```

If no hooks exist for an event, nothing is injected — the command runs as normal.

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

**All `/spec.*` commands automatically resolve hooks.** The resolution happens at two points:

1. **Before the command starts** — resolve and inject `before-{command}` hooks
2. **After the command completes** — resolve and inject `after-{command}` hooks

For `/spec.implement`, two additional hook points exist:
3. **Before each step** — resolve and inject `before-implement-step` hooks
4. **After each step** — resolve and inject `after-implement-step` hooks

For `/spec.feature`, hooks are resolved for each sub-command in the pipeline:
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

The following pattern must be present in the project's `.gitignore` (added by `/spec.init`):

```
.specs/hooks/*.local.md
```

---

## Discovery

Use `/spec.hooks [command]` to see which hooks would be loaded for a given command, or `--create`/`--edit` to manage them. See `commands/hooks.md` for details.

---

*LiveSpec Hooks Protocol v1.0*
