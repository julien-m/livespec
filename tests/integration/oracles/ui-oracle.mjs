/** Frozen browser acceptance; Penflow certification is checked separately. */
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
const require = createRequire(import.meta.url);
const { chromium } = require("@playwright/test");
const browser = await chromium.launch({ headless: true });
try {
	const page = await browser.newPage();
	await page.goto(pathToFileURL(join(process.argv[2], "index.html")).href);
	await page.evaluate(() => {
		window.witnessSubmits = 0;
		document.querySelector("form").addEventListener("submit", () => window.witnessSubmits++);
	});
	const success = page.locator('[data-semantic-id="success"]');
	await page.locator('[data-semantic-id="submit-item"]').click();
	assert.equal(await page.evaluate(() => window.witnessSubmits), 0, "empty input submitted");
	assert.equal(await success.isVisible(), false, "empty success visible");
	await page.locator('[data-semantic-id="item-name"]').fill("Atelier du jeudi");
	await page.locator('[data-semantic-id="submit-item"]').click();
	assert.equal(await page.evaluate(() => window.witnessSubmits), 1, "valid submit missing");
	assert.equal(await success.isVisible(), true, "success missing");
	assert.match(await success.textContent(), /Atelier du jeudi/);
	console.log(JSON.stringify({ passed: true, assertions: 5 }));
} finally {
	await browser.close();
}
