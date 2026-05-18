# Preflight System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Preflight System to LiveSpec that verifies tooling, authentication, and credentials before autonomous work begins.

**Architecture:** Three components — a Generator that infers checks from the stack, a Manifest file (`.specs/preflight.md`) that is the source of truth, and an Execution Engine described in the command file that runs checks in 3 passes (parallel verify → sequential auto-resolve → grouped human blockers). Integrated into existing commands as Phase D (init), post-generation hook (specify), Phase 0.5 (implement/feature), and post-ADR hook (stack).

**Tech Stack:** Markdown command files (LiveSpec convention), Bash (install.sh), Markdown templates

**Spec:** `docs/superpowers/specs/2026-03-19-preflight-system-design.md`

---

## File Structure

### New files

| File | Responsibility |
|------|----------------|
| `commands/spec-preflight.md` | Standalone `/spec.preflight` command — manifest parsing, 3-pass execution engine, report generation, `--light`/`--regenerate`/`--dry-run` flags |
| `system/templates/preflight-manifest-template.md` | Template for `.specs/preflight.md` with section structure and Custom markers |
| `system/templates/preflight-report-template.md` | Template for `.specs/preflight-report.md` with Summary/Verdict/Details structure |

### Modified files

| File | Change |
|------|--------|
| `commands/spec-init.md` | Add Phase D after Phase C — generate manifest, execute full preflight, update exit criteria |
| `commands/spec-specify.md` | Add post-generation hook — detect Infrastructure Requirements, propose manifest additions |
| `commands/spec-implement.md` | Add Phase 0.5 before Phase 1 — light preflight check before implementation |
| `commands/spec-feature.md` | Add Phase 2.7 before Phase 3 — light preflight check before implementation phase |
| `commands/spec-stack.md` | Add Step 7 after Step 6 — regenerate manifest on stack change |
| `scripts/install.sh` | Add `preflight` to COMMANDS array |
| `system/spec-system.md` | Add `preflight.md` and `preflight-report.md` to `.specs/` layout |

---

## Task 1: Preflight manifest template

**Files:**
- Create: `system/templates/preflight-manifest-template.md`

- [ ] **Step 1: Create the manifest template**

```markdown
# Preflight Manifest

> Auto-generated from stack and specs. Editable — changes are preserved on regeneration.

## Tooling

<!-- Generated tooling checks appear here -->

## Authentication

<!-- Generated authentication checks appear here -->

## Tokens

<!-- Generated token checks appear here -->

## Custom

<!-- preflight:custom:start -->
<!-- Add manual checks here. Use the same ### format as above. Set source: manual -->
<!-- preflight:custom:end -->
```

Write this to `system/templates/preflight-manifest-template.md`.

- [ ] **Step 2: Verify file exists**

Run: `cat system/templates/preflight-manifest-template.md | head -5`
Expected: Shows the `# Preflight Manifest` header

- [ ] **Step 3: Commit**

```bash
git add system/templates/preflight-manifest-template.md
git commit -m "feat(preflight): add manifest template with Custom section markers"
```

---

## Task 2: Preflight report template

**Files:**
- Create: `system/templates/preflight-report-template.md`

- [ ] **Step 1: Create the report template**

```markdown
# Preflight Report

> Generated: <ISO-8601> | Mode: <full|light> | Duration: <seconds>

## Summary

| Category | Total | Pass | Auto-resolved | Failed | Blocked |
|----------|-------|------|---------------|--------|---------|
| Tooling | 0 | 0 | 0 | 0 | 0 |
| Authentication | 0 | 0 | 0 | 0 | 0 |
| Tokens | 0 | 0 | 0 | 0 | 0 |
| Custom | 0 | 0 | 0 | 0 | 0 |
| **Total** | **0** | **0** | **0** | **0** | **0** |

## Verdict: READY

### Auto-resolved

_None_

### Blocked (human action required)

_None_

## Details

### Tooling

| Check | Status | Command | Duration |
|-------|--------|---------|----------|

### Authentication

| Check | Status | Command | Duration |
|-------|--------|---------|----------|

### Tokens

| Check | Status | Command | Duration |
|-------|--------|---------|----------|

### Custom

| Check | Status | Command | Duration |
|-------|--------|---------|----------|
```

Write this to `system/templates/preflight-report-template.md`.

- [ ] **Step 2: Verify file exists**

