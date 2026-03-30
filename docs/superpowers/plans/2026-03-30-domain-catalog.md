# Domain Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a centralized domain-catalog.md in ai-ressources that maps keyword signals to convention files, replacing the hardcoded mapping in LiveSpec's conventions-sync.md.

**Architecture:** domain-catalog.md lives at ai-ressources root. `/conventions.init` and `/conventions.refresh` read it at runtime. LiveSpec extracts raw signals from .specs/ and passes them — no pre-mapping.

**Tech Stack:** Markdown (no code), ai-ressources knowledge base, LiveSpec hooks system

---

### Task 1: Create domain-catalog.md in ai-ressources

**Files:**
- Create: `/Users/julienm/projects/ai-ressources/domain-catalog.md`

- [ ] **Step 1: Create domain-catalog.md with header and instructions**

Create the file at `/Users/julienm/projects/ai-ressources/domain-catalog.md` with:

```markdown
# Domain Catalog — Signal-to-Convention Mapping

> **This file is the single source of truth for mapping keyword signals to convention files.**
> Read by: `/conventions.init`, `/conventions.refresh`, `/audit`.
> When a consumer provides a list of keyword signals (from a stack file, dependencies, or project context), resolve each signal against the tables below to determine which convention files to include.

## How to Use

1. Receive a flat list of keyword signals (case-insensitive)
2. Match each signal against ALL tables below (a signal can match multiple categories)
3. Collect all matched file paths (union — no deduplication needed, handled downstream)
4. Unknown signals are silently ignored

## How to Maintain

When any `.md` file is created, renamed, or deleted in a domain directory (architecture/, code-conventions/, conventions/, copywriting/, design/, legal/, pricing-models/, seo/, stack-ref/, models/), update this catalog in the same pass.

---
```

- [ ] **Step 2: Add Code Conventions section**

Append to domain-catalog.md:

```markdown
## Code Conventions

**Base conventions (always include when any language is detected):**
- `code-conventions/general.md`
- `code-conventions/architecture.md`
- `code-conventions/logging.md`
- `code-conventions/testing.md`

| Signal | Convention file |
|---|---|
| `typescript`, `ts`, `.ts`, `.tsx`, `javascript`, `js`, `.js`, `.jsx`, `node`, `bun`, `deno` | `code-conventions/javascript.md` |
| `go`, `golang` | `code-conventions/go.md` |
| `rust`, `cargo` | `code-conventions/rust.md` |
| `swift`, `ios`, `macos`, `swiftui`, `uikit` | `code-conventions/swift-kotlin.md` |
| `kotlin`, `android`, `jetpack` | `code-conventions/swift-kotlin.md` |
| `delphi`, `pascal`, `.pas`, `.dfm`, `.dproj` | `code-conventions/delphi.md` |
| `sql`, `postgresql`, `mysql`, `sqlite`, `database`, `migration`, `schema` | `code-conventions/database.md` |

---
```

- [ ] **Step 3: Add Framework Deltas section**

```markdown
## Framework Deltas

| Signal | Convention file |
|---|---|
| `react`, `react-dom`, `.tsx`, `.jsx`, `jsx` | `code-conventions/react.md` |
| `next`, `next.js`, `nextjs`, `next.config` | `code-conventions/nextjs.md` |
| `shadcn`, `shadcn/ui`, `components/ui` | `code-conventions/shadcn.md` |
| `tailwind`, `tailwindcss`, `@tailwindcss`, `tailwind.config` | `code-conventions/tailwind.md` |
| `cloudflare`, `workers`, `hono`, `wrangler`, `wrangler.toml` | `code-conventions/cloudflare.md` |
| `tanstack`, `react-query`, `react-router`, `react-start`, `@tanstack` | `code-conventions/tanstack.md` |
| `drizzle`, `drizzle-orm`, `drizzle-kit`, `drizzle.config` | `code-conventions/drizzle.md` |
| `prisma`, `@prisma/client`, `prisma/schema.prisma` | `code-conventions/prisma.md` |
| `remotion`, `@remotion`, `remotion.config` | `code-conventions/remotion.md` |

---
```

