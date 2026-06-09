// LiveSpec traceability anchors
// @spec(AC-012)
// @spec(AC-013)
// @spec(AC-016)
// @spec(AC-017)
// @spec(AC-018)
// @spec(FR-010)
// @spec(FR-011)
// @spec(FR-012)
// @spec(FR-015)
// @spec(FR-016)

import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
	testDir: "tests",
	snapshotPathTemplate:
		".specs/features/010-visual-testing-complete/baselines/{projectName}/{testFilePath}/{arg}{ext}",
	projects: [
		{
			name: "mobile-chromium",
			use: {
				...devices["Desktop Chrome"],
				browserName: "chromium",
				viewport: { width: 375, height: 667 },
			},
		},
		{
			name: "tablet-chromium",
			use: {
				...devices["Desktop Chrome"],
				browserName: "chromium",
				viewport: { width: 768, height: 1024 },
			},
		},
		{
			name: "desktop-chromium",
			use: {
				...devices["Desktop Chrome"],
				browserName: "chromium",
				viewport: { width: 1920, height: 1080 },
			},
		},
		{
			name: "desktop-firefox",
			use: {
				...devices["Desktop Firefox"],
				browserName: "firefox",
				viewport: { width: 1920, height: 1080 },
			},
		},
		{
			name: "desktop-webkit",
			use: {
				...devices["Desktop Safari"],
				browserName: "webkit",
				viewport: { width: 1920, height: 1080 },
			},
		},
	],
});