Run: `cat system/templates/preflight-report-template.md | head -5`
Expected: Shows the `# Preflight Report` header

- [ ] **Step 3: Commit**

```bash
git add system/templates/preflight-report-template.md
git commit -m "feat(preflight): add report template with Summary/Verdict/Details structure"
```

---

## Task 3: Standalone `/spec.preflight` command

This is the core command file. It defines the Generator (stack-to-checks catalog), the Execution Engine (3-pass algorithm), and the report generation logic.

**Files:**
- Create: `commands/spec-preflight.md`

- [ ] **Step 1: Create the command file**

The command must follow the existing LiveSpec command pattern (frontmatter → title → overview → steps → flags → definition of done). Write `commands/spec-preflight.md` with the following structure:

```markdown
---
description: "Verify tooling, auth, and credentials before autonomous work"
---

# Command: /spec.preflight

> Preflight check — verify all tools, sessions, and tokens are ready before autonomous implementation.

---

## Overview

`/spec.preflight [flags]`

Reads `.specs/preflight.md` (the manifest), executes verification checks, auto-resolves what it can, and presents human-required actions grouped together. Produces both inline terminal output and a persisted `.specs/preflight-report.md`.

Can also generate/regenerate the manifest from the project stack and feature specs.

---

## Manifest Format

The manifest (`.specs/preflight.md`) has 4 sections:

### Structure

Each check is a `###` heading with bullet-point fields:

**Tooling checks:**
```markdown
### <check-name>
- **binary:** `<binary-name>`
- **verify:** `<command to check presence/version>`
- **install:** `<command to install>`
- **severity:** critical | warning
- **source:** stack (_default.md) | spec (NNN-feature-name) | manual
```

**Authentication checks:**
```markdown
### <check-name>
- **type:** oauth
- **verify:** `<command to check session>`
- **resolve:** `<command to re-authenticate>`
- **severity:** critical | warning
- **expires:** true
- **source:** stack (_default.md) | spec (NNN-feature-name) | manual
```

**Token checks:**
```markdown
### <check-name>
- **type:** creds
- **entry:** `<creds entry path>`
- **verify:** `creds get <entry> > /dev/null 2>&1`
- **resolve:** human
- **severity:** critical | warning
- **source:** stack (_default.md) | spec (NNN-feature-name) | manual
```

**Custom section** uses markers:
```markdown
## Custom

<!-- preflight:custom:start -->
<!-- user entries here -->
<!-- preflight:custom:end -->
```

### Field Definitions

| Field | Values | Description |
|-------|--------|-------------|
| `binary` | String | Binary name (Tooling only) |
| `verify` | Shell command | Command to check if the check passes (exit 0 = pass) |
| `install` / `resolve` | Shell command or `human` | How to fix a failed check. `human` = requires user action |
| `severity` | `critical` / `warning` | Critical blocks implementation, warning is informational |
| `type` | `oauth` / `creds` | Authentication/Token type discriminator |
| `entry` | String | `creds` entry path (Tokens only) |
| `expires` | `true` / absent | If true, re-verified on every light check |
| `source` | String | Traceability — where this check was inferred from |
| `timeout` | Integer (seconds) | Per-check timeout override for `verify` command. Default: 10s |

### Custom Section Merge Algorithm

Regeneration preserves the Custom section:
1. Locate `<!-- preflight:custom:start -->` and `<!-- preflight:custom:end -->` markers
2. Extract content between markers verbatim
3. Regenerate Tooling, Authentication, Tokens sections from stack + specs
4. Re-insert Custom content between markers unchanged
5. If markers missing/malformed → abort, warn: "Custom section markers corrupted. Run `/spec.preflight --regenerate --force` to reset, or fix markers manually."
6. If duplicate check name between generated and Custom → keep both, rename Custom entry with `(custom)` suffix, warn

---

## Generator — Stack-to-Checks Catalog

| Stack detected in `_default.md` | Generated checks |
|---------------------------------|------------------|
| Cloudflare Workers | `wrangler` (tooling, critical) + `cloudflare-oauth` (auth, critical) |
| Supabase | `supabase` CLI (tooling) + `supabase-login` (auth) + token if direct API |
| Vercel | `vercel` CLI (tooling) + `vercel-oauth` (auth) |
| Next.js | `node` + `npm` (tooling) |
| Playwright | `npx playwright` (tooling) + `playwright install` (browsers) |
| Vitest / Jest | test runner (tooling, warning) |
| ESLint | linter (tooling, warning) |
| TypeScript | `tsc` (tooling, warning) |
| Stripe | `stripe` CLI (tooling) + `stripe-login` (auth) + `creds:*/stripe_secret_key` (token) |
| AWS | `aws` CLI (tooling) + `aws-sso` or `creds:*/aws_*` |
| GitHub API | `gh` CLI (tooling) + `gh-auth` (auth) |

