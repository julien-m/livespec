---
description: "Show which lifecycle hooks are active for a command"
argument-hint: "[command-name]"
---

# Command: /spec.hooks

> Display which lifecycle hooks would be loaded for a given command, with their resolution order and mode.

---

## Overview

`/spec.hooks [command-name]`

Diagnostic command that shows the hook resolution chain for any `/spec.*` command without executing anything.

---

## Steps

### Step 1 — Resolve Command Name

If `command-name` is provided:
- Strip `spec.` prefix if present (e.g., `spec.plan` → `plan`)
- Validate it matches a known command: `init`, `propose`, `specify`, `plan`, `implement`, `check`, `explain`, `stack`, `feature`, `refine`, `preflight`

If no `command-name` is provided:
- Show hooks for ALL commands (summary view)

### Step 2 — Scan Hook Locations

For the target command, check existence of hook files at all 3 levels:

```
~/.claude/livespec/hooks/before-{command}.md       → Global
~/.claude/livespec/hooks/after-{command}.md        → Global
.specs/hooks/before-{command}.md                   → Project
.specs/hooks/after-{command}.md                    → Project
.specs/hooks/before-{command}.local.md             → Local
.specs/hooks/after-{command}.local.md              → Local
```

For `implement`, also check step-level hooks:
```
~/.claude/livespec/hooks/before-implement-step.md  → Global
~/.claude/livespec/hooks/after-implement-step.md   → Global
.specs/hooks/before-implement-step.md              → Project
.specs/hooks/after-implement-step.md               → Project
.specs/hooks/before-implement-step.local.md        → Local
.specs/hooks/after-implement-step.local.md         → Local
```

### Step 3 — Read Frontmatter

For each existing hook file, parse the YAML frontmatter to extract:
- `mode`: `extend` (default) or `override`

### Step 4 — Display Results

#### Single command view (`/spec.hooks plan`)

```
Hooks for /spec.plan:

  BEFORE:
    ✓ ~/.claude/livespec/hooks/before-plan.md          (global, extend)
    ✓ .specs/hooks/before-plan.md                      (project, extend)
    ✓ .specs/hooks/before-plan.local.md                (local, extend)

  AFTER:
    ✓ ~/.claude/livespec/hooks/after-plan.md           (global, extend)
    ✗ .specs/hooks/after-plan.md                       (not found)
    ✗ .specs/hooks/after-plan.local.md                 (not found)

  Resolution: global → project → local (all extend)
```

If a local hook uses `mode: override`:

```
Hooks for /spec.plan:

  BEFORE:
    ✗ ~/.claude/livespec/hooks/before-plan.md          (global — SKIPPED by override)
    ✗ .specs/hooks/before-plan.md                      (project — SKIPPED by override)
    ✓ .specs/hooks/before-plan.local.md                (local, override)

  Resolution: local only (override active)
```

#### Summary view (`/spec.hooks`)

```
LiveSpec Hooks Summary:

  Command       Before              After
  ─────────     ─────────           ─────────
  init          —                   —
  specify       project             —
  plan          global + project    global
  implement     global + local      —
    step        project             project + local
  check         —                   —
  explain       —                   —
  stack         —                   —
  feature       project             —
  refine        —                   —
  preflight     —                   —

  Legend: global = ~/.claude/livespec/hooks/
          project = .specs/hooks/*.md (committed)
          local = .specs/hooks/*.local.md (gitignored)
```

### Step 5 — Show Content (with `--verbose`)

If `--verbose` is provided, also display the first 10 lines of each active hook:

```
Hooks for /spec.plan:

  BEFORE:
    ✓ ~/.claude/livespec/hooks/before-plan.md (global, extend)
      │ ## Code Conventions
      │ Before planning, load and apply code conventions:
      │ - Read code conventions from the project's CLAUDE.md references
      │ ...

    ✓ .specs/hooks/before-plan.md (project, extend)
      │ ## Domain Context
      │ - This is a fintech project. Consider PCI-DSS compliance.
      │ ...
```

---

## Flags

| Flag | Behavior |
|------|----------|
| `--verbose` | Show first 10 lines of each active hook file |

---

## Output

This command produces no files. It is read-only and diagnostic.

---

## Definition of Done (Command-Level)

`/spec.hooks` is complete when:

- [ ] All 3 hook levels are scanned (global, project, local)
- [ ] Step-level hooks are shown for `implement` command
- [ ] Override mode is correctly reflected (parent hooks marked as SKIPPED)
- [ ] Summary view shows all commands when no argument provided
- [ ] No files are created or modified

---

*LiveSpec Command v1.0*
