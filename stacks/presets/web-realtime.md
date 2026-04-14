# Stack Preset: Web Real-Time

> Use this preset for applications with live updates, collaborative features, or frequently changing data.

---

## Use When

- Users need to see data update without refreshing the page
- Multiple users interact with shared data (collaboration, comments, presence)
- Events need to be pushed from server to clients (notifications, live feeds, dashboards)
- Data freshness requirement is under 2 seconds

## Do NOT Use When

- Data changes less than once per minute → use [web-static](web-static.md) or [api-rest](api-rest.md) with polling
- No user-facing frontend → use [api-rest](api-rest.md)
- Read-only content site → use [web-static](web-static.md)

---

## Infrastructure Decision Tree

```mermaid
flowchart TD
    A[New Web App] --> B{Users spread globally?}
    B -- Yes, latency matters --> C[Edge deployment]
    B -- No, single region ok --> D[Standard deployment]

    C --> E{Data freshness requirement?}
    D --> E

    E -- Under 500ms → live --> F[WebSocket / Supabase Realtime]
    E -- Under 5s → near-live --> G[Server-Sent Events]
    E -- Minutes ok → polling --> H[REST + polling interval]

    F --> I{Persistence needed?}
    G --> I
    H --> I

    I -- Yes, relational data --> J[PostgreSQL / Supabase]
    I -- Yes, document data --> K[MongoDB]
    I -- Ephemeral only --> L[Redis only]

    J --> M{Auth complexity?}
    K --> M
    L --> M

    M -- Social login + RLS --> N[Supabase Auth + RLS]
    M -- Custom logic needed --> O[Auth.js / Custom JWT]
    M -- Simple / internal --> P[JWT + middleware]

    N --> Q[Recommended: Supabase Stack]
    O --> R[Recommended: Next.js + Custom Auth]
    P --> R
```

---

## Recommended Stack

| Layer | Choice | Why |
|---|---|---|
| Framework | **Next.js 14** (App Router) | Server components + API routes + streaming |
| Runtime / Deploy | **Vercel** (Edge Functions where needed) | Zero-config, edge network, preview URLs |
| Database | **Supabase PostgreSQL** | Managed Postgres + realtime built in |
| Real-time | **Supabase Realtime** | WebSocket subscriptions on Postgres changes |
| Cache | **Upstash Redis** | Serverless Redis for rate limiting, sessions, queues |
| Auth | **Supabase Auth** | Row-Level Security + social providers built in |
| File Storage | **Supabase Storage** | S3-compatible, integrated with auth |
| Testing | **Vitest + Playwright** | Fast unit tests + full E2E + visual regression |
| CI/CD | **GitHub Actions** | Native GitHub integration |
| **Dev Tooling** | | |
| Package Manager | npm / pnpm / bun | User preference — ask during init |
| Linter | ESLint / Biome | ESLint: wider ecosystem; Biome: faster, unified |
| Formatter | Prettier / Biome | Prettier: standard; Biome: unified with linter |

---

## Architecture Pattern

```mermaid
graph TB
    subgraph Client
        C[React / Next.js App]
        WS[WebSocket Client]
    end

    subgraph Edge
        E[Vercel Edge Network]
        EF[Edge Functions]
    end

    subgraph Backend
        API[Next.js API Routes]
        RT[Supabase Realtime]
        AUTH[Supabase Auth]
    end

    subgraph Data
        PG[(PostgreSQL)]
        REDIS[(Upstash Redis)]
        S3[Supabase Storage]
    end

    C <--> E
    E --> API
    EF --> REDIS
    WS <--> RT
    API --> PG
    API --> REDIS
    RT --> PG
    AUTH --> PG
    API --> S3
```

---

## Latency Considerations

| Scenario | Expected Latency | Optimization |
|---|---|---|
| Initial page load | < 100ms | Edge caching, RSC streaming |
| API data fetch | < 200ms | Connection pooling (Supabase), Redis cache |
| Real-time event delivery | < 500ms | Supabase Realtime WebSocket |
| Database write | < 50ms | Supabase managed Postgres, regional instance |
| File upload | Variable | Multipart to Supabase Storage |