This catalog is extensible — new mappings can be added as new stacks are supported.

### Generation Rules

1. **Parse `_default.md`** — extract the stack (framework, deploy, DB, auth, testing, etc.)
2. **Match catalog** — each recognized technology generates its checks
3. **Scan specs** — parse "Infrastructure Requirements" sections from all `spec.md` files for additional needs. If no feature specs exist yet (fresh init), only stack-level checks are generated
4. **Detect tokens** — if a `.env` file exists at project root, each `creds:*` entry becomes a Token check
5. **Deduplicate** — if a check already exists (manually added or from previous run), do not overwrite
6. **Preserve Custom** — everything in the Custom section is untouched

### Regeneration Behavior

When `--regenerate` is used:

1. Parse existing `preflight.md` and extract Custom section (between `<!-- preflight:custom:start -->` and `<!-- preflight:custom:end -->` markers)
2. If markers missing or malformed → abort, warn: "Custom section markers corrupted. Run `/spec.preflight --regenerate --force` to reset, or fix markers manually."
3. Read `.specs/stacks/_default.md` — extract stack technologies
4. Match against catalog — generate Tooling, Authentication, Tokens sections
5. Scan all `.specs/features/*/spec.md` for "Infrastructure Requirements" sections
6. If `.env` exists at project root, scan for `creds:*` entries → add Token checks
7. Deduplicate against existing entries (do not overwrite)
8. If duplicate check name between generated and Custom → keep both, rename Custom entry with `(custom)` suffix, warn
9. Re-insert Custom section between markers unchanged
10. Write updated `preflight.md`

When `--regenerate --force` is used: reset Custom section to empty template markers.

---

## Execution Engine — 3-Pass Algorithm

### Pass 1 — Verification (parallel)

Execute all `verify` commands in parallel (max concurrency: system default). Default timeout per command: 10 seconds (override with `timeout` field in manifest).

Each check receives a status:
- `pass` — exit code 0
- `fail` — exit code non-zero
- `error` — timed out or command not found

### Pass 2 — Auto-resolution (sequential)

For each `fail` check where `resolve`/`install` is not `human`:

0. If `source: manual` → prompt user: "Execute `[resolve command]` for check `[name]`? (y/n)". If declined → mark `failed`, escalate to Pass 3
1. Execute the `resolve`/`install` command
2. Re-execute the `verify` command
3. Final status: `resolved` (verify now passes) or `failed` (still failing)

Sequential to avoid conflicts (e.g., two npm installs racing).

Partial failure: if auto-resolution fails, mark check `failed` and escalate to Pass 3 as human blocker with the error output. No rollback — all install/resolve commands must be idempotent.

### Pass 3 — Human blockers (grouped)

Present all remaining `failed` checks that require human action together:

```
⚠ Preflight — N actions required:

  1. [TYPE] check-name
     → Run: <resolve command>

  ...

Resolve these, then press Enter to re-verify (or type 'skip' to continue — critical failures will still block).
```

After user action (Enter): run a full Pass 1 + Pass 2 cycle. This catches cascading dependencies. If new failures detected, re-enter Pass 3.

If user types 'skip': continue. Critical failures still enforce the gate.

Loop terminates when all checks pass or user skips.

---

## Report Generation

After execution (regardless of verdict — READY, WARNINGS, or BLOCKED), write `.specs/preflight-report.md` using the template from `system/templates/preflight-report-template.md`. Fill in:

- Generated timestamp (ISO-8601)
- Mode (`full` or `light`)
- Duration
- Summary table with counts per category
- Verdict: `READY` (all pass), `BLOCKED` (any critical failed), or `WARNINGS` (only warnings failed)
- Auto-resolved list
- Blocked list
- Details tables per category with check name, status symbol, command + output (version for `--version` commands, exit code only for token/auth checks), duration

Token values are **never** displayed — only `exists` or `missing`.

---