- [ ] **Step 4: Add Architecture Patterns section**

```markdown
## Architecture Patterns

| Signal | Convention file |
|---|---|
| `oauth`, `jwt`, `session`, `auth`, `login`, `authentication`, `sign-in`, `mfa`, `2fa` | `architecture/auth-flows.md` |
| `cron`, `scheduled`, `background`, `worker`, `queue`, `job`, `task-scheduler`, `async-task` | `architecture/background-jobs.md` |
| `cache`, `caching`, `redis`, `memoize`, `ttl`, `lru`, `invalidation`, `cdn` | `architecture/caching-strategies.md` |
| `migration`, `migrate`, `schema-change`, `alter-table`, `versioning`, `expand-contract` | `architecture/database-migrations.md` |
| `event`, `pubsub`, `publish`, `subscribe`, `emit`, `cqrs`, `event-driven`, `event-sourcing`, `message-queue` | `architecture/event-driven.md` |
| `tenant`, `multi-tenant`, `workspace`, `org`, `organization`, `isolation`, `rls`, `row-level-security` | `architecture/multi-tenant.md` |
| `rate-limit`, `rate-limiting`, `throttle`, `429`, `token-bucket`, `sliding-window` | `architecture/rate-limiting.md` |
| `webhook`, `callback`, `idempotency`, `hmac`, `event-delivery`, `retry`, `dlq` | `architecture/webhook-patterns.md` |

---
```

- [ ] **Step 5: Add Stack-Ref section (all 12 subcategories)**

