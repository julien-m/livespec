# Testing Strategy: [Project Name]

> This document defines what to test, how to test it, and with which tools.
> Generated during `/spec.init` Phase B based on project type and stack.
> AI tools read this before generating test code in any feature plan.

---

## By Feature Type

| Feature Type | Test Types | Tools | When to Run |
|---|---|---|---|
| Business logic (pure functions) | Unit | Vitest | On every commit |
| API endpoints | Contract + Integration | Vitest + supertest | On every commit |
| UI Components (isolated) | Unit + Visual snapshot | Vitest + Storybook | On every commit |
| User flows (pages) | E2E + Visual regression | Playwright | On PR + nightly |
| Real-time features | E2E + WebSocket mocks | Playwright | On PR + nightly |
| Database queries | Integration | Vitest + test DB | On every commit |
| Authentication flows | E2E | Playwright | On PR |

---

## Unit Testing

**Framework:** Vitest (or Jest)

**What to test:**
- All pure functions in `src/data/` and `src/lib/`
- All utility functions
- All state management logic
- Component rendering in isolation (with mocked dependencies)

**What NOT to unit test:**
- Database queries (use integration tests)
- API endpoints (use integration tests)
- User interactions spanning multiple components (use E2E)

**File convention:**
- Test file lives next to source file: `notifications.ts` → `notifications.test.ts`
- Test names reference the AC: `"AC-001: returns unread notification count"`

**Example:**

```typescript
// src/data/notifications.test.ts
import { describe, it, expect, vi } from 'vitest'
import { getUnreadNotifications } from './notifications'

describe('getUnreadNotifications', () => {
  it('AC-001: returns only unread notifications for the given user', async () => {
    const mockDb = {
      select: vi.fn().mockResolvedValue([
        { id: '1', message: 'Hello', read: false },
      ]),
    }

    const result = await getUnreadNotifications('user-123', mockDb)

    expect(result).toHaveLength(1)
    expect(result[0].read).toBe(false)
  })
})
```

---

## Integration Testing

**Framework:** Vitest + supertest (or your project's HTTP testing tool)

**What to test:**
- Every API endpoint: happy path + error paths
- Database interactions with a real test database
- Authentication middleware

**Test database setup:**
- Use a separate test database (configured via `DATABASE_URL_TEST`)
- Run migrations before test suite
- Seed test data per test (not global state)
- Clean up after each test

**Example:**

```typescript
// tests/api/notifications.test.ts
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import request from 'supertest'
import { app } from '../../src/app'
import { seedNotifications, cleanupNotifications } from '../helpers/db'

describe('GET /api/notifications', () => {
  beforeEach(async () => {
    await seedNotifications({ userId: 'test-user', count: 3, unread: 2 })
  })

  afterEach(async () => {
    await cleanupNotifications('test-user')
  })

  it('AC-001: returns unread count for authenticated user', async () => {
    const response = await request(app)
      .get('/api/notifications')
      .set('Authorization', 'Bearer test-token')
      .expect(200)

    expect(response.body.unreadCount).toBe(2)
    expect(response.body.notifications).toHaveLength(3)
  })
})
```

---

## E2E Testing

**Framework:** Playwright

**What to test:**
- All primary user flows (one E2E test per user story P1 and P2)
- Authentication flows
- Critical business operations (checkout, publish, delete account)

**What NOT to E2E test:**
- Every edge case (use unit/integration for those)
- Component styling details (use visual tests)
- Performance (use dedicated tools)

**File convention:**
- Tests in `tests/e2e/`
- One file per feature: `tests/e2e/notifications.spec.ts`
- Test names reference the user story: `"Story 1: User receives real-time notification"`

---

## Visual Testing (Playwright)

> Visual tests capture and compare screenshots to detect unintended UI regressions.

### How It Works

1. **Baseline capture:** On first run, Playwright captures a screenshot and saves it as the baseline
2. **Comparison:** On subsequent runs, Playwright takes a new screenshot and diffs it against the baseline
3. **Threshold:** If diff > 2% → test FAILS and reports the diff image
4. **Update baseline:** When UI is intentionally changed, run `npx playwright test --update-snapshots`

### Visual Test Example

```typescript
// tests/e2e/notifications.spec.ts
import { test, expect } from '@playwright/test'

test.describe('Notification Panel — Visual Tests', () => {

  test('SC-004: empty state matches baseline', async ({ page }) => {
    // Navigate to the page
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Ensure user has no notifications (use seeded test state)
    await page.evaluate(() => window.__TEST_CLEAR_NOTIFICATIONS?.())

    // Open the notification panel
    await page.click('[data-testid="notification-bell"]')
    await page.waitForSelector('[data-testid="notification-panel"]')

    // Capture and compare screenshot
    await expect(page.locator('[data-testid="notification-panel"]'))
      .toHaveScreenshot('panel-empty.png', { threshold: 0.02 })
  })

  test('SC-004: panel with unread notifications matches baseline', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Seed notifications for this test
    await page.evaluate(() => window.__TEST_SEED_NOTIFICATIONS?.({ count: 3, unread: 2 }))

    await page.click('[data-testid="notification-bell"]')
    await page.waitForSelector('[data-testid="notification-panel"]')

    await expect(page.locator('[data-testid="notification-panel"]'))
      .toHaveScreenshot('panel-with-unread.png', { threshold: 0.02 })
  })

  test('badge count displays correctly', async ({ page }) => {
    await page.goto('/dashboard')

    // With 5 unread notifications
    await page.evaluate(() => window.__TEST_SEED_NOTIFICATIONS?.({ count: 5, unread: 5 }))
    await page.reload()
    await page.waitForLoadState('networkidle')

    await expect(page.locator('[data-testid="notification-bell"]'))
      .toHaveScreenshot('bell-badge-5.png', { threshold: 0.02 })
  })
})
```

### Baseline Management

- Baselines are stored in `.specs/features/NNN-feature-name/baselines/`
- Baselines are committed to version control
- When a spec changes intentionally: run `npx playwright test --update-snapshots`, commit new baselines
- Old baselines are moved to `baselines/archived/YYYY-MM-DD/` before deletion

### Playwright Configuration

```typescript
// playwright.config.ts
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  snapshotDir: './.specs/features', // Playwright uses {snapshotDir}/{testFilePath}/{testName}-{platform}.png
  // Individual baselines land in .specs/features/NNN-feature-name/baselines/ via test file path structure
  use: {
    baseURL: process.env.TEST_BASE_URL || 'http://localhost:3000',
    screenshot: 'only-on-failure',
  },
  expect: {
    toHaveScreenshot: {
      threshold: 0.02,  // 2% difference threshold
      maxDiffPixels: 100,
    },
  },
})
```

---

## Iteration Rule

When tests fail during `/spec.implement`:

- **Unit tests:** Max 3 fix iterations → then flag for human review
- **Integration tests:** Max 3 fix iterations → then flag for human review
- **E2E / Visual tests:** Max 5 fix iterations → then flag for human review

After max iterations, the AI stops, reports the failure with context, and asks the human to intervene.

---

## CI Pipeline

Tests run in CI on every PR and every push to main:

```yaml
# .github/workflows/test.yml (example)
test:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - run: npm ci
    - run: npm run test:unit       # Vitest unit + integration
    - run: npm run test:e2e        # Playwright E2E + visual
```

---

*Generated by `/spec.init` Phase B — LiveSpec v1.0*
*Update this file when testing tools or strategies change.*