---

## Environment Variables

```env
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=xxx
SUPABASE_SERVICE_ROLE_KEY=xxx  # Server-side only

# Upstash Redis
UPSTASH_REDIS_REST_URL=https://xxx.upstash.io
UPSTASH_REDIS_REST_TOKEN=xxx
```

---

## Getting Started

```bash
# Create Next.js app
npx create-next-app@latest my-app --typescript --tailwind --app

# Install Supabase client
npm install @supabase/supabase-js @supabase/ssr

# Install Upstash Redis (optional)
npm install @upstash/redis

# Install testing tools
npm install -D vitest @vitejs/plugin-react @playwright/test
```

---

## Testing Strategy with This Stack

- **Unit tests:** Vitest — business logic, data transformations, utility functions
- **Integration tests:** Vitest + Supabase local emulator — API routes, database queries
- **E2E tests:** Playwright — full user flows against local or staging environment
- **Visual tests:** Playwright screenshots — UI components with defined visual specs
- **Real-time tests:** Playwright with WebSocket mocking — subscription behavior

See `testing-strategy-template.md` for detailed test examples.
See `system/testing/test-protocol.md` for the stack-agnostic discovery and execution protocol.

---

<!-- @spec FR-008: visual testing section in web presets — .specs/features/003-visual-testing-fidelity/spec.md#fr-008 -->

## Visual Testing

### Playwright Configuration

Use `maxDiffPixels: 0` — zero tolerance for regressions. Never use `maxDiffPixelRatio`.

```typescript
// playwright.config.ts
import { defineConfig } from '@playwright/test'

export default defineConfig({
  expect: {
    toHaveScreenshot: {
      // Zero tolerance — any pixel diff is a regression.
      // Use { maxDiffPixels: 10 } inline for screens with aa_tolerance: true.
      maxDiffPixels: 0,
    },
  },
})
```

### Component-Level Snapshots

Prefer component-level snapshots over full-page screenshots. Add `selector` to your spec.md Screens table:

```markdown
| Screen | Route      | Mockup       | selector                  | aa_tolerance |
|--------|------------|--------------|---------------------------|--------------|
| nav    | /dashboard | nav.png      | [data-testid='main-nav']  | false        |
| badge  | /dashboard | badge.png    | [data-testid='unread-badge'] | false     |
```

Generated test:
```typescript
await page.locator("[data-testid='unread-badge']").toHaveScreenshot("badge.png")
```

### Docker Render Environment

Pin Playwright to a Docker image to ensure identical pixel output locally and in CI.
Run `spec.test --reset-baselines` inside Docker for CI-compatible baselines.

```yaml
# docker-compose.visual.yml (auto-generated by spec.test on first run)
services:
  visual-tests:
    image: mcr.microsoft.com/playwright:v1.44.0-jammy
    volumes:
      - ./tests:/app/tests
      - ./.specs:/app/.specs
    command: npx playwright test tests/e2e/screens/
    working_dir: /app
```

### Baseline Workflow

```bash
# Intentional UI update → reset baselines (locally, never on CI)
spec.test <feature> --reset-baselines

# Approve the new baselines when prompted
# Approve baselines? [y/n/view <screen-name>] → y
```

---

## Deterministic Selection Profile

When this preset is selected, generate `_default.md` with these required fields:

- `Project Type`: web-realtime
- `Primary Latency Target`: `<500ms live events` or explicit alternative
- `Data Model`: relational/document/ephemeral
- `Auth Mode`: Supabase Auth / custom JWT / Auth.js
- `Deployment Mode`: edge-first / single-region
- `Cost Posture`: low-start / balanced / performance-first

If any field is unknown, set `[ASSUMED]` and list follow-up questions.

### Fallback Variants

If Supabase or Vercel is constrained by policy/cost/region, choose one variant explicitly:

1. `Next.js + PostgreSQL + Pusher + Auth.js`
2. `Remix + Postgres + SSE + custom JWT`
3. `SPA + API REST backend + polling/SSE` (near-real-time only)

Always document chosen variant and rejection reason for non-selected options.

---

*LiveSpec Stack Preset v1.0*