```markdown
## Stack-Ref (External Services & Platforms)

### AI
| Signal | Convention file |
|---|---|
| `openai`, `openrouter`, `gpt`, `claude`, `llm`, `ai-api` | `stack-ref/ai/openrouter.md` |
| `vercel-ai`, `ai-sdk`, `@ai-sdk` | `stack-ref/ai/vercel-ai-sdk.md` |
| `poyo`, `pyo` | `stack-ref/ai/pyo.md` |

### Auth
| Signal | Convention file |
|---|---|
| `better-auth` | `stack-ref/auth/better-auth.md` |
| `clerk`, `@clerk` | `stack-ref/auth/clerk.md` |
| `next-auth`, `authjs`, `auth.js`, `@auth` | `stack-ref/auth/authjs.md` |
| `workos`, `@workos` | `stack-ref/auth/workos.md` |
| `supabase-auth` | `stack-ref/auth/supabase-auth.md` |

### CMS
| Signal | Convention file |
|---|---|
| `notion-cms`, `notion` (as CMS) | `stack-ref/cms/notion-cms.md` |

### Databases
| Signal | Convention file |
|---|---|
| `turso`, `libsql`, `@tursodatabase` | `stack-ref/databases/turso.md` |
| `neon`, `@neondatabase` | `stack-ref/databases/neon.md` |
| `postgresql`, `postgres`, `pg`, `@types/pg` | `stack-ref/databases/postgres.md` |
| `mysql`, `mysql2` | `stack-ref/databases/mysql.md` |
| `sqlite`, `better-sqlite3`, `sql.js` | `stack-ref/databases/sqlite.md` |
| `redis` (self-hosted), `ioredis` | `stack-ref/databases/redis-self-hosted.md` |
| `upstash`, `@upstash/redis` | `stack-ref/databases/upstash-redis.md` |
| `d1`, `cloudflare-d1` | `stack-ref/databases/cloudflare-d1.md` |
| `kv`, `cloudflare-kv` | `stack-ref/databases/cloudflare-kv.md` |
| `convex` | `stack-ref/databases/convex.md` |
| `supabase-db`, `supabase` (database) | `stack-ref/databases/supabase-db.md` |
| `cockroachdb`, `cockroach` | `stack-ref/databases/cockroachdb.md` |
| `planetscale` | `stack-ref/databases/planetscale.md` |

### Email
| Signal | Convention file |
|---|---|
| `resend` | `stack-ref/email/resend.md` |
| `sendgrid`, `@sendgrid` | `stack-ref/email/sendgrid.md` |
| `postmark` | `stack-ref/email/postmark.md` |
| `ses`, `amazon-ses`, `@aws-sdk/client-ses` | `stack-ref/email/amazon-ses.md` |
| `mailgun` | `stack-ref/email/mailgun.md` |
| `brevo` | `stack-ref/email/brevo.md` |
| `ahasend` | `stack-ref/email/ahasend.md` |

### Frontend
| Signal | Convention file |
|---|---|
| `web`, `webapp`, `spa`, `ssr`, `website` | `stack-ref/frontend/web.md` |
| `mobile`, `react-native`, `expo`, `capacitor` | `stack-ref/frontend/mobile.md` |
| `desktop`, `electron`, `tauri` | `stack-ref/frontend/desktop.md` |
| `cli`, `command-line`, `terminal`, `parseArgs`, `commander`, `yargs`, `meow` | `stack-ref/frontend/cli.md` |

### Jobs
| Signal | Convention file |
|---|---|
| `inngest` | `stack-ref/jobs/inngest.md` |
| `trigger.dev`, `triggerdotdev`, `@trigger.dev` | `stack-ref/jobs/triggerdotdev.md` |
| `bullmq`, `bull` | `stack-ref/jobs/bullmq.md` |
| `cloudflare-queues` | `stack-ref/jobs/cloudflare-queues.md` |

### Operations
| Signal | Convention file |
|---|---|
| `notion-crm` | `stack-ref/ops/notion-crm.md` |
| `solo-saas`, `ops-stack` | `stack-ref/ops/solo-saas-ops-stack.md` |

### Payments
| Signal | Convention file |
|---|---|
| `stripe`, `@stripe` | `stack-ref/payments/stripe.md` |
| `lemon-squeezy`, `lemonsqueezy` | `stack-ref/payments/lemon-squeezy.md` |
| `mollie`, `@mollie` | `stack-ref/payments/mollie.md` |
| `paddle`, `@paddle` | `stack-ref/payments/paddle.md` |

### Platforms
| Signal | Convention file |
|---|---|
| `cloudflare` (platform), `workers`, `pages`, `wrangler` | `stack-ref/platforms/cloudflare.md` |
| `vercel`, `@vercel` | `stack-ref/platforms/vercel.md` |
| `firebase`, `firebase-admin`, `@firebase` | `stack-ref/platforms/firebase.md` |
| `fly.io`, `flyio`, `fly.toml` | `stack-ref/platforms/flyio.md` |
| `aws`, `amazon`, `@aws-sdk` | `stack-ref/platforms/aws.md` |
| `gcp`, `google-cloud`, `@google-cloud` | `stack-ref/platforms/gcp.md` |
| `supabase` (platform), `@supabase` | `stack-ref/platforms/supabase.md` |
| `infomaniak` | `stack-ref/platforms/infomaniak.md` |

### Search
| Signal | Convention file |
|---|---|
| `meilisearch` | `stack-ref/search/meilisearch.md` |
| `algolia`, `algoliasearch`, `@algolia` | `stack-ref/search/algolia.md` |
| `orama`, `@orama` | `stack-ref/search/orama.md` |
| `typesense` | `stack-ref/search/typesense.md` |

### Storage
| Signal | Convention file |
|---|---|
| `r2`, `cloudflare-r2` | `stack-ref/storage/cloudflare-r2.md` |
| `backblaze`, `b2`, `backblaze-b2` | `stack-ref/storage/backblaze-b2.md` |
| `gcs`, `google-cloud-storage`, `@google-cloud/storage` | `stack-ref/storage/google-cloud-storage.md` |

---
```

- [ ] **Step 6: Add Design section**

