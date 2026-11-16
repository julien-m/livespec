// Direct Node tool asset, like playwright_assertions/*.mjs: no consumer transpilation required.
// @spec FR-002: Exact existing suite execution
// — .specs/features/123-existing-test-journeys/spec.md#fr-002
import { realpathSync } from "node:fs";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

/** @type {{path: string, config: string|null, test_name: string|null}} */
const selection = JSON.parse(process.argv[2]);
const consumerRequire = createRequire(resolve(process.cwd(), "package.json"));
const { createVitest } = await import(pathToFileURL(consumerRequire.resolve("vitest/node")).href);
process.env.TEST = "true";
process.env.VITEST = "true";
process.env.NODE_ENV ??= "test";
const context = await createVitest("test", {
	config: selection.config ?? undefined,
	testNamePattern: selection.test_name ?? undefined,
	watch: false,
	run: true,
	passWithNoTests: false,
	// An empty reporter-specific destination selects stdout, independent of config.outputFile.
	reporters: [["json", { outputFile: "" }]],
});
try {
	await context.init();
	const selectedPath = realpathSync(selection.path);
	const specifications = (await context.globTestSpecifications([selection.path]))
		.filter(specification => realpathSync(specification.moduleId) === selectedPath);
	if (!specifications.length) {
		throw new Error("The configured runner did not collect the referenced test file");
	}
	const result = await context.runTestSpecifications(specifications);
	if (result.unhandledErrors.length || result.testModules.some(module => !module.ok())) {
		process.exitCode = 1;
	}
} finally {
	await context.close();
}