## Inline Output

### READY verdict

```
✓ Preflight Complete (N checks)

  Tooling         name1 ✓  name2 ✓
  Authentication  name3 ✓
  Tokens          name4 ✓
  Custom          name5 ✓

  ⏱ Xs | N passed, N auto-resolved, 0 blocked
```

### WARNINGS verdict

```
⚠ Preflight Complete with warnings (N checks)

  Tooling         name1 ✓  name2 ✓
  ...

  Warnings:
    name — reason (warning, non-blocking)

  ⏱ Xs | N passed, N auto-resolved, 0 blocked, N warning
```

### BLOCKED verdict

Execution does not complete — Pass 3 loop is active until resolved or skipped.

---

## Light Check Mode (`--light`)

Verifies only a subset of the manifest:
- Items with `expires: true` (OAuth sessions — may have expired)
- Items whose `source` references the current feature (if feature name provided)
- Items added since last full run (check name exists in manifest but not in Details tables of `preflight-report.md`)
- Skips all other items already `pass` at last run

If `preflight.md` does not exist: log warning "No preflight manifest found. Run `/spec.preflight --regenerate` to create one." and **continue** without blocking.

If `preflight-report.md` does not exist: treat all items as new (run full check set).

---

## Dry Run Mode (`--dry-run`)

Parse the manifest and display what would be checked without executing:

```
Preflight dry run — N checks would be executed:

  Tooling (N):        name1, name2, ...
  Authentication (N): name3, ...
  Tokens (N):         name4, ...
  Custom (N):         name5, ...

  Critical: N | Warning: N
```

---

## Gate Behavior

| Condition | Result |
|-----------|--------|
| Any `critical` check `failed` after Pass 3 | **BLOCKS** — cannot proceed to implementation |
| Only `warning` checks `failed` | Displays warning, **continues** |
| All checks `pass` or `resolved` | **READY** — proceeds normally |

---

## Flags

| Flag | Behavior |
|------|----------|
| `--light` | Light check — only expires, feature-source, and new items |
| `--regenerate` | Regenerate manifest from stack + specs (preserves Custom) |
| `--regenerate --force` | Regenerate manifest and reset Custom section |
| `--dry-run` | Show what would be checked without executing |

---

## Definition of Done (Command-Level)

`/spec.preflight` is complete only if all are true:

- [ ] `.specs/preflight.md` exists (or was just generated with `--regenerate`)
- [ ] All `verify` commands were executed (or skipped per `--light` rules)
- [ ] Auto-resolvable failures were attempted
- [ ] Human blockers were presented grouped (if any)
- [ ] `.specs/preflight-report.md` was written with Verdict
- [ ] Inline output was displayed with summary
- [ ] If called as Phase 0.5: gate behavior enforced (critical = block, warning = continue)

---

## Changelog Policy

Preflight manifest updates are infrastructure-level artifacts — they do not generate entries in feature changelogs or the global `.specs/changelog.md`.

---

## Security

- Auto-generated entries use only well-known package manager commands
- Entries with `source: manual` require user confirmation before auto-resolution
- Token values are never displayed — only existence checked via `creds get ... > /dev/null`
- The manifest is versioned in git — modifications visible in diffs

---

*LiveSpec Command v1.0*
```

Write this content verbatim to `commands/spec-preflight.md`. All sections are fully expanded — no placeholders remain.

- [ ] **Step 2: Verify file structure**

Run: `head -10 commands/spec-preflight.md`
Expected: Shows frontmatter with description and `# Command: /spec.preflight` title

- [ ] **Step 3: Verify command follows pattern**

Check: file has frontmatter (`---`), title (`# Command:`), Overview, Steps/Sections, Flags table, Definition of Done — matching the pattern of `commands/spec-init.md`, `commands/spec-implement.md`, etc.

- [ ] **Step 4: Commit**

```bash
git add commands/spec-preflight.md
git commit -m "feat(preflight): add /spec.preflight command with 3-pass engine and generator"
```

---

## Task 4: Update `scripts/install.sh`

**Files:**
- Modify: `scripts/install.sh:17` (COMMANDS array)

- [ ] **Step 1: Add `preflight` to COMMANDS array**

Change line 17 from:
```bash
COMMANDS=(init propose specify plan implement check explain stack feature refine play-coverage)
```
to:
```bash
COMMANDS=(init propose specify plan implement check explain stack feature refine play-coverage preflight)
```

