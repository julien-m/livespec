---
description: "Initialize LiveSpec in a project through a 3-phase conversational brainstorm"
---

# Command: /spec.init

> Initialize LiveSpec in a project through a 3-phase conversational brainstorm.
> This is NOT a simple file copier. It interviews the user, decides the stack, and generates a tailored project setup.

---

## Overview

`/spec.init` runs a 3-phase process:

1. **Phase A — Brainstorm:** Conversational interview to understand the project
2. **Phase B — Stack Decisions:** AI-guided infrastructure decisions with visual decision trees
3. **Phase C — Installation:** Automatic creation of the `.specs/` directory structure

---

## Phase A — Brainstorm (Conversational)

The AI asks questions one at a time, waits for answers, and builds a PROJECT PROFILE.

### Conversation Flow

**Opening:**

> 👋 Let's set up LiveSpec for your project. I'll ask you a few questions to understand what you're building — then I'll recommend a stack and generate your spec system. This takes about 5 minutes.
>
> **Question 1/6: What are you building?**
> Describe it like you're explaining to a friend with no technical background.

---

*User answers, e.g.: "A platform where freelancers can find clients and manage projects, kind of like Upwork but focused on designers."*

---

> Got it — a freelancer marketplace for designers.
>
> **Question 2/6: WHO uses it?**
> What are the different types of people (roles) in your system, and what level of access does each have?
> Example: "Designers post portfolios (full access), Clients browse and hire (limited access), Admins manage disputes (admin access)"

---

*User answers: "Designers can create profiles and bid on jobs. Clients can post jobs and hire. Admins can manage disputes and ban users."*

---

> Got it. I see 3 roles:
> - **Designer** — create profiles, browse jobs, bid, manage contracts
> - **Client** — post jobs, review bids, hire, pay
> - **Admin** — moderation, disputes, user management
>
> **Question 3/6: WHERE do they use it?**
> Desktop browser? Mobile browser? Native iOS/Android app? On the go or at a desk?

---

*User answers: "Mostly desktop for clients posting jobs. Designers use both desktop and mobile."*

---

> Good — primarily web, but mobile-responsive is important for designers.
>
> **Question 4/6: WHAT needs to be fast (real-time)?**
> Which features need data to update instantly without the user refreshing?
> Think about: messaging, notifications, live status updates, collaborative editing, etc.

---

*User answers: "Messaging between clients and designers should be real-time. Notifications when a new bid comes in."*

---

> Real-time messaging and notifications — noted. Those drive infrastructure choices.
>
> **Question 5/6: WHERE are your users geographically?**
> Single country? Europe only? Global?
> This impacts where we deploy your infrastructure.

---

*User answers: "Initially US and Europe. Global within 2 years."*

---

> Multi-region from the start then. This means we'll want edge-capable infrastructure.
>
> **Question 6/6: What's your budget and scale expectation?**
> Rough estimate: how many users in year 1? Year 3? What's your infra budget (e.g., < $100/month, $500/month, flexible)?

---

*User answers: "Maybe 1,000 users year 1, 50,000 by year 3. Budget is flexible but ideally under $500/month to start."*

---

### Project Profile Summary

After the 6 questions, the AI presents a summary and asks for confirmation:

> 📋 **PROJECT PROFILE — [Project Name]**
>
> **What it is:** Freelancer marketplace for designers — Upwork-style platform focused on the design industry.
>
> **Users:**
> | Role | Access | Key Needs |
> |---|---|---|
> | Designer | Full (own data) | Mobile-friendly, fast bidding, real-time messages |
> | Client | Standard | Easy job posting, responsive bids, secure payments |
> | Admin | Full admin | Moderation tools, audit logs |
>
> **Scale:** 1,000 → 50,000 users over 3 years
> **Geography:** US + Europe initially, global by year 3
> **Budget:** < $500/month initial infra
>
> **Real-time needs:**
> - Messaging (< 500ms latency)
> - Notifications (< 2s latency)
>
> **Platforms:** Web (desktop primary, mobile-responsive)
>
> Does this look right? Type **yes** to continue to stack decisions, or tell me what to change.

---

## Phase B — Stack Decisions (AI-Guided)

Based on the project profile, the AI runs the infrastructure decision tree and recommends a stack.

### Step 1 — Run the Decision Tree

> Based on your project profile, here's how I'm reasoning about your stack:

```mermaid
flowchart TD
    A[Designer Marketplace] --> B{Real-time features?}
    B -- Yes: messaging + notifications --> C[WebSocket needed]
    C --> D{Geographic spread?}
    D -- US + Europe + Global --> E[Edge deployment]
    E --> F{Data model?}
    F -- Relational: users, jobs, bids, contracts --> G[PostgreSQL]
    G --> H{Auth complexity?}
    H -- Multi-role + social login --> I[Supabase Auth + RLS]
    I --> J[Recommended: Supabase + Next.js on Vercel]
```

### Step 2 — Present Recommended Stack

