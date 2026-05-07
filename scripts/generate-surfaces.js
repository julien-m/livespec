#!/usr/bin/env node
// Migration script: generates .specs/surfaces.yaml from filesystem detection.
// Idempotent: skips if surfaces.yaml already exists.
//
// Usage:
//   node scripts/generate-surfaces.js              # Generate surfaces.yaml
//   node scripts/generate-surfaces.js --dry-run    # Preview without creating file
//   node scripts/generate-surfaces.js --force      # Overwrite existing file

import { existsSync, readdirSync, readFileSync, writeFileSync } from "fs";
import { join } from "path";

const SURFACES_CONFIG = ".specs/surfaces.yaml";

const WEB_MARKERS = [
	"react",
	"vue",
	"next",
	"nuxt",
	"svelte",
	"@angular",
	"astro",
	"vite",
	"webpack",
	"remix",
	"solid-js",
	"qwik",
	"@sveltejs",
];

// Backend directory names — skip these even if they have web deps (e.g., vite as bundler)
const BACKEND_DIR_NAMES = new Set([
	"api",
	"server",
	"backend",
	"worker",
	"workers",
	"functions",
	"lambda",
]);
const UI_FRAMEWORKS = [
	"react",
	"vue",
	"next",
	"nuxt",
	"svelte",
	"@angular",
	"astro",
	"solid-js",
	"qwik",
	"@sveltejs",
];

function hasWebDeps(dir) {
	const pkgPath = join(dir, "package.json");
	if (!existsSync(pkgPath)) {
		return false;
	}

	try {
		const pkg = JSON.parse(readFileSync(pkgPath, "utf-8"));
		const deps = { ...pkg.dependencies, ...pkg.devDependencies };
		const dependencyNames = Object.keys(deps);
		const hasWebMarker = WEB_MARKERS.some((marker) =>
			dependencyNames.some((dependencyName) => dependencyName.startsWith(marker)),
		);
		const hasUiFramework = UI_FRAMEWORKS.some((framework) =>
			dependencyNames.some((dependencyName) => dependencyName.startsWith(framework)),
		);
		return hasUiFramework || (hasWebMarker && hasRoutesDir(dir));
	} catch {
		// Treat unreadable or malformed package.json files as non-web so the migration stays best-effort.
		return false;
	}
}

function hasRoutesDir(dir) {
	const frontendRouteCandidates = ["app/routes", "src/pages", "pages", "src/app/routes"];
	if (frontendRouteCandidates.some((candidate) => existsSync(join(dir, candidate)))) {
		return true;
	}

	const srcRoutes = join(dir, "src", "routes");
	if (!existsSync(srcRoutes)) {
		return false;
	}

	try {
		const files = readdirSync(srcRoutes);
		return files.some(
			(fileName) =>
				fileName.endsWith(".tsx") ||
				fileName.endsWith(".jsx") ||
				fileName.endsWith(".vue"),
		);
	} catch {
		// Ignore unreadable route folders because they are only a heuristic signal for frontend detection.
		return false;
	}
}

function detectTestDir(dir) {
	const candidates = [
		join(dir, "tests", "e2e"),
		join(dir, "tests", "visual"),
		join(dir, "test", "e2e"),
	];

	for (const candidate of candidates) {
		if (existsSync(candidate)) {
			return candidate;
		}
	}

	// Default to tests/e2e so downstream migrations produce the conventional path even before tests exist.
	return join(dir, "tests", "e2e");
}

function findPlaywrightConfig(dir) {
	const tsPath = join(dir, "playwright.config.ts");
	if (existsSync(tsPath)) {
		return tsPath;
	}

	const jsPath = join(dir, "playwright.config.js");
	if (existsSync(jsPath)) {
		return jsPath;
	}

	return null;
}

