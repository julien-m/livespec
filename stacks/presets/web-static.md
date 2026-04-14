# Stack Preset: Web Static

> Use this preset for content-driven sites, documentation, blogs, and marketing pages where content changes infrequently.

---

## Use When

- Content is primarily text, images, and static assets
- Content changes on a schedule (daily, weekly) not in real-time
- SEO and Core Web Vitals are critical
- Site is a blog, documentation, marketing page, landing page, or portfolio
- No authenticated user-specific dynamic content (or minimal)

## Do NOT Use When

- Users need to see live data updates → use [web-realtime](web-realtime.md)
- Significant user authentication and personalization → use [web-realtime](web-realtime.md)
- Complex data interactions → use [api-rest](api-rest.md) as backend

---

## Infrastructure Decision Tree

```mermaid
flowchart TD
    A[Content Site] --> B{Primary content type?}

    B -- Blog / Docs / Articles --> C[Markdown / MDX content]
    B -- Marketing / Landing --> D[Component-based pages]
    B -- E-commerce catalog --> E[CMS-driven content]

    C --> F{Content update frequency?}
    D --> F
    E --> F

    F -- Developer-driven deploys ok --> G[Git-based: Markdown in repo]
    F -- Non-technical editors need access --> H[Headless CMS: Contentlayer / Sanity / Notion]

    G --> I{JavaScript needed on page?}
    H --> I

    I -- Minimal / none --> J[Astro — zero JS by default]
    I -- Some interactivity --> K[Next.js static export]
    I -- Rich interactivity + content --> L[Next.js with ISR]

    J --> M[Deploy: Vercel / Cloudflare Pages / Netlify]
    K --> M
    L --> M
```

---

## Recommended Stack

| Layer | Choice | Why |
|---|---|---|
| Framework | **Astro** (for pure content) or **Next.js** (static export) | Astro = zero JS by default, best performance; Next.js = needed for more interactivity |
| Content | **Markdown / MDX** in repo, or **Contentlayer** | Type-safe content from Markdown files |
| Styling | **Tailwind CSS** | Utility-first, no unused CSS with PurgeCSS |
| Deploy | **Vercel** or **Cloudflare Pages** | CDN-first delivery, instant cache invalidation |
| Images | **Cloudinary** or built-in `<Image>` | Automatic format optimization, CDN delivery |
| Search | **Pagefind** (static) or **Algolia** (managed) | Pagefind is zero-server; Algolia scales to millions |
| Analytics | **Plausible** (privacy-first) or **Vercel Analytics** | No cookies, GDPR-friendly |
| Testing | **Vitest + Playwright** | Component tests + E2E for critical paths |
| **Dev Tooling** | | |
| Package Manager | npm / pnpm / bun | User preference — ask during init |
| Linter | ESLint / Biome | ESLint: wider ecosystem; Biome: faster, unified |
| Formatter | Prettier / Biome | Prettier: standard; Biome: unified with linter |

---

## Architecture Pattern

```mermaid
graph TB
    subgraph Build
        MD[Markdown / MDX Files]
        CMS[Headless CMS API]
        B[Build Process - Astro / Next.js]
    end

    subgraph CDN
        CF[Cloudflare / Vercel CDN]
        CACHE[Edge Cache]
    end

    subgraph Client
        Browser[Browser]
        HTML[Static HTML]
        JS[Minimal JS]
    end

    MD --> B
    CMS --> B
    B --> CF
    CF --> CACHE
    CACHE --> Browser
    HTML --> Browser
    JS --> Browser
```

---

## Performance Targets

| Metric | Target | How |
|---|---|---|
| Lighthouse Performance | > 95 | Static HTML, minimal JS, optimized images |
| LCP (Largest Contentful Paint) | < 2.5s | Image optimization, CDN delivery |
| CLS (Cumulative Layout Shift) | < 0.1 | Defined image dimensions, no layout shifts |
| FID / INP | < 100ms | Minimal JS, deferred non-critical scripts |
| Build time | < 60s | Incremental builds, content caching |

---

## Getting Started

```bash
# Astro (recommended for pure content sites)
npm create astro@latest my-site

# Next.js static export
npx create-next-app@latest my-site --typescript --tailwind --app
# Then in next.config.js: output: 'export'

# Install Contentlayer (for type-safe Markdown)
npm install contentlayer next-contentlayer

# Install testing tools
npm install -D vitest @playwright/test
```

---

## Deterministic Selection Profile

When this preset is selected, `_default.md` must include:

- `Rendering Mode`: SSG / ISR
- `Content Source`: git-mdx / headless-cms
- `Interactivity Budget`: minimal / moderate
- `Search Strategy`: Pagefind / Algolia
- `Analytics Strategy`: Plausible / provider-native
- `Deploy Target`: Vercel / Cloudflare Pages / Netlify

If any field is unknown, set `[ASSUMED]` and list one follow-up question per unknown.

See `system/testing/test-protocol.md` for the stack-agnostic discovery and execution protocol.

### Dynamic Escalation Rule

If personalization, auth complexity, or update frequency increases beyond static assumptions:

- mark `Escalation Suggested: web-realtime`
- list impacted pages/features
- recommend running `/spec.stack impact "web-static -> web-realtime"`

---

## Deployment Configuration (Copy-Paste Safe)

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "astro"
}
```

For Next.js static export, set `"framework": "nextjs"` and ensure static export is configured in `next.config.js`.

---

## When Content Changes

For **Git-based content:** Push to main → CI builds → Vercel deploys automatically

For **CMS-based content:** Editor saves → CMS sends webhook → Vercel triggers rebuild → Site updated in ~30s

---

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
| Screen | Route | Mockup   | selector             | aa_tolerance |
|--------|-------|----------|----------------------|--------------|
| logo   | /     | logo.png | [data-testid='logo'] | false        |
```

Generated test:
```typescript
await page.locator("[data-testid='logo']").toHaveScreenshot("logo.png")
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

*LiveSpec Stack Preset v1.0*