> Based on your needs, I recommend the **Web Real-Time** stack preset:
>
> | Layer | Choice | Why For Your Project |
> |---|---|---|
> | Framework | Next.js 14 (App Router) | Best for multi-role apps, SSR for SEO on job listings |
> | Deploy | Vercel Edge | Global edge network covers US + Europe + growing regions |
> | Database | Supabase PostgreSQL | Row-Level Security is perfect for multi-role data isolation |
> | Real-time | Supabase Realtime | WebSocket messaging + notifications built in |
> | Cache | Upstash Redis | Session management, rate limiting bids |
> | Auth | Supabase Auth | Social login (Google, LinkedIn) + multi-role with RLS |
> | Testing | Vitest + Playwright | Full coverage for marketplace flows |
>
> Would you like to use this stack, or adjust anything?
> Examples: "I prefer Firebase over Supabase" / "We already have an AWS account" / "Can we use Prisma instead of Supabase?"

---

*User might say: "Looks good, but we want to use Stripe for payments."*

---

> Good call. Adding Stripe to the stack:
> - **Payments:** Stripe (Connect for marketplace payouts to designers)
> - I'll create an ADR documenting this choice.
>
> Updated stack confirmed. Proceeding.

### Step 3 — Testing Strategy

> For a marketplace with real-time features, here's your testing strategy:
>
> | Feature Type | Test Types | Tools |
> |---|---|---|
> | Business logic (bidding, pricing) | Unit | Vitest |
> | API endpoints | Integration | Vitest + supertest |
> | Messaging | E2E + WebSocket | Playwright |
> | Notifications | E2E + visual | Playwright |
> | Job listing pages | E2E + visual regression | Playwright |
> | Payment flows | E2E (Stripe test mode) | Playwright |
>
> Visual tests will capture baselines for all key screens (job listing, profile, messaging).
> Threshold: 2% diff = FAIL.

### Step 4 — Architecture Decision Records (MANDATORY)

> **At least 1 ADR is REQUIRED before proceeding to Phase C.**
> Every significant stack choice (framework, database, auth, deploy) must have a corresponding ADR.
> An ADR documents WHAT was chosen, WHAT alternatives were considered, and WHY.
> Without ADRs, future developers (and AI tools) cannot understand the reasoning behind the stack.

> I'll create ADRs for the key choices:
> - ADR-001: Supabase over Firebase (reasons: PostgreSQL, RLS, built-in realtime)
> - ADR-002: Next.js over Remix (reasons: larger ecosystem, Vercel integration)
> - ADR-003: Stripe Connect for marketplace payments (reasons: built-in split payments)

ADR files are written to `.specs/stacks/decisions/ADR-NNN-short-name.md` with this structure:

```markdown
# ADR-NNN: [Choice] over [Alternative]

- **Date:** YYYY-MM-DD
- **Status:** Accepted
- **Context:** [What problem are we solving?]
- **Decision:** [What did we choose?]
- **Alternatives considered:** [What else was evaluated?]
- **Consequences:** [What are the trade-offs?]
```

---

## Phase C — Installation (Automatic)

After confirmation, the AI creates the `.specs/` directory structure:

```
.specs/
├── README.md               ← Spec registry and artifact index
├── spec-system.md          ← Copied from livespec system/spec-system.md
├── constitution.md         ← Generated from conversation
├── project.md              ← Generated from Phase A brainstorm
│
├── stacks/
│   ├── _default.md         ← Generated from Phase B decisions
│   └── decisions/
│       ├── ADR-001-supabase-over-firebase.md
│       ├── ADR-002-nextjs-over-remix.md
│       └── ADR-003-stripe-connect.md
│
├── testing/
│   └── strategy.md         ← Generated from Phase B testing decisions
│
├── features/               ← Empty, ready for /spec.specify
│
└── changelog.md            ← Global changelog (initial entry)
```

### Step 3.10 — Create README.md

Create `.specs/README.md` as the centralized spec registry and artifact index.

**Template:**

```markdown
# .specs — [Project Name]

> Specification registry for [Project Name]. All artifacts produced by LiveSpec are indexed here.
>
> Last updated: YYYY-MM-DD

---

## System Files

| Document | Description |
|---|---|
| [spec-system.md](spec-system.md) | Universal spec rules (read first) |
| [constitution.md](constitution.md) | Architecture principles |
| [project.md](project.md) | Project profile (vision, users, constraints) |
| [stacks/_default.md](stacks/_default.md) | Current tech stack |
| [testing/strategy.md](testing/strategy.md) | Testing strategy |
| [changelog.md](changelog.md) | Global changelog |

---

## Features

<!-- readme:features:start -->
| # | Feature | Status | Created | Updated | Spec |
|---|---|---|---|---|---|
<!-- readme:features:end -->

> No features yet. Create your first with `/spec.specify "feature description"`.

---

## Architecture Decisions

<!-- readme:decisions:start -->
| ADR | Decision | Date | Status |
|---|---|---|---|
<!-- readme:decisions:end -->

---

## Recent Activity

> Latest entries from [changelog.md](changelog.md).

<!-- readme:activity:start -->
| Date | Type | Description |
|---|---|---|
| YYYY-MM-DD | Setup | LiveSpec initialized |
<!-- readme:activity:end -->

---

*Maintained automatically by LiveSpec commands. Do not remove section markers.*
```

