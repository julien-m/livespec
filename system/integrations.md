# LiveSpec — User-Level Integrations (Level 0)

> Markdown instructions in `~/.config/livespec/*.md` that LiveSpec injects
> into the context of selected commands. **Read** [`hooks.md`](hooks.md) for
> the resolution algorithm. **Read** [`spec-system.md`](spec-system.md) for the
> framework overview.

---

## Concept

Two extension surfaces live under `~/.config/livespec/`:

| Path | Content | Consumed by |
|------|---------|-------------|
| `~/.config/livespec/provider.py` | Python callable (LLM routing) | LiveSpec runtime via `import` |
| `~/.config/livespec/<name>.md` | Markdown instructions | LLM orchestrator at the right hook event |

This document covers the **Markdown** pattern only. The two surfaces are
complementary and decoupled — installing or removing one does not affect
the other.

The LiveSpec core is **tool-agnostic**: it never hard-codes the name of
any specific integration. The presence (or absence) of any `*.md` file
is the only signal.

---

## Location

```
~/.config/livespec/
├── provider.py          (existing — Python callable)
└── <integration>.md     (this pattern — markdown instructions, optional)
```

Multiple integration files may coexist (e.g. `mockups.md`, `compliance.md`).
Each file targets one or more commands via its frontmatter.

---

## Frontmatter schema

The file MUST open with a YAML frontmatter block (delimited by `---` on
the very first line). Comments inside the frontmatter (`#`-prefixed lines)
are tolerated.

```yaml
---
integration: <name>            # REQUIRED — logical name, non-empty string
commands: [<cmd>, ...]         # REQUIRED — non-empty list of command names
phase: before | after          # default: before
mode: extend | override        # default: extend
order: <int>                   # default: 100 — lower = injected earlier
---

<markdown body — injected as-is, with template variables resolved>
```

### Single eligibility rule

A file is treated as an integration **if and only if** its frontmatter
contains BOTH the `integration:` key AND the `commands:` key.

| Case | Behavior |
|------|----------|
| No frontmatter at all | **Silently ignored** (free notes tolerated) |
| Frontmatter, missing `integration:` | **Silently ignored** |
| Frontmatter, missing `commands:` | **Silently ignored** |
| Frontmatter, both keys present, well-formed | **Used** |
| Frontmatter, both keys, but malformed (unknown command, invalid mode/types, broken YAML) | **Single stderr warning + skipped** |

A file that declares itself an integration is *engaged* — any malformation
is signalled exactly once on stderr.

### Valid commands

The canonical command set is the contents of `.agent-sync/skills/spec-*` in
the LiveSpec repo. There is no other allowlist: adding a new skill directory
with `SKILL.md` and `expectations.md` automatically makes it a valid target.
See `validator.integrations.valid_command_names()`.

---

## Resolution order

For a given event `(before|after)-<cmd>`, the chain is:

```
Level 0: ~/.config/livespec/*.md         (Level 0 — integrations, sorted)
  ↓
Level 1: ~/.claude/livespec/hooks/...    (Global)
  ↓
Level 2: .specs/hooks/...                (Project)
  ↓
Level 3: .specs/hooks/*.local.md         (Personal)
```

Within Level 0, files are sorted by `(order ASC, basename ASC)`.

### Override scope (bounded)

| `mode:` location | Effect |
|------------------|--------|
| `override` on a Level 0 file | All other Level 0 files for this event are discarded. **Levels 1/2/3 are NOT affected.** |
| `override` on a Level 3 (`.local.md`) hook | Levels 1 and 2 are skipped. **Level 0 is NOT affected.** |

Two `mode: override` integrations targeting the same event raise an
explicit error — `Multiple override integrations for event <before|after>-<cmd>`.

### Dedup

Two integration files declaring the same `(name, sorted(commands), phase)`
triple raise an error at discovery time — silent shadowing is refused.

---

## Template variables

The same variables as `system/hooks.md` are substituted in the body:

| Variable | Source |
|----------|--------|
| `{{command}}` | The invoked command (always resolved) |
| `{{feature_name}}` | Feature slug (when CLI is called with `--feature`) |
| `{{feature_number}}` | First 3 digits of the slug (zero-padded), if the slug matches `^\d{3}-` |
| `{{feature_path}}` | `.specs/features/<slug>/` |
| `{{stack}}` | Read from `.specs/stacks/_default.md` (best effort) |
| `{{project_name}}` | Read from `.specs/project.md` or `cwd().name` (always resolved) |

**Unresolved variables stay literal in the output** — no warning, no
error. This is intentional (`system/hooks.md` § Template Variables): a
hook can be re-used outside a feature context without crashing.

### `{{feature_number}}` literal pass-through