- [ ] **Step 2: Verify integrity check passes**

> **Dependency:** Task 3 must be complete — `commands/spec-preflight.md` must exist before `install.sh` integrity check (line 129-136) will pass.

Run: `bash scripts/install.sh --dry-run 2>&1 | grep preflight`
Expected: Output includes a line matching `→ [dry-run] commands/spec.preflight.md → <repo-root>/commands/spec-preflight.md` (where `<repo-root>` is the absolute path to the livespec repo on this machine). No errors from the integrity check.

- [ ] **Step 3: Commit**

```bash
git add scripts/install.sh
git commit -m "feat(preflight): add preflight to install.sh COMMANDS array"
```

---

## Task 5: Update `system/spec-system.md` — project layout

**Files:**
- Modify: `system/spec-system.md:38-82` (Project Layout section)

- [ ] **Step 1: Add preflight files to the `.specs/` layout tree**

In the Project Layout tree diagram (around line 38-82), add `preflight.md` and `preflight-report.md` after `project.md`:

```
.specs/
├── README.md
├── spec-system.md
├── constitution.md
├── project.md
├── preflight.md             ← Preflight manifest (tooling, auth, tokens)
├── preflight-report.md      ← Latest preflight execution report
│
├── commands/
...
```

- [ ] **Step 2: Add preflight to `/spec.init` exit criteria**

In `system/spec-system.md` around line 427, find the "Before `/spec.init` is considered complete:" checklist. Add:

```markdown
- [ ] `preflight.md` exists with checks generated from stack
- [ ] `preflight-report.md` exists with execution results
```

- [ ] **Step 3: Verify consistency**

Read `system/spec-system.md` lines 34-90 (layout tree) and lines 427-435 (init checklist) to confirm both sections include the preflight files.

- [ ] **Step 4: Commit**

```bash
git add system/spec-system.md
git commit -m "feat(preflight): add preflight.md and preflight-report.md to canonical .specs/ layout and init checklist"
```

---

## Task 6: Update `commands/spec-init.md` — Phase D

**Files:**
- Modify: `commands/spec-init.md` (add Phase D after Phase C, update exit criteria)

- [ ] **Step 1: Add Phase D section**

After the Phase C section (around line 339, before the "Installation output" block), add:

```markdown
### Phase D — Preflight Setup

After `.specs/` structure is installed, generate and execute the preflight manifest:

1. **Generate manifest:** Read `.specs/stacks/_default.md`, match stack technologies against the catalog defined in `/spec.preflight`, generate `.specs/preflight.md` using `system/templates/preflight-manifest-template.md` as base structure
2. **Detect `.env` tokens:** If a `.env` file exists at project root, scan for `creds:*` entries and add them as Token checks
3. **Execute full preflight:** Run the 3-pass execution engine (Pass 1: verify all → Pass 2: auto-resolve → Pass 3: human blockers)
4. **Present blockers:** The user is present during init — present all human-required actions (OAuth login, `creds set`) grouped together
5. **Commit:** Add `preflight.md` and `preflight-report.md` to the init commit

If the user declines to resolve blockers during init, the manifest is still committed with the checks marked as failing in the report. They can re-run `/spec.preflight` later.
```

- [ ] **Step 2: Update exit criteria**

In the Exit Criteria section (around line 412-422), add after the CLAUDE.md check:

```markdown
- [ ] `.specs/preflight.md` exists with checks generated from stack
- [ ] `.specs/preflight-report.md` exists with execution results
```

- [ ] **Step 3: Update installation output message**

In the installation output block (around line 341-360), add to the "Created:" list:

```markdown
> - `.specs/preflight.md` — preflight manifest (tooling, auth, tokens)
> - `.specs/preflight-report.md` — preflight execution report
```

- [ ] **Step 4: Update CLAUDE.md commands list**

In `commands/spec-init.md` line 335, replace the commands list with the complete set:

From:
```
Commands: `/spec.init` · `/spec.propose` · `/spec.specify` · `/spec.plan` · `/spec.implement` · `/spec.check` · `/spec.explain` · `/spec.stack` · `/spec.feature`
```

To:
```
Commands: `/spec.init` · `/spec.propose` · `/spec.specify` · `/spec.plan` · `/spec.implement` · `/spec.check` · `/spec.explain` · `/spec.stack` · `/spec.feature` · `/spec.refine` · `/spec.preflight`
```

