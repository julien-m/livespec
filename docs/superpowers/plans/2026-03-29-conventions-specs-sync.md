# Conventions ↔ Specs Sync — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically generate and refresh `.conventions/conventions.md` from the stack declared in `.specs/stacks/_default.md`, triggered by LiveSpec hooks.

**Architecture:** Four global LiveSpec hooks trigger `conventions.init`/`conventions.refresh` at the right moments. `conventions.init` gains a spec-aware detection path that reads `_default.md` as a complementary source. A date comparison mechanism (`stacks.updated` vs `conventions.generated` vs `ai-ressources/.last-updated`) avoids unnecessary refreshes.

**Tech Stack:** Markdown instruction files (LiveSpec commands, ai-ressources skills, LiveSpec hooks). No runtime code.

**Design spec:** `docs/superpowers/specs/2026-03-29-conventions-specs-sync-design.md`

---

## File Structure

### New files

| File | Responsibility |
|---|---|
| `hooks/after-init.md` | Hook: trigger `conventions.init` after `/spec.init` |
| `hooks/after-stack.md` | Hook: trigger `conventions.refresh --full` after `/spec.stack` |
| `hooks/before-plan.md` | Hook: freshness check + conditional refresh before `/spec.plan` |
| `hooks/before-implement.md` | Hook: freshness check + conditional refresh before `/spec.implement` |

### Modified files

| File | Change |
|---|---|
| `commands/spec-init.md` | Add Dev Tooling questions in Phase B + `updated` frontmatter in Phase C |
| `commands/spec-stack.md` | Bump `updated` field after every stack change (Step 5) |
| `stacks/presets/web-realtime.md` | Add optional Dev Tooling rows |
| `stacks/presets/api-rest.md` | Add optional Dev Tooling rows |
| `stacks/presets/web-static.md` | Add optional Dev Tooling rows |
| `scripts/install.sh` | Add hooks installation (symlink `hooks/*.md` → `~/.claude/livespec/hooks/`) |
| `~/projects/ai-ressources/claude/skills/conventions.init/SKILL.md` | Add spec-aware detection in Phase 1 |
| `~/projects/ai-ressources/claude/skills/conventions.refresh/SKILL.md` | Add spec-aware freshness check |

---

## Task 1: Add `updated` frontmatter to `_default.md` in `commands/spec-init.md`

**Files:**
- Modify: `commands/spec-init.md:353-385` (Phase C installation)

- [ ] **Step 1: Add `updated` frontmatter instruction to Phase C**

In `commands/spec-init.md`, after the Phase C directory structure listing (line 385), find the section that describes generating `_default.md` from Phase B decisions. Add an instruction that the generated `_default.md` MUST include a YAML frontmatter block:

```markdown
### Step 3.x — Generate `_default.md` with frontmatter

When generating `.specs/stacks/_default.md` from Phase B decisions, **always** include a YAML frontmatter block:

\`\`\`yaml
---
updated: {today's date YYYY-MM-DD}
---
\`\`\`

This `updated` field is used by LiveSpec hooks to determine if `.conventions/conventions.md` needs refreshing. It is bumped by `/spec.stack` on every stack change.
```

Insert this after the existing directory structure block and before Step 3.9 (Generate Roadmap).

- [ ] **Step 2: Verify the directory structure listing includes frontmatter hint**

In the `.specs/` directory tree listing (lines 358-384), update the `_default.md` comment:

Change:
```
│   ├── _default.md         ← Generated from Phase B decisions
```

To:
```
│   ├── _default.md         ← Generated from Phase B decisions (with `updated` frontmatter)
```

- [ ] **Step 3: Verify no conflicts with existing content**

Read `commands/spec-init.md` lines 350-400 to confirm the insertion point doesn't break existing step numbering. Adjust step numbers if needed.

---

## Task 2: Add Dev Tooling questions to `commands/spec-init.md` Phase B

