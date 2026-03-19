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

### Rules

- Token values are **never** displayed — only `exists` or `missing`
- The `Custom` section is delimited by an HTML comment and preserved on regeneration
- Entries added manually should use `source: manual`

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
3. **Scan specs** — parse "Infrastructure Requirements" sections from all `spec.md` files for additional needs (external APIs, third-party services)
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
1. Execute the `resolve` / `install` command
2. Re-execute the `verify` command to confirm
3. Final status: `resolved` or `failed`

Sequential to avoid conflicts (e.g., two npm installs racing).

### Pass 3 — Human blockers (grouped)

All checks still `failed` that require human action are presented together:

```
⚠ Preflight — 2 actions required:

  1. [TOKEN] project/dev/cloudflare_api_token
     → Run: echo -n "your-token" | creds set project/dev/cloudflare_api_token

  2. [OAUTH] cloudflare session expired
     → Run: wrangler login

Resolve these, then press Enter to re-verify.
```

After user action, the engine **re-verifies only the resolved items** (not the full manifest).

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
- Items added since the last full run
- Skips items already `pass` at last run (except OAuth)

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
- **Versions captured** in Details (useful for debugging regressions)
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

## Files Created / Modified

### New files
| File | Purpose |
|------|---------|
| `.specs/preflight.md` | Manifest — source of truth for all checks |
| `.specs/preflight-report.md` | Execution report (snapshot, overwritten each run) |
| `commands/spec.preflight.md` | New LiveSpec command definition |

### Modified files
| File | Change |
|------|--------|
| `commands/spec.init.md` | Add Phase D (preflight setup) |
| `commands/spec.specify.md` | Add post-generation hook for Infrastructure Requirements |
| `commands/spec.implement.md` | Add Phase 0.5 (light preflight check) |
| `commands/spec.feature.md` | Add Phase 0.5 (light preflight check) before implementation |
| `commands/spec.stack.md` | Add post-modification hook for manifest regeneration |
| `scripts/install.sh` | Add `spec.preflight` command to symlink list |
| `system/templates/` | Add `preflight-manifest-template.md` and `preflight-report-template.md` |

## Non-Goals

- **Runtime monitoring** — Preflight checks readiness before work starts, not during
- **Secret rotation** — Preflight verifies tokens exist, not that they are valid beyond basic auth checks
- **Dependency version management** — Preflight checks presence, not semver compatibility
- **Network connectivity** — Preflight checks tool/auth readiness, not that APIs are online