function detectSurfaces() {
	// Check monorepo-style locations first, then legacy locations, so the first detected surface matches the most specific project layout.
	const surfaces = [];

	if (existsSync("apps")) {
		try {
			const appDirs = readdirSync("apps", { withFileTypes: true })
				.filter((directoryEntry) => directoryEntry.isDirectory())
				.map((directoryEntry) => directoryEntry.name);

			for (const appDir of appDirs) {
				const appPath = join("apps", appDir);
				const isBackendNamedDirectory = BACKEND_DIR_NAMES.has(appDir);
				const isWeb =
					!isBackendNamedDirectory && (hasWebDeps(appPath) || hasRoutesDir(appPath));
				const isNative =
					!isWeb &&
					(existsSync(join(appPath, "ios")) ||
						existsSync(join(appPath, "android")) ||
						existsSync(join(appPath, "Info.plist")) ||
						existsSync(join(appPath, "Package.swift")));

				if (isWeb) {
					const config = findPlaywrightConfig(appPath);
					surfaces.push({
						id: appDir,
						name: appDir.charAt(0).toUpperCase() + appDir.slice(1),
						path: appPath,
						testDir: detectTestDir(appPath),
						runner: "playwright",
						runnerConfig: config,
					});
					// Stop evaluating the same app as native once we have a web match because the manifest allows only one runner per surface.
					continue;
				}

				if (isNative) {
					surfaces.push({
						id: appDir,
						name: appDir.charAt(0).toUpperCase() + appDir.slice(1),
						path: appPath,
						testDir: detectTestDir(appPath),
						runner: "manual",
					});
				}
			}
		} catch {
			// Skip unreadable monorepo app folders so one bad directory does not block migration output.
		}
	}

	if (existsSync("packages") && surfaces.length === 0) {
		try {
			const packageDirs = readdirSync("packages", { withFileTypes: true })
				.filter((directoryEntry) => directoryEntry.isDirectory())
				.map((directoryEntry) => directoryEntry.name);

			for (const packageDir of packageDirs) {
				if (BACKEND_DIR_NAMES.has(packageDir)) {
					// Skip backend-named packages because shared tooling packages often depend on frontend bundlers without exposing a UI surface.
					continue;
				}

				const packagePath = join("packages", packageDir);
				if (!hasWebDeps(packagePath)) {
					// Ignore non-web packages here so later fallbacks can detect a dedicated frontend folder or root app instead.
					continue;
				}

				const config = findPlaywrightConfig(packagePath);
				surfaces.push({
					id: packageDir,
					name: packageDir.charAt(0).toUpperCase() + packageDir.slice(1),
					path: packagePath,
					testDir: detectTestDir(packagePath),
					runner: "playwright",
					runnerConfig: config,
				});
			}
		} catch {
			// Skip unreadable monorepo package folders so the generator can fall back to later detection paths.
		}
	}

	if (surfaces.length === 0 && existsSync("frontend")) {
		if (hasWebDeps("frontend") || hasRoutesDir("frontend")) {
			const config = findPlaywrightConfig("frontend");
			surfaces.push({
				id: "frontend",
				name: "Frontend",
				path: "frontend",
				testDir: detectTestDir("frontend"),
				runner: "playwright",
				runnerConfig: config,
			});
		}
	}

	if (surfaces.length === 0 && (hasWebDeps(".") || hasRoutesDir("."))) {
		const testDir = existsSync("tests/e2e")
			? "tests/e2e"
			: existsSync("tests/visual")
				? "tests/visual"
				: "tests/e2e";
		const config = findPlaywrightConfig(".");
		surfaces.push({
			id: "default",
			name: "Default",
			path: ".",
			testDir,
			runner: "playwright",
			runnerConfig: config,
		});
	}

	return surfaces;
}

function toYaml(surfaces) {
	// Build YAML in the exact field order expected by the checked-in manifest format so regeneration produces stable diffs.
	const lines = [
		"# Auto-generated by LiveSpec Migration v8",
		"# Edit to match your project structure",
		"",
		"surfaces:",
	];

	for (const surface of surfaces) {
		lines.push(`  - id: ${surface.id}`);
		lines.push(`    name: ${surface.name}`);
		lines.push(`    path: ${surface.path}`);
		lines.push(`    testDir: ${surface.testDir}`);
		lines.push(`    runner: ${surface.runner}`);
		if (surface.runnerConfig) {
			lines.push(`    runnerConfig: ${surface.runnerConfig}`);
		}
	}

	return `${lines.join("\n")}\n`;
}

function main() {
	const args = process.argv.slice(2);
	const dryRun = args.includes("--dry-run");
	const force = args.includes("--force");

	if (existsSync(SURFACES_CONFIG) && !force) {
		console.log(`${SURFACES_CONFIG} already exists — skipping generation`);
		console.log("Use --force to overwrite");
		return 0;
	}

	const surfaces = detectSurfaces();
	if (surfaces.length === 0) {
		console.log("No UI surfaces detected — skipping surfaces.yaml generation");
		return 0;
	}

	console.log(`Detected ${surfaces.length} surface(s):`);
	for (const surface of surfaces) {
		// Print one summary line per detected surface so dry runs stay easy to scan in CI logs.
		console.log(`  [${surface.id}] ${surface.name} (${surface.runner}) → ${surface.testDir}`);
	}

	if (dryRun) {
		console.log(`\n[DRY RUN] Would create ${SURFACES_CONFIG}:`);
		console.log(toYaml(surfaces));
		return 0;
	}

	const yaml = toYaml(surfaces);
	writeFileSync(SURFACES_CONFIG, yaml);
	console.log(`\nCreated ${SURFACES_CONFIG}`);
	return 0;
}

try {
	process.exitCode = main();
} catch (error) {
	console.error(error instanceof Error ? error.message : String(error));
	process.exitCode = 1;
}