**Files:**
- Modify: `commands/spec-init.md:279-340` (Phase B, after Step 3 Testing Strategy)

- [ ] **Step 1: Add Dev Tooling substep after Testing Strategy**

After "### Step 3 — Testing Strategy" (line 279) and before "### Step 3.5 — Design Tool Check" (line 295), add a new step:

```markdown
### Step 3.1 — Dev Tooling (Optional)

After confirming the testing strategy, offer dev tooling choices:

> I have a few quick tooling questions. These help generate accurate coding conventions. Skip any you don't have a preference on.
>
> **Package manager?**
> - npm (default)
> - pnpm (fast, disk-efficient)
> - bun (fastest, native TypeScript)
> - yarn
>
> **Linter / Formatter?**
> - ESLint + Prettier (classic, wide plugin support)
> - Biome (fast, unified lint + format)
> - None

If the user skips or has no preference, use sensible defaults based on the stack:
- TypeScript project → ESLint + Prettier (unless Biome detected in existing config)
- Bun runtime → bun as package manager

Add the chosen tools as rows in the stack table under a "Dev Tooling" separator comment:

| Layer | Choice | Reason |
|---|---|---|
| ... existing layers ... |
| <!-- Dev Tooling --> |
| Package Manager | bun | User choice |
| Linter | Biome | User choice |
| Formatter | Biome | Same tool as linter |

These rows are optional — they appear in `_default.md` only if the user provided preferences.
```

- [ ] **Step 2: Verify step numbering**

Ensure the new step 3.1 doesn't conflict with existing 3.5 (Design Tool Check). The numbering is non-sequential already (3 → 3.5), so 3.1 fits naturally between 3 and 3.5.

---

## Task 3: Bump `updated` in `commands/spec-stack.md`

**Files:**
- Modify: `commands/spec-stack.md:254-257` (Step 5 — Update _default.md)

- [ ] **Step 1: Add `updated` bump instruction**

Find "#### Step 5 — Update _default.md" (line 254) which currently says:

```markdown
#### Step 5 — Update _default.md

Update `.specs/stacks/_default.md` to reflect the new stack decisions.
```

Replace with:

```markdown
#### Step 5 — Update _default.md

Update `.specs/stacks/_default.md` to reflect the new stack decisions.

**Always bump the `updated` field in the YAML frontmatter to today's date.** If the file does not have a frontmatter block, add one:

\`\`\`yaml
---
updated: {today's date YYYY-MM-DD}
---
\`\`\`

This date is compared against `.conventions/conventions.md`'s `generated` date by the `before-plan` and `before-implement` hooks to determine if conventions need refreshing.
```

---

## Task 4: Add Dev Tooling rows to stack presets

**Files:**
- Modify: `stacks/presets/web-realtime.md`
- Modify: `stacks/presets/api-rest.md`
- Modify: `stacks/presets/web-static.md`

- [ ] **Step 1: Read the Recommended Stack table in each preset**

Read the "## Recommended Stack" section of each preset to find where to add the Dev Tooling rows.

- [ ] **Step 2: Add optional Dev Tooling section to `web-realtime.md`**

After the last row of the Recommended Stack table, add:

```markdown
| **Dev Tooling** | | |
| Package Manager | npm / pnpm / bun | User preference — ask during init |
| Linter | ESLint / Biome | ESLint: wider ecosystem; Biome: faster |
| Formatter | Prettier / Biome | Prettier: standard; Biome: unified with linter |
```

- [ ] **Step 3: Add the same Dev Tooling section to `api-rest.md`**

Same rows as step 2, appended to its Recommended Stack table.

- [ ] **Step 4: Add the same Dev Tooling section to `web-static.md`**

Same rows as step 2, appended to its Recommended Stack table.

---

## Task 5: Create the 4 hook files