```markdown
## Design

### Design Systems
| Signal | Convention file |
|---|---|
| `web`, `webapp`, `react`, `next`, `vue`, `svelte`, `html` | `design/systems/web-standards.md` |
| `ios`, `macos`, `swift`, `swiftui`, `apple` | `design/systems/apple-hig.md` |
| `android`, `kotlin`, `material`, `jetpack` | `design/systems/material-design.md` |
| `cli`, `terminal`, `command-line`, `tui` | `design/systems/cli-patterns.md` |

### Design Quality
| Signal | Convention file |
|---|---|
| `web`, `webapp`, `accessibility`, `wcag`, `a11y` | `design/quality/accessibility.md` |
| `ui`, `frontend`, `responsive`, `layout` | `design/quality/ui-rules.md` |

### Design Components (include selectively based on feature context)
| Signal | Convention file |
|---|---|
| `form`, `input`, `validation` | `design/components/forms.md` |
| `button`, `cta`, `action` | `design/components/buttons.md` |
| `modal`, `dialog`, `popup`, `overlay` | `design/components/modals.md` |
| `nav`, `navigation`, `sidebar`, `menu`, `breadcrumb` | `design/components/navigation.md` |
| `list`, `table`, `grid`, `collection` | `design/components/lists.md` |
| `toast`, `notification`, `alert`, `snackbar`, `feedback` | `design/components/feedback.md` |
| `chart`, `graph`, `dashboard`, `analytics`, `metrics`, `visualization` | `design/components/data-visualization.md` |
| `log`, `log-viewer`, `audit-trail` | `design/components/log-viewer.md` |
| `payment`, `checkout`, `billing`, `subscription`, `pricing` | `design/components/payment-flows.md` |
| `realtime`, `websocket`, `sse`, `live`, `streaming` | `design/components/realtime-streams.md` |
| `email-template`, `transactional-email` | `design/components/email-templates.md` |

### Design Tokens (include when any UI work is detected)
| Signal | Convention file |
|---|---|
| Any UI signal (web, mobile, desktop) | `design/tokens/spacing.md` + `design/tokens/typography.md` + `design/tokens/colors.md` + `design/tokens/motion.md` |
| Cross-platform (iOS + Android, or web + mobile) | `design/tokens/cross-platform.md` |

### Design References (include selectively)
| Signal | Convention file |
|---|---|
| `webapp`, `app`, `saas` | `design/references/app-views.md` + `design/references/app-ui.md` |
| `landing-page`, `marketing`, `homepage` | `design/references/landing-pages.md` |
| `mockup`, `wireframe`, `pencil`, `figma` | `design/references/mockup-specs.md` |
| `devtools`, `developer-tools` | `design/references/devtools.md` |

---
```

- [ ] **Step 7: Add Copywriting, Conventions, Legal, Pricing, SEO, Models sections**

```markdown
## Copywriting

| Signal | Convention file |
|---|---|
| `landing-page`, `marketing`, `homepage`, `hero`, `cta` | `copywriting/landing-page.md` |
| `email`, `transactional-email`, `newsletter`, `drip`, `sequence` | `copywriting/email-sequences.md` |
| `tagline`, `slogan`, `value-proposition`, `headline` | `copywriting/taglines.md` |

---

## Conventions (Transversal)

| Signal | Convention file |
|---|---|
| `mermaid`, `gherkin`, `diagram`, `flowchart`, `sequence`, `state` | `conventions/diagrams.md` |
| `naming`, `file-name`, `directory`, `kebab-case` | `conventions/naming.md` |
| `convention-conflict`, `override`, `authority` | `conventions/authority.md` |

---

## Legal (French/EU SaaS)

| Signal | Convention file |
|---|---|
| `cgu`, `terms-of-service`, `tos`, `conditions-generales` | `legal/cgu-saas-type.md` |
| `cgv`, `conditions-de-vente` | `legal/cgv-saas.md` |
| `rgpd`, `gdpr`, `data-protection`, `dpo` | `legal/rgpd-obligations.md` |
| `privacy`, `privacy-policy`, `politique-de-confidentialite` | `legal/privacy-policy.md` |
| `cookie`, `cookie-policy`, `cookie-banner`, `consent` | `legal/cookie-policy.md` |
| `mentions-legales`, `legal-notice` | `legal/mentions-legales.md` |
| `merchant-of-record`, `mor`, `reseller` | `legal/merchant-of-record.md` |

---

## Pricing Models

| Signal | Convention file |
|---|---|
| `freemium`, `free-tier`, `free-plan` | `pricing-models/freemium.md` |
| `flat-rate`, `fixed-price`, `monthly` | `pricing-models/flat-rate.md` |
| `per-seat`, `per-user`, `seat-based` | `pricing-models/per-seat.md` |
| `usage-based`, `pay-as-you-go`, `metered`, `consumption` | `pricing-models/usage-based.md` |

---

## SEO

| Signal | Convention file |
|---|---|
| `core-web-vitals`, `cwv`, `lcp`, `fid`, `cls`, `performance` | `seo/core-web-vitals.md` |
| `programmatic-seo`, `auto-generated-pages`, `template-pages` | `seo/programmatic.md` |
| `next-seo`, `nextjs-seo`, `sitemap`, `robots`, `metadata` | `seo/technical-nextjs.md` |

---

## AI Models (Reference)

| Signal | Convention file |
|---|---|
| `image-generation`, `dall-e`, `stable-diffusion`, `midjourney` | `models/image.md` |
| `video-generation`, `sora`, `runway`, `kling` | `models/video.md` |
| `chat-model`, `llm-model`, `model-selection` | `models/chat.md` |
| `music-generation`, `audio-generation` | `models/music.md` |
```