**Fill instructions:**
- Replace `[Project Name]` with the project name from Phase A brainstorm
- Replace `YYYY-MM-DD` with today's date
- Populate the Architecture Decisions table with all ADRs created in Phase B Step 4 (one row per ADR, Status: Active)
- The Features table starts empty (only header row between markers)

### Step 3.11 — Install LiveSpec section in CLAUDE.md

After creating the `.specs/` structure, install the LiveSpec section in the project's `CLAUDE.md`:

1. **If `CLAUDE.md` does not exist** → create it with the LiveSpec section
2. **If `CLAUDE.md` exists but does NOT contain `<!-- livespec:start -->`** → append the LiveSpec section at the end
3. **If `CLAUDE.md` exists and contains `<!-- livespec:start -->`** → replace everything between `<!-- livespec:start -->` and `<!-- livespec:end -->` markers (idempotent update)

The section content is minimal — a boot pointer to `spec-system.md` plus the command list:

```markdown
<!-- livespec:start -->
## LiveSpec

This project uses [LiveSpec](https://github.com/julien-m/livespec). **Read `.specs/spec-system.md` before any spec command or code modification.**

Commands: `/spec.init` · `/spec.specify` · `/spec.plan` · `/spec.implement` · `/spec.check` · `/spec.explain` · `/spec.stack` · `/spec.feature`
<!-- livespec:end -->
```

This keeps the CLAUDE.md lean. All rules, intent classification, and guardrails are in `.specs/spec-system.md`.

**Installation output:**

> ✅ **LiveSpec installed successfully!**
>
> Created:
> - `.specs/spec-system.md` — the rules (AI reads this first, always)
> - `.specs/constitution.md` — architecture principles for this project
> - `.specs/project.md` — your project profile
> - `.specs/stacks/_default.md` — your recommended stack
> - `.specs/stacks/decisions/` — 3 Architecture Decision Records
> - `.specs/testing/strategy.md` — your testing strategy
> - `.specs/features/` — ready for your first feature spec
> - `.specs/README.md` — spec registry and artifact index
> - `.specs/changelog.md` — global changelog
>
> **Next step:** Create your first feature spec with:
> ```
> /spec.specify "User can post a job listing"
> ```

---

## Flags

| Flag | Behavior |
|---|---|
| `--auto` | Use defaults, skip all questions (generates generic constitution) |
| `--stack [preset]` | Skip Phase A, use specified preset (web-realtime / web-static / api-rest) |
| `--dir [path]` | Install in specified directory instead of current directory |
| `--dry-run` | Show what would be created without creating files |

---

## Generated Files Reference

| File | Template Used | Customization |
|---|---|---|
| `.specs/spec-system.md` | `system/spec-system.md` (verbatim copy) | None — universal rules |
| `.specs/constitution.md` | `system/constitution-template.md` | Filled from conversation + stack |
| `.specs/project.md` | `system/templates/project-template.md` | Filled from Phase A answers |
| `.specs/stacks/_default.md` | Stack preset (e.g., `stacks/presets/web-realtime.md`) | Customized with project-specific choices |
| `.specs/testing/strategy.md` | `system/templates/testing-strategy-template.md` | Tailored to project type and stack |
| `.specs/README.md` | Inline (template) | Filled with project name, initial ADRs |
| `.specs/changelog.md` | Inline | Empty global changelog with first entry |

---

## Execution Reliability Addendum

### Ambiguity and Contradiction Handling

If user answers are vague or contradictory, do not continue with hidden assumptions.

1. Ask up to **2 targeted questions** to resolve conflicts.
2. If conflict remains, present **2 explicit options** with trade-offs and ask for selection.
3. If user says "not sure", apply conservative defaults and mark them as `[ASSUMED]` in `project.md` and `_default.md`.

Common conflict examples:
- "Global users" + "single-region low cost"
- "No backend" + "real-time collaborative editing"
- "Under $100/month" + "high-throughput multi-region"

### Fast-Path Mode (Short Interview)

If user already knows their stack, allow a compact flow:

- Ask only 3 questions: project type, expected scale, must-have constraints.
- Confirm preset and generate files.
- Record skipped interview fields as `[NOT PROVIDED]` in `project.md`.

### Exit Criteria (Must Pass)

Before declaring success, verify:

- [ ] `.specs/spec-system.md` exists
- [ ] `.specs/project.md` contains users, scale, geography (or explicit placeholders)
- [ ] `.specs/stacks/_default.md` contains chosen stack + rationale
- [ ] At least 1 ADR exists in `.specs/stacks/decisions/`
- [ ] `.specs/testing/strategy.md` exists
- [ ] `.specs/README.md` exists with project name and initial ADRs
- [ ] `CLAUDE.md` contains a valid `<!-- livespec:start --> ... <!-- livespec:end -->` block

If any check fails, report the exact missing artifact and create/fix it before finishing.

*LiveSpec Command v1.0*