**Files:**
- Create: `hooks/after-init.md`
- Create: `hooks/after-stack.md`
- Create: `hooks/before-plan.md`
- Create: `hooks/before-implement.md`

- [ ] **Step 1: Create `hooks/after-init.md`**

```markdown
# After Init — Generate Conventions

After `/spec.init` completes and `.specs/stacks/_default.md` has been created, generate the project's coding conventions.

## Instructions

1. Check if `.conventions/conventions.md` already exists
   - If it exists → skip (conventions already initialized)
   - If it does not exist → continue

2. Run `/conventions.init`
   - The skill will automatically detect `.specs/stacks/_default.md` and use it as a stack source
   - This generates `.conventions/conventions.md` with the correct conventions for the declared stack

3. Report briefly:
   ```
   Conventions generated from stack in .specs/stacks/_default.md
   ```
```

- [ ] **Step 2: Create `hooks/after-stack.md`**

```markdown
# After Stack — Refresh Conventions

After `/spec.stack` completes and the stack has changed, refresh coding conventions to match the new stack.

## Instructions

1. Check if `.conventions/conventions.md` exists
   - If it does not exist → run `/conventions.init` instead and stop
   - If it exists → continue

2. Run `/conventions.refresh --full`
   - Full mode re-detects domains from scratch (new stack components may add/remove entire convention categories)
   - The skill will automatically detect `.specs/stacks/_default.md` and use the updated stack

3. Report briefly:
   ```
   Conventions refreshed after stack change
   ```
```

- [ ] **Step 3: Create `hooks/before-plan.md`**

```markdown
# Before Plan — Ensure Fresh Conventions

Before `/spec.plan` starts, verify that `.conventions/conventions.md` is up to date with the current stack and ai-ressources knowledge base.

## Instructions

### Freshness check

Read three dates:
1. `generated` from `.conventions/conventions.md` YAML frontmatter
2. `updated` from `.specs/stacks/_default.md` YAML frontmatter
3. Content of `~/projects/ai-ressources/.last-updated`

### Decision

- If `.conventions/conventions.md` does **not** exist AND `.specs/stacks/_default.md` exists:
  → Run `/conventions.init`. Report: `Conventions initialized before planning.`

- If `.conventions/conventions.md` exists AND `generated` < `updated` (stack changed since last conventions generation):
  → Run `/conventions.refresh --full`. Report: `Conventions refreshed (stack changed since last generation).`

- If `.conventions/conventions.md` exists AND `generated` < `ai-ressources/.last-updated` (rules changed):
  → Run `/conventions.refresh`. Report: `Conventions refreshed (ai-ressources updated).`

- If `.conventions/conventions.md` exists AND `generated` >= both dates:
  → Skip silently. Do not report anything.

- If `.specs/stacks/_default.md` does **not** exist:
  → Skip silently. This project does not use LiveSpec stack management.

### Notes

- If `updated` is missing from `_default.md` frontmatter, treat it as "always stale" (triggers refresh). The refresh will not add the field — that is `/spec.stack`'s responsibility.
- If `~/projects/ai-ressources/.last-updated` does not exist, skip that comparison.
```

- [ ] **Step 4: Create `hooks/before-implement.md`**