This adds both `/spec.refine` (which was missing) and `/spec.preflight` (new).

- [ ] **Step 5: Verify init.md is consistent**

Read the updated file to confirm Phase D appears between Phase C and the Installation output, exit criteria includes the two new checks, and the CLAUDE.md template includes `/spec.preflight`.

- [ ] **Step 6: Commit**

```bash
git add commands/spec-init.md
git commit -m "feat(preflight): add Phase D (preflight setup) to /spec.init"
```

---

## Task 7: Update `commands/spec-specify.md` — post-generation hook

**Files:**
- Modify: `commands/spec-specify.md` (add hook after spec generation, before Definition of Done)

- [ ] **Step 1: Add preflight manifest update hook**

After Step 8 (Optionally Create Git Branch), before the Flags section. This becomes **Step 9**. Add:

```markdown
### Step 9 — Preflight Manifest Update

After `spec.md` is generated, check if it contains an "Infrastructure Requirements" section with content:

1. If the section is empty or absent → skip this step
2. If the section has content:
   a. Read `.specs/preflight.md` (if it exists)
   b. Compute which new checks would be needed based on the infrastructure requirements (new CLI tools, new OAuth sessions, new tokens)
   c. Show the proposed additions as a diff:
      ```
      Preflight manifest — 2 checks to add:

        [TOOLING]  redis-cli (verify: redis-cli ping, install: brew install redis)
        [TOKEN]    project/dev/redis_url (verify: creds get ..., resolve: human)

      Add to preflight manifest? (y/n)
      ```
   d. If confirmed → add entries to the appropriate sections in `preflight.md`, commit
   e. If declined → no change. User can run `/spec.preflight --regenerate` later
3. No execution — this step only updates the manifest, it does not run checks
```

- [ ] **Step 2: Verify specify.md structure is consistent**

Read the updated file to confirm the new step fits between existing steps and the Flags section.

- [ ] **Step 3: Commit**

```bash
git add commands/spec-specify.md
git commit -m "feat(preflight): add post-generation hook to /spec.specify for Infrastructure Requirements"
```

---

## Task 8: Update `commands/spec-implement.md` — Phase 0.5

**Files:**
- Modify: `commands/spec-implement.md` (add Phase 0.5 before Phase 1)

- [ ] **Step 1: Add Phase 0.5 section**

After the "Preflight Safety Contract" section (which checks file existence) and before "Phase 2 — Plan Execution" (around line 72), add:

```markdown
### Phase 0.5 — Preflight Check (Light)

After verifying spec/plan files exist (Preflight Safety Contract), run a light preflight check to verify tools and access are ready:

1. If `.specs/preflight.md` does not exist → log warning: "No preflight manifest found. Run `/spec.preflight --regenerate` to create one." and continue to Phase 2
2. Run `/spec.preflight --light` with the current feature name as context
3. Gate behavior:
   - Any `critical` check failed → **STOP**. Write `preflight-report.md` with BLOCKED verdict. Report blocker + recovery command. Do not start implementation.
   - Only `warning` checks failed → write `preflight-report.md` with WARNINGS verdict, display warning, continue to Phase 2
   - All pass → write `preflight-report.md` with READY verdict, continue to Phase 2

This phase ensures tools, OAuth sessions, and API tokens are available before autonomous work begins. It runs AFTER the Preflight Safety Contract (which checks spec/plan file existence) and BEFORE the Infrastructure Gate (Phase 2 Step 0, which checks cloud resource existence).
```

- [ ] **Step 2: Verify the phase ordering makes sense**

Read the updated file to confirm ordering: Preflight Safety Contract (file checks) → Phase 0.5 (preflight tooling check) → Phase 2 (Plan Execution with Step 0 infra gate).

- [ ] **Step 3: Commit**

```bash
git add commands/spec-implement.md
git commit -m "feat(preflight): add Phase 0.5 (light preflight check) to /spec.implement"
```

---

## Task 9: Update `commands/spec-feature.md` — Phase 0.5

**Files:**
- Modify: `commands/spec-feature.md` (add Phase 0.5 before Phase 3 — Implement)

- [ ] **Step 1: Add preflight check before implementation phase**

In the feature pipeline, the preflight check should run just before the implementation phase starts (Phase 3). Find the Phase 3 — Implement section and add before it:

```markdown
### Phase 2.7 — Preflight Check (Light)

Before starting implementation, run a light preflight check:

1. If `.specs/preflight.md` does not exist → log warning and continue
2. Run `/spec.preflight --light` with the current feature name as context
3. Gate behavior:
   - Any `critical` check failed → **STOP**. Write `preflight-report.md` with BLOCKED verdict. Report blocker + recovery command. Update `pipeline.md`: Preflight → `Blocked`
   - Only `warning` checks failed → write `preflight-report.md` with WARNINGS verdict, display warning, continue
   - All pass → write `preflight-report.md` with READY verdict, continue to Phase 3

This ensures all tools and credentials are available before the autonomous implementation phase begins.
```

- [ ] **Step 2: Update pipeline.md template embedded in `commands/spec-feature.md`**

In the `pipeline.md` template embedded inside `commands/spec-feature.md` (around line 53-66), add the Preflight row between Plan Review and Implement:

```markdown
| Phase | Status | Completed At |
|-------|--------|--------------|
| Specify | Pending | — |
| Spec Review | Pending | — |
| Plan | Pending | — |
| Plan Review | Pending | — |
| Preflight | Pending | — |
| Implement | Pending | — |
```

- [ ] **Step 3: Verify feature.md structure**

Read the updated file to confirm the preflight phase appears between Plan Review and Implement.

- [ ] **Step 4: Commit**

```bash
git add commands/spec-feature.md
git commit -m "feat(preflight): add Phase 2.7 (preflight check) to /spec.feature before implementation"
```

---

## Task 10: Update `commands/spec-stack.md` — post-ADR hook

**Files:**
- Modify: `commands/spec-stack.md` (add Step 7 after Step 6)

- [ ] **Step 1: Add preflight manifest regeneration step**

After Step 6 (Generate Migration Specs), before the `/spec.stack decisions` section (around line 239), add:

```markdown
#### Step 7 — Regenerate Preflight Manifest

After creating the ADR and updating `_default.md`:

1. If `.specs/preflight.md` exists:
   a. Run the generator in merge mode: re-read `_default.md`, match against catalog, generate new checks
   b. Preserve Custom section (between `<!-- preflight:custom:start/end -->` markers)
   c. Deduplicate — do not overwrite existing checks
   d. Show diff: "Stack modified. Preflight updated: 2 checks added (vercel CLI, vercel-oauth), 1 check removed (heroku)."
   e. Commit updated `preflight.md`
2. If `.specs/preflight.md` does not exist → skip silently (project may not use preflight yet)
```

- [ ] **Step 2: Update Definition of Done**

In the Definition of Done section (around line 272-283), add:

```markdown
- [ ] `.specs/preflight.md` regenerated with new stack checks (if manifest exists)
```

- [ ] **Step 3: Verify stack.md structure**

Read the updated file to confirm Step 7 appears after Step 6 and before the `decisions` subcommand section.

- [ ] **Step 4: Commit**

```bash
git add commands/spec-stack.md
git commit -m "feat(preflight): add post-ADR preflight manifest regeneration to /spec.stack"
```

---

## Task 11: Final verification

**Files:** All modified files

- [ ] **Step 1: Run install.sh dry-run**

Run: `bash scripts/install.sh --dry-run`
Expected: All 12 commands (including `spec.preflight`) listed, no errors

- [ ] **Step 2: Verify all new/modified files exist**

Run: `ls -la commands/spec-preflight.md system/templates/preflight-manifest-template.md system/templates/preflight-report-template.md`
Expected: All 3 new files exist

- [ ] **Step 3: Verify modified files mention preflight**

Run: `grep -l "preflight" commands/spec-init.md commands/spec-specify.md commands/spec-implement.md commands/spec-feature.md commands/spec-stack.md system/spec-system.md scripts/install.sh`
Expected: All 7 files listed

- [ ] **Step 4: Run install.sh for real**

Run: `bash scripts/install.sh --force`
Expected: All commands and agents installed, including `spec.preflight`

- [ ] **Step 5: Verify symlink**

Run: `ls -la ~/.claude/commands/spec.preflight.md`
Expected: Symlink pointing to `livespec/commands/spec-preflight.md`

- [ ] **Step 6: Commit if any uncommitted changes remain**

```bash
git status
# If changes: git add ... && git commit -m "feat(preflight): final integration verification"
```
