# Preflight System — Design Specification

> **Status:** Approved
> **Date:** 2026-03-19
> **Scope:** LiveSpec core — new `/spec.preflight` command + integration in existing commands

## Problem

LiveSpec's current verification mechanisms (Test Discovery, Infrastructure Gate, Preflight Check) all run **at implementation time** — when the user may no longer be present to provide credentials, authenticate via browser OAuth flows, or unblock missing tooling.

This creates a failure mode where autonomous implementation is blocked late in the process by missing tools, expired sessions, or absent API tokens — exactly the scenario LiveSpec's autonomous pipeline is designed to avoid.

## Solution

A **Preflight System** that verifies all tooling, authentication, and credentials are in place **before the user leaves**, enabling fully autonomous implementation afterward.

The system consists of three components:

1. **Generator** — Infers required checks from the project stack and feature specs
2. **Manifest** — A structured, editable, versioned file (`.specs/preflight.md`)
3. **Execution Engine** — Reads the manifest, runs checks, auto-resolves what it can, and reports blockers

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Timing | Full setup post-init + light check pre-implementation | Full setup while user is present; light check catches expired sessions and feature-specific delta |
| Autonomy | Auto-resolve max, human only for OAuth/creds | Minimize friction — only interrupt for actions that require human presence |
| Check source | Hybrid (inference + manual overrides) | Inference covers 90% automatically; manual overrides catch edge cases |
| Report | Inline terminal + persisted file | Immediate feedback + traceability |
| Blocker handling | Grouped by type (auto first, human second) | Efficient UX — user sees all required actions at once |
| Gate behavior | Blocking by severity (critical blocks, warning informs) | Missing API token = hard stop; missing formatter = acceptable |
| Integration | Standalone command + integrated phase | Diagnostic on demand + automatic in workflow |

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Preflight System                │
│                                                  │
│  ┌──────────────┐  ┌───────────┐  ┌───────────┐ │
│  │  Generator   │  │ Manifest  │  │ Execution │ │
│  │  (inference) │─▶│ preflight │─▶│  Engine   │ │
│  │              │  │   .md     │  │           │ │
│  └──────────────┘  └───────────┘  └───────────┘ │
│        ▲                ▲              │         │
│        │                │              ▼         │
│   stack + specs    manual edits   report.md      │
│                                  + inline output │
└─────────────────────────────────────────────────┘
```

## Component 1 — Manifest Format (`.specs/preflight.md`)

The manifest is the source of truth for all checks. It is auto-generated, editable, and versioned in git.

### Structure

```markdown
# Preflight Manifest

> Auto-generated from stack and specs. Editable — changes are preserved on regeneration.

## Tooling

### <check-name>
- **binary:** `<binary-name>`
- **verify:** `<command to check presence/version>`
- **install:** `<command to install>`
- **severity:** critical | warning
- **source:** stack (_default.md) | spec (NNN-feature-name) | manual

## Authentication

### <check-name>
- **type:** oauth
- **verify:** `<command to check session>`
- **resolve:** `<command to re-authenticate>`
- **severity:** critical | warning
- **expires:** true
- **source:** stack (_default.md) | spec (NNN-feature-name) | manual

## Tokens

### <check-name>
- **type:** creds
- **entry:** `<creds entry path>`
- **verify:** `creds get <entry> > /dev/null 2>&1`
- **resolve:** human
- **severity:** critical | warning
- **source:** stack (_default.md) | spec (NNN-feature-name) | manual

## Custom

<!-- Add manual checks here — preserved on regeneration -->
```

### Field definitions

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

### Rules

- Token values are **never** displayed — only `exists` or `missing`
- Entries added manually should use `source: manual`
- Default timeout for `verify` commands: **10 seconds**. Override per check with an optional `timeout` field (in seconds)

### Custom section merge algorithm

The `Custom` section is delimited by two markers:
```markdown
## Custom