- [ ] **Step 8: Run index update and build**

```bash
cd /Users/julienm/projects/ai-ressources && bun run scripts/build-index.ts && date +%Y-%m-%d > .last-updated
```

---

### Task 2: Add auto-sync rule to ai-ressources

**Files:**
- Create: `/Users/julienm/projects/ai-ressources/.claude/rules/domain-catalog-sync.md`

- [ ] **Step 1: Create the rule file**

```markdown
# Domain Catalog Sync

After any `.md` file is **created, renamed, or deleted** in a domain directory, verify that `domain-catalog.md` at the project root reflects the change.

## Affected directories

- `architecture/`
- `code-conventions/`
- `conventions/`
- `copywriting/`
- `design/` (all subdirectories)
- `legal/`
- `models/`
- `pricing-models/`
- `seo/`
- `stack-ref/` (all subdirectories)

## What to check

| Event | Action on domain-catalog.md |
|-------|----------------------------|
| File created | Add signal entries mapping relevant keywords to the new file path |
| File deleted | Remove all entries referencing the deleted file path |
| File renamed | Update file paths in all entries referencing the old name |

## Rules

- Update `domain-catalog.md` in the **same pass** as the file operation and the `index.yaml` update
- Choose signal keywords that a consumer would naturally extract from a stack file, dependency list, or project description
- A new file should have at least 2-3 signal keywords
- Do NOT add signals that are too generic (e.g., `app`, `code`) unless they map to a specific convention
```

---

### Task 3: Update /conventions.init to read domain-catalog.md

**Files:**
- Modify: `/Users/julienm/projects/ai-ressources/claude/skills/conventions.init/SKILL.md`

- [ ] **Step 1: Add catalog reading instruction to Phase 2**

In the SKILL.md file, find Phase 2 (Domain Detection) and add at the very beginning, before Channel 1:

```markdown
### Catalog-Based Detection (Primary when signals provided)

If the caller provides a list of keyword signals (e.g., from a LiveSpec stack file):

1. **Read** [`~/projects/ai-ressources/domain-catalog.md`](~/projects/ai-ressources/domain-catalog.md)
2. Match each provided signal against all tables in the catalog
3. Collect all matched convention file paths
4. Use these as the **primary** detected domains — they take precedence over file scanning and code grepping
5. Still run Channels 1-3 for any additional signals not covered by the caller's list, but do NOT override catalog results

If no signals are provided by the caller, proceed with Channels 1-3 as before (backward compatible).
```

- [ ] **Step 2: Update the spec-aware detection section**

Find the existing spec-aware detection section and update it to reference the catalog:

```markdown
### Spec-Aware Detection (Updated)

If `.specs/stacks/_default.md` exists:

1. Read the stack file and extract all technology names, dependency names, and keywords as a flat signal list
2. Resolve these signals through `domain-catalog.md` (same as catalog-based detection above)
3. Merge results with Channel 1-3 detections (union)

This replaces the previous hardcoded mapping table for spec-aware detection.
```