```markdown
# Before Implement — Ensure Fresh Conventions

Before `/spec.implement` starts, verify that `.conventions/conventions.md` is up to date with the current stack and ai-ressources knowledge base.

## Instructions

### Freshness check

Read three dates:
1. `generated` from `.conventions/conventions.md` YAML frontmatter
2. `updated` from `.specs/stacks/_default.md` YAML frontmatter
3. Content of `~/projects/ai-ressources/.last-updated`

### Decision

- If `.conventions/conventions.md` does **not** exist AND `.specs/stacks/_default.md` exists:
  → Run `/conventions.init`. Report: `Conventions initialized before implementation.`

- If `.conventions/conventions.md` exists AND `generated` < `updated` (stack changed since last conventions generation):
  → Run `/conventions.refresh --full`. Report: `Conventions refreshed (stack changed since last generation).`

- If `.conventions/conventions.md` exists AND `generated` < `ai-ressources/.last-updated` (rules changed):
  → Run `/conventions.refresh`. Report: `Conventions refreshed (ai-ressources updated).`

- If `.conventions/conventions.md` exists AND `generated` >= both dates:
  → Skip silently. Do not report anything.

- If `.specs/stacks/_default.md` does **not** exist:
  → Skip silently. This project does not use LiveSpec stack management.

### Notes

- If `updated` is missing from `_default.md` frontmatter, treat it as "always stale" (triggers refresh). The refresh will not add the field — that is `/spec.stack`'s responsibility.
- If `~/projects/ai-ressources/.last-updated` does not exist, skip that comparison.
```

---

## Task 6: Update `install.sh` to link hooks

**Files:**
- Modify: `scripts/install.sh`

- [ ] **Step 1: Add hooks array to config section**

After the `AGENTS` array (line 18), add:

```bash
HOOKS_SRC_DIR="$LIVESPEC_ROOT/hooks"
HOOKS_DST_DIR="$HOME/.claude/livespec/hooks"
```

- [ ] **Step 2: Add hooks installation logic**

After the agents installation loop, add a hooks installation section that:
1. Creates `$HOOKS_DST_DIR` if it doesn't exist (`mkdir -p`)
2. Iterates over all `.md` files in `$HOOKS_SRC_DIR`
3. For each file, creates a symlink in `$HOOKS_DST_DIR` (same logic as commands/agents: check existence, respect `--force`, `--dry-run`)

- [ ] **Step 3: Add hooks uninstall logic**

In the uninstall section, add removal of hook symlinks from `$HOOKS_DST_DIR`.

- [ ] **Step 4: Update the help text**

Update the help message to mention hooks installation:

```
Installs LiveSpec /spec.* commands, agents, and hooks into ~/.claude/.
```

---

## Task 7: Add spec-aware detection to `conventions.init`

**Files:**
- Modify: `~/projects/ai-ressources/claude/skills/conventions.init/SKILL.md`

- [ ] **Step 1: Add spec-aware detection step at the start of Phase 1**

Before "1. **Dependencies**" (line 22), add a new step 0:

```markdown
0. **Spec stack (if available)** — Check if `.specs/stacks/_default.md` exists in the project root. If it does:
   - Read the file
   - Find the first Markdown table with a "Layer" or "Technology" column header
   - Extract each row: the layer name (column 1) and the choice value (column 2)
   - Store the extracted layers as an additional detection source. These are merged with the code scan results in Phase 2.

   This enables conventions generation for greenfield projects where no code exists yet but the stack is declared in LiveSpec specs.

   If `.specs/stacks/_default.md` does not exist, skip this step silently. The rest of Phase 1 proceeds as normal.
```

- [ ] **Step 2: Add spec layer mapping to Phase 2**

After the Channel 1b section (line 83), add a new paragraph:

```markdown
#### Spec-aware detection (merges with channels above)

If step 0 extracted layers from `.specs/stacks/_default.md`, map each layer's choice value to convention domains:

| Choice value contains (case-insensitive) | Treated as |
|---|---|
| `typescript`, `javascript` | `.ts`/`.js` extension detected (Channel 1) |
| `go` | `.go` extension detected (Channel 1) |
| `rust` | `.rs` extension detected (Channel 1) |
| `swift`, `kotlin` | `.swift`/`.kt` extension detected (Channel 1) |
| `delphi`, `pascal` | `.pas` extension detected (Channel 1) |
| `next.js`, `next` | `next` dependency detected (Channel 1b) |
| `react` | `react` dependency detected (Channel 1b) |
| `tailwind` | `tailwindcss` dependency detected (Channel 1b) |
| `shadcn` | `@shadcn/ui` dependency detected (Channel 1b) |
| `cloudflare`, `hono`, `workers` | `wrangler.toml` detected (Channel 1b) |
| `tanstack` | `@tanstack/*` dependency detected (Channel 1b) |
| `drizzle` | `drizzle-orm` dependency detected (Channel 1b) |
| `prisma` | `@prisma/client` dependency detected (Channel 1b) |
| `remotion` | `remotion` dependency detected (Channel 1b) |
| `postgresql`, `sqlite`, `mysql` | `.sql` extension detected (Channel 1) |
| `supabase`, `stripe`, `redis`, etc. | Package name for Channel 2 lookup |

**Merge strategy:** Union. Spec layers and code scan results are combined. If both sources detect the same domain, it appears once. If only specs or only code detects a domain, it's included.

This means on a greenfield project (no code), the specs alone provide enough signal to generate accurate conventions. On an existing project, both sources enrich each other.
```

- [ ] **Step 3: Verify the changes don't break the existing flow**

Read the full SKILL.md after modifications to confirm Phase 1 → Phase 2 → Phase 3 → Phase 4 flow is intact. The spec-aware detection adds data to the existing pipeline without changing the downstream phases.

---

## Task 8: Add spec-aware freshness check to `conventions.refresh`

**Files:**
- Modify: `~/projects/ai-ressources/claude/skills/conventions.refresh/SKILL.md`

- [ ] **Step 1: Extend the default mode freshness check**

In the "### Default mode (date check)" section (lines 18-24), replace the 3-step procedure with:

```markdown
### Default mode (date check)

1. **Read** the `generated` date from the YAML frontmatter of `.conventions/conventions.md`
2. **Read** `~/projects/ai-ressources/.last-updated` to get the last modification date of the knowledge base
3. **Read** the `updated` date from `.specs/stacks/_default.md` YAML frontmatter (if the file exists)
4. **Compare** (in priority order):
   - If `.specs/stacks/_default.md` exists AND has an `updated` field AND `generated` < `updated` → conventions are stale (stack changed), proceed to **full** regeneration (re-detect domains, same as `--full` mode)
   - If `generated` < `.last-updated` → conventions are stale (rules changed), proceed to regeneration (same categories)
   - Otherwise → conventions are up to date, stop

Note: If `.specs/stacks/_default.md` does not exist or has no `updated` frontmatter, skip the stack comparison and fall back to the ai-ressources date check only.
```

- [ ] **Step 2: Update the Rules section**

Add a new rule after the existing rules (line 64):

```markdown
- When stack staleness is detected (`generated` < `stacks.updated`), use `--full` mode automatically (re-detect domains) because a stack change may add/remove entire convention categories
- When only ai-ressources staleness is detected, use default mode (same categories, refreshed content)
```

- [ ] **Step 3: Update the Output section**

Add a new output message for spec-triggered refresh:

```markdown
Stack-triggered full refresh:
```
Full refresh (stack changed): 6 categories (was 5), 1 new (cloudflare), all regenerated
```
```

---

## Dependency Graph

```
Task 1 (updated frontmatter) ─┐
Task 2 (dev tooling questions) ├── independent, all in livespec/commands/
Task 3 (stack.md bump)        ─┘

Task 4 (presets)               ── independent

Task 5 (hooks)                 ── independent (references conventions.init/refresh but doesn't modify them)

Task 6 (install.sh)           ── depends on Task 5 (hooks must exist to be linked)

Task 7 (conventions.init)     ── independent (in ai-ressources)
Task 8 (conventions.refresh)  ── independent (in ai-ressources)
```

**Parallel groups:**
- Group A: Tasks 1, 2, 3 (livespec commands)
- Group B: Task 4 (presets)
- Group C: Task 5 (hooks)
- Group D: Tasks 7, 8 (ai-ressources)
- Sequential: Task 6 after Task 5

All groups A, B, C, D can run in parallel.