<!-- preflight:custom:start -->
...user entries...
<!-- preflight:custom:end -->
```

**Regeneration behavior:**
1. Parse the file and locate the `<!-- preflight:custom:start -->` and `<!-- preflight:custom:end -->` markers
2. Extract the content between markers verbatim
3. Regenerate all sections above Custom from stack + specs
4. Re-insert the Custom content between markers unchanged
5. If markers are missing or malformed → **abort regeneration**, warn user: "Custom section markers corrupted. Run `/spec.preflight --regenerate --force` to reset, or fix markers manually."
6. If a Custom entry has the same `### <check-name>` as a generated entry → **keep both**, append `(custom)` suffix to the Custom entry name, and warn: "Duplicate check `<name>` found in Custom — renamed to `<name> (custom)`. Review and merge manually."

## Component 2 — Generator (Inference Engine)

The generator produces and updates `preflight.md` from the project stack and feature specs.

### Stack-to-checks catalog

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

### Generation rules

1. **Parse `_default.md`** — extract the stack (framework, deploy, DB, auth, testing, etc.)
2. **Match catalog** — each recognized technology generates its checks
3. **Scan specs** — parse "Infrastructure Requirements" sections from all `spec.md` files for additional needs (external APIs, third-party services). If no feature specs exist yet (fresh init), only stack-level checks are generated from `_default.md`
4. **Detect tokens** — if a `.env` file exists at project root, each `creds:*` entry becomes a Token check
5. **Deduplicate** — if a check already exists (manually added or from previous run), do not overwrite
6. **Preserve Custom** — everything in the `Custom` section is untouched

### When the generator runs

| Event | Action |
|-------|--------|
| `/spec.init` Phase D | Full generation from stack |
| `/spec.specify` | If "Infrastructure Requirements" detected → propose additions (diff shown, confirmation asked) |
| `/spec.stack` | If stack changes (new ADR) → regeneration with merge |
| `/spec.preflight --regenerate` | Force regeneration (preserves Custom) |

## Component 3 — Execution Engine

The engine reads `preflight.md` and proceeds in **3 passes**.

### Pass 1 — Verification (parallel)

Execute all `verify` commands in parallel. Each check receives a status:
- `pass` — command exited 0
- `fail` — command exited non-zero
- `error` — command timed out or could not be executed

### Pass 2 — Auto-resolution (sequential)

For each `fail` check where `resolve` is not `human`:
0. If check has `source: manual`, prompt user for confirmation before executing. If declined, mark as `failed` and escalate to Pass 3
1. Execute the `resolve` / `install` command
2. Re-execute the `verify` command to confirm
3. Final status: `resolved` or `failed`

Sequential to avoid conflicts (e.g., two npm installs racing).

**Partial failure handling:** All `install`/`resolve` commands must be idempotent — re-running a failed install should not corrupt state. If an auto-resolution command fails (non-zero exit), the check is marked `failed` and escalated to Pass 3 as a human blocker with the error output. The engine does not attempt rollback — package managers (npm, brew, etc.) handle partial states on re-run. If `source: manual`, the engine prompts for confirmation before executing the resolve command.

### Pass 3 — Human blockers (grouped)

All checks still `failed` that require human action are presented together:

```
⚠ Preflight — 2 actions required:

  1. [TOKEN] project/dev/cloudflare_api_token
     → Run: echo -n "your-token" | creds set project/dev/cloudflare_api_token

  2. [OAUTH] cloudflare session expired
     → Run: wrangler login

Resolve these, then press Enter to re-verify (or type 'skip' to continue — critical failures will still block).
```

After user action, the engine **runs a full Pass 1 + Pass 2 cycle** (not just the resolved items). This catches cascading dependencies — e.g., resolving an OAuth session may unblock a token check that depends on it. If new failures are detected, they enter Pass 3 again. The loop terminates when all checks pass or the user explicitly aborts.

### Inline output (final)