---

### Task 4: Simplify conventions-sync.md (LiveSpec)

**Files:**
- Modify: `/Users/julienm/.claude/livespec/references/conventions-sync.md`

- [ ] **Step 1: Replace Stack-First Detection section**

Remove everything from `## Stack-First Detection` to the end of the file. Replace with:

```markdown
## Stack-First Detection

**Critical:** When this algorithm triggers `/conventions.init` or `/conventions.refresh`, the stack defined in `.specs/stacks/_default.md` is the **primary and authoritative source** for domain detection.

### Signal Extraction Procedure

Before invoking `/conventions.init` or `/conventions.refresh --full`:

1. **Read** `.specs/stacks/_default.md` fully
2. **Read** `.specs/project.md` if it exists
3. **Extract a flat list of keyword signals** from both files:
   - Technology names (e.g., `typescript`, `bun`, `react`, `cloudflare`)
   - Dependency names (e.g., `cron-parser`, `stripe`, `drizzle-orm`)
   - Architecture keywords (e.g., `cron`, `queue`, `webhook`, `multi-tenant`)
   - Project type keywords (e.g., `cli`, `webapp`, `dashboard`, `landing-page`)
   - Platform keywords (e.g., `vercel`, `aws`, `supabase`)
   - Any other relevant technology or pattern keywords
4. Pass the signal list to the skill with the instruction:
   > "Keyword signals extracted from `.specs/stacks/_default.md`: {signal list}.
   > Resolve these signals using `domain-catalog.md` in ai-ressources.
   > The stack file is authoritative — do NOT rely on repo file scanning for domain detection."

### Example

For a project with `.specs/stacks/_default.md` containing Bun + TypeScript + cron-parser + parseArgs:

**Extracted signals:** `typescript, bun, cron-parser, parseArgs, cli`

The `/conventions.init` skill reads `domain-catalog.md` and resolves:
- `typescript` → `code-conventions/javascript.md` + base conventions
- `bun` → `code-conventions/javascript.md` (already included)
- `cron-parser` → `architecture/background-jobs.md`
- `parseArgs` → `stack-ref/frontend/cli.md`
- `cli` → `design/systems/cli-patterns.md` + `stack-ref/frontend/cli.md`

---

## Notes

- The signal-to-domain mapping lives in `~/projects/ai-ressources/domain-catalog.md` — NOT in this file
- `/conventions.init` reads the catalog at runtime for resolution
- When ai-ressources adds new convention files, the catalog is updated there — no change needed here
- `/conventions.refresh --full` uses the same catalog-based detection
- `/conventions.refresh` (without `--full`) refreshes within existing domains only — no catalog needed
```

---

### Task 5: Update /spec.refresh-conventions command

**Files:**
- Modify: `/Users/julienm/projects/livespec/commands/refresh-conventions.md`

- [ ] **Step 1: Update Step 2 to be signal extraction only**

Find `### Step 2 — Read Stack (Primary Source)` and replace with:

```markdown
### Step 2 — Extract Signals from Stack

**Read** `.specs/stacks/_default.md` fully. **Read** `.specs/project.md` if it exists.

Extract a flat list of keyword signals: technology names, dependency names, architecture keywords, project type keywords, platform keywords. These are **raw signals** — do not attempt to map them to convention domains yourself.

Example: for a Bun + TypeScript + cron-parser project → `typescript, bun, cron-parser, parseArgs, cli`
```

- [ ] **Step 2: Update Step 3 to pass signals**

Find `### Step 3 — Run Conventions Sync` and replace with:

```markdown
### Step 3 — Run Conventions Sync

**Read** [`~/.claude/livespec/references/conventions-sync.md`](~/.claude/livespec/references/conventions-sync.md) and follow its algorithm. When invoking `/conventions.init` or `/conventions.refresh`, pass the extracted signals from Step 2 so the skill can resolve them via `domain-catalog.md`.
```