When `--feature` is provided but the slug does not match `^\d{3}-`
(e.g. test fixtures, legacy slugs), `{{feature_number}}` is left literal.
No warning is emitted — the responsibility of slug validation lies with
the Identity Guard of `.agent-sync/skills/spec-feature/SKILL.md`, not the resolver.

---

## Runtime injection

LiveSpec commands invoke the runtime CLI from the directive injected by
`system/anti-drift-block.md`:

```bash
livespec hooks resolve --event before --command <cmd> [--feature <slug>]
livespec hooks resolve --event after  --command <cmd> [--feature <slug>]
```

The CLI prints the concatenated, template-rendered chain on stdout
(blocks separated by `\n\n---\n\n`). Stdout is empty when nothing
applies. Exit code is **always 0** — absence is never an error.

Diagnostic (read-only) :

```bash
livespec integrations list           # tabular view of all L0 files
/spec-hooks <command>                # shows the full L0→L3 chain for <command>
```

---

## Chained / pipeline invocations

The hook resolver always receives the name of the **currently executing
sub-command**, not the outer pipeline. Implementation contract (locked
by Decision D-α option β):

1. `/spec-feature` resolves `before-feature` / `after-feature` at its
   outer boundary.
2. Before spawning each subagent (Specify, Plan, Implement, Test, …), the
   `.agent-sync/skills/spec-feature/SKILL.md` supervisor resolves the current
   LiveSpec `project_root`, runs the subagent with `cwd`/working directory fixed
   to that root, and prepends a synthetic `/spec-<subcmd>` invocation header.
   If the native agent API has no cwd field, the prompt first instructs
   `cd <project_root>` and **Read** [`../.specs/spec-system.md`](../.specs/spec-system.md).
   The subagent then resolves `before-<subcmd>` / `after-<subcmd>`.
3. The same rule applies to `.agent-sync/skills/spec-ship/SKILL.md` (batch wrapper).
4. **No automatic propagation from outer to inner.** Integrations target
   sub-phases by listing them explicitly in `commands:`. To inject at
   both outer and inner, list every relevant name.

> ⚠️ `--economy` mode and Level 0 integrations
>
> Integrations targeting sub-phases (`commands: [specify, plan, implement, …]`)
> are NOT injected when running `/spec-feature --economy`. The economy mode
> executes those phases inline in the main context without spawning subagents,
> so the runtime directive only resolves at the outer `feature` boundary.
>
> Workaround: omit `--economy` (default pipeline mode injects normally), OR
> list `feature` explicitly in `commands:` to inject at the outer boundary in
> both modes.

---

## Disable / remove an integration

Removing or renaming the file in `~/.config/livespec/` is enough — there
is no cache, no daemon, no registry. The next command invocation sees an
empty Level 0 and behaves exactly as before installing the integration.

---

## Examples

### Minimal — inject before `plan` only

```markdown
---
integration: domain-rules
commands: [plan]
---

When planning, always include a "Compliance" section listing PCI-DSS hooks.
```

### Targeting multiple phases

```markdown
---
integration: mockups
commands: [specify, plan]
order: 50
---

Generate or refresh visual mockups via `/mockup-factory` before producing
screens or design plans.
```

### `after` hook with template variables

```markdown
---
integration: changelog-reminder
commands: [implement]
phase: after
---

Feature `{{feature_name}}` is implemented. Remember to update CHANGELOG.md
under the **Unreleased** section.
```

---

## Differences with `~/.config/livespec/provider.py`

| | `provider.py` | `<name>.md` |
|--|---------------|-------------|
| Type | Python module (callable) | Markdown text |
| Loaded by | LiveSpec runtime (Python `import`) | LLM orchestrator via `livespec hooks resolve` |
| Purpose | Override LLM routing (e.g. local model) | Inject prompt context at hook events |
| Required keys | `call_llm(...)` function | YAML frontmatter `integration:` + `commands:` |

The two are entirely independent — installing one has no effect on the
other.

---

## Adding a new subagent spawn site

If a new `.agent-sync/skills/spec-*/SKILL.md` adds a subagent spawn, its prompt
template MUST propagate the current LiveSpec `project_root`, set child
`cwd`/working directory to that root (or prompt `cd <project_root>` + **Read**
[`../.specs/spec-system.md`](../.specs/spec-system.md) when no native cwd field
exists), and prepend a synthetic `/spec-<subcmd>` header so the subagent's
anti-drift directive resolves the correct command name. This is enforced by
`tests/test_pipeline_chained_resolution.py` and command audit.

---

*LiveSpec Integrations v1.0 — see `.agent-sync/skills/spec-hooks/SKILL.md` for the diagnostic UX.*