```
✓ Preflight Complete (12 checks)

  Tooling         wrangler ✓  vitest ✓  playwright ✓
  Authentication  cloudflare ✓  github ✓
  Tokens          cf_api_token ✓  supabase_key ✓
  Custom          redis-local ✓

  ⏱ 4.2s | 10 passed, 2 auto-resolved, 0 blocked
```

### Light check behavior (pre-implementation)

The light check only verifies a subset of the manifest:
- Items with `expires: true` (OAuth sessions)
- Items whose `source` references the current feature
- Items added since the last full run (determined by diffing the manifest's check names against the Details tables in `preflight-report.md` — if a check exists in the manifest but not in the report's Details tables, it is new)
- Skips items already `pass` at last run (except OAuth)

If `preflight.md` does not exist (e.g., project initialized before the Preflight System was added), the light check logs a warning: "No preflight manifest found. Run `/spec.preflight --regenerate` to create one." and **continues** without blocking — the existing Infrastructure Gate (Phase 0) still provides its own checks.

### Inline output for WARNINGS verdict

When only `warning`-severity checks fail:
```
⚠ Preflight Complete with warnings (12 checks)

  Tooling         wrangler ✓  vitest ✓  playwright ✓
  Authentication  cloudflare ✓  github ✓
  Tokens          cf_api_token ✓  supabase_key ✓
  Custom          redis-local ✓

  Warnings:
    eslint — not installed (warning, non-blocking)

  ⏱ 3.8s | 11 passed, 0 auto-resolved, 0 blocked, 1 warning
```

### Gate behavior

| Condition | Result |
|-----------|--------|
| Any `critical` check `failed` | **BLOCKS** implementation — cannot proceed |
| Only `warning` checks `failed` | Displays warning, **continues** |
| All checks `pass` or `resolved` | **READY** — proceeds normally |

## Component 4 — Persisted Report (`.specs/preflight-report.md`)

Each execution produces a report file — overwritten on each run (history is in git).

### Structure

```markdown
# Preflight Report

> Generated: <ISO-8601> | Mode: full | light | Duration: <seconds>

## Summary

| Category | Total | Pass | Auto-resolved | Failed | Blocked |
|----------|-------|------|---------------|--------|---------|
| Tooling | N | N | N | N | N |
| Authentication | N | N | N | N | N |
| Tokens | N | N | N | N | N |
| Custom | N | N | N | N | N |
| **Total** | **N** | **N** | **N** | **N** | **N** |

## Verdict: READY | BLOCKED | WARNINGS

### Auto-resolved
- **<check>** — <action taken> ✓

### Blocked (human action required)
- **<check>** — <reason>, needs `<command>`

## Details

### <Category>
| Check | Status | Command | Duration |
|-------|--------|---------|----------|
| <name> | ✓ pass | `<cmd>` → <output> | <time> |
```

### Rules

- **Verdict** at the top: `READY`, `BLOCKED`, or `WARNINGS`
- **Versions captured** in Details for commands that produce meaningful stdout (e.g., `--version`). For token/auth checks that produce no useful stdout, only exit code and duration are recorded
- Token values are **never** displayed — only `exists` or `missing`
- Run mode (`full` or `light`) is recorded

## Integration in Existing Commands

### `/spec.init` — new Phase D

After Phase C (`.specs/` structure installation):

1. Generator: stack → `preflight.md`
2. Detect `.env` at root → add token checks
3. Execute in full mode
4. Auto-resolve
5. Present human blockers (user is still present)
6. Commit `preflight.md` + `preflight-report.md`

### `/spec.specify` — post-generation hook

After `spec.md` generation:

- If "Infrastructure Requirements" section is non-empty:
  - Compute diff against current `preflight.md`
  - Show proposed additions
  - Ask for confirmation
  - If confirmed: add entries + commit `preflight.md`
  - If declined: no change to `preflight.md`. The user can run `/spec.preflight --regenerate` later to incorporate
- No execution — manifest update only

