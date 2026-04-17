import { defineConfig, devices } from '@playwright/test';

// @spec FR-010: Viewport matrix — .specs/features/010-visual-testing-complete/spec.md#fr-010
// @spec FR-015: Browser projects — .specs/features/010-visual-testing-complete/spec.md#fr-015

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    trace: 'on-first-retry',
    // Animations disabled by default for static visual tests; override per test for animation tests
    // @spec FR-019: Animation tests use animations: 'allow' — spec.md#fr-019
    animations: 'disabled',
  },

  // Snapshot path template routes baselines per project (viewport+browser combination)
  // @spec FR-011: Per-viewport baseline directories — spec.md#fr-011
  // @spec FR-016: Per-browser baseline directories — spec.md#fr-016
  snapshotPathTemplate: '{testDir}/{testFileDir}/baselines/{projectName}/{testName}-{arg}{ext}',

  // 5 critical project combinations (EC-013: avoids full 9-job matrix by default)
  // @spec FR-010: 3 viewports (mobile/tablet/desktop) — spec.md#fr-010
  // @spec FR-015: 3 browsers (chromium/firefox/webkit) — spec.md#fr-015
  projects: [
    {
      name: 'mobile-chromium',
      use: {
        browserName: 'chromium',
        // @spec AC-012: mobile viewport 375×667 — spec.md#ac-012
        viewport: { width: 375, height: 667 },
      },
    },
    {
      name: 'tablet-chromium',
      use: {
        browserName: 'chromium',
        // @spec AC-012: tablet viewport 768×1024 — spec.md#ac-012
        viewport: { width: 768, height: 1024 },
      },
    },
    {
      name: 'desktop-chromium',
      use: {
        browserName: 'chromium',
        // @spec AC-012: desktop viewport 1920×1080 — spec.md#ac-012
        viewport: { width: 1920, height: 1080 },
      },
    },
    {
      name: 'desktop-firefox',
      use: {
        browserName: 'firefox',
        // @spec AC-017: Firefox browser — spec.md#ac-017
        viewport: { width: 1920, height: 1080 },
      },
    },
    {
      name: 'desktop-webkit',
      use: {
        browserName: 'webkit',
        // @spec AC-017: WebKit browser — spec.md#ac-017
        viewport: { width: 1920, height: 1080 },
      },
    },
  ],
});