### `/spec.implement` and `/spec.feature` — new Phase 0.5

Before the existing Infrastructure Gate (Phase 0):

1. Read `preflight.md`
2. Run light check (expires + feature source + new items)
3. Auto-resolve if possible
4. If any critical failed → **STOP** + request human action
5. If all green → write `preflight-report.md` + continue to Phase 0

The preflight check and infrastructure gate remain **distinct**:
- Preflight = "are tools and access in place?"
- Infra gate = "do cloud resources exist?" (KV namespaces, D1 databases, etc.)

### `/spec.stack` — post-modification hook

After creating an ADR that modifies the stack:

- Regenerate `preflight.md` (merge mode, preserves Custom)
- Inform user of changes ("Stack modified. Preflight updated, 2 checks added.")

### `/spec.preflight` — standalone command

```
/spec.preflight              → full execution
/spec.preflight --light      → light check (expires + delta)
/spec.preflight --regenerate → regenerate manifest from stack + specs
/spec.preflight --dry-run    → show what would be checked, without executing
```

**`--dry-run` output:**
```
Preflight dry run — 12 checks would be executed:

  Tooling (5):        wrangler, vitest, node, playwright, eslint
  Authentication (3): cloudflare-oauth, github-cli, supabase
  Tokens (3):         cf_api_token, supabase_key, stripe_key
  Custom (1):         redis-local

  Critical: 8 | Warning: 4
```

## Files Created / Modified

### New files
| File | Purpose |
|------|---------|
| `.specs/preflight.md` | Manifest — source of truth for all checks |
| `.specs/preflight-report.md` | Execution report (snapshot, overwritten each run) |
| `commands/preflight.md` | New LiveSpec command definition (`spec.` prefix added by `install.sh` at symlink time) |

### Modified files
| File | Change |
|------|--------|
| `commands/spec.init.md` | Add Phase D (preflight setup) |
| `commands/spec.specify.md` | Add post-generation hook for Infrastructure Requirements |
| `commands/spec.implement.md` | Add Phase 0.5 (light preflight check) |
| `commands/spec.feature.md` | Add Phase 0.5 (light preflight check) before implementation |
| `commands/spec.stack.md` | Add post-modification hook for manifest regeneration |
| `scripts/install.sh` | Add `preflight` to COMMANDS array (script adds `spec.` prefix automatically) — `commands/preflight.md` must exist first |
| `system/spec-system.md` | Add `preflight.md` and `preflight-report.md` to the canonical `.specs/` layout section; add preflight check to `/spec.init` exit criteria checklist |
| `system/` | Add `preflight-manifest-template.md` and `preflight-report-template.md` (flat, alongside existing templates) |

## Security

The manifest is a versioned, committed file — it has the same trust level as a `Makefile` or `package.json` script. Commands in `install`/`resolve` fields are executed by the engine with the user's permissions.

**Mitigations:**
- Auto-generated entries (from the catalog) use only well-known package manager commands
- Entries with `source: manual` require **user confirmation** before auto-resolution (Pass 2 prompts before executing)
- The manifest is in git — any malicious modification is visible in diffs
- Token values are never read, stored, or displayed by the engine — only existence is checked via `creds get ... > /dev/null`

## Changelog Policy

Preflight manifest updates (`preflight.md`) are **infrastructure-level artifacts** — they do not generate entries in feature changelogs or the global `.specs/changelog.md`. This is analogous to how `testing/strategy.md` updates during test discovery do not generate changelog entries. The preflight report (`preflight-report.md`) is ephemeral by design (overwritten each run) and is likewise exempt.

## Non-Goals

- **Runtime monitoring** — Preflight checks readiness before work starts, not during
- **Secret rotation** — Preflight verifies tokens exist, not that they are valid beyond basic auth checks
- **Dependency version management** — Preflight checks presence, not semver compatibility
- **Network connectivity** — Preflight checks tool/auth readiness, not that APIs are online
