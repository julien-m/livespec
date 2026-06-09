#!/usr/bin/env node
// LiveSpec traceability anchors
// @spec(AC-004)
// @spec(AC-006)
// @spec(FR-001)
// @spec(FR-002)
// @spec(FR-005)
// @spec(FR-006)

// Migration script: generates .specs/surfaces.yaml from filesystem detection.
// Idempotent: skips if surfaces.yaml already exists (unless --force or --migrate-surfaces).
//
// Usage:
//   node scripts/generate-surfaces.js                    # Generate surfaces.yaml
//   node scripts/generate-surfaces.js --dry-run          # Preview without creating file
//   node scripts/generate-surfaces.js --force            # Overwrite existing file
//   node scripts/generate-surfaces.js --migrate-surfaces # Additive: append missing visual surface entries
//                                                       # to an existing manifest, preserving existing entries.
//                                                       # Combine with --dry-run to preview. --force takes precedence.

// @spec FR-001: detectTestDirs returns array, FR-008: extend findPlaywrightConfig — .specs/features/036-multi-surface-detection-and-migration/spec.md#fr-001
// @spec FR-001: iOS/watchOS surface detection — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-001
// @spec FR-001: Android/Maestro surface detection — .specs/features/031-ui-runner-android/spec.md#fr-001
import { existsSync, readdirSync, readFileSync, writeFileSync } from "fs";
import { basename, join } from "path";
import { fileURLToPath } from "url";
// @spec FR-004: Xcode test target enumeration — .specs/features/037-test-multi-runner-integration/spec.md#fr-004
import {
	enumerateAndFallback,
	kebabize,
	listSharedSchemes,
	pickSchemeForPlatform,
} from "./lib/pbxproj.js";

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

// @spec FR-001: iOS/watchOS surface detection — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-001
/**
 * Detect whether a directory contains an Xcode project (iOS/watchOS).
 * Matches: Package.swift at root OR a *.xcodeproj directory.
 */
export function hasXcodeProject(dir) {
	if (existsSync(join(dir, "Package.swift"))) return true;
	try {
		const entries = readdirSync(dir, { withFileTypes: true });
		return entries.some(
			(entry) => entry.isDirectory() && entry.name.endsWith(".xcodeproj"),
		);
	} catch {
		return false;
	}
}

/**
 * Locate the .xcodeproj directory inside a project directory.
 * @param {string} dir
 * @returns {string | null}
 */
export function findXcodeProjectDir(dir) {
	try {
		const entries = readdirSync(dir, { withFileTypes: true });
		for (const entry of entries) {
			if (entry.isDirectory() && entry.name.endsWith(".xcodeproj")) {
				return join(dir, entry.name);
			}
		}
	} catch {
		// fall through
	}
	return null;
}

// @spec FR-001: runnerConfig wiring — .specs/features/038-runner-config-wiring/spec.md#fr-001
/**
 * Build the runnerConfig payload for an xcuitest surface so the dispatcher can
 * pass `-scheme`/`-project`/`-destination` to xcodebuild without filesystem
 * introspection at runtime.
 *
 * @param {string} xcodeprojDir      Absolute path to the .xcodeproj directory
 * @param {"ios"|"watchos"|undefined} platform
 * @returns {Record<string, string> | null}
 */
export function buildXcuitestRunnerConfig(xcodeprojDir, platform, testTargetName) {
	if (!xcodeprojDir) return null;
	// xcodebuild runs with cwd = surface.path, so -project must be the project
	// name relative to that directory (just the basename, not the full repo path).
	const projectPath = basename(xcodeprojDir);
	const schemes = listSharedSchemes(xcodeprojDir);
	const scheme = pickSchemeForPlatform(schemes, platform);
	// Do NOT hardcode a specific simulator name (e.g. "iPhone 16") — runtimes
	// vary across machines (iPhone 16 not installed on iOS 26+ hosts). The
	// XCUITestRunnerHandler auto-detects the first available simulator at
	// runtime via `xcrun simctl list devices --json`. We only emit `platform`
	// so the handler picks the correct family (iOS vs watchOS).
	const config = { project: projectPath };
	if (platform) config.platform = platform;
	if (scheme) config.scheme = scheme;
	// onlyTesting restricts xcodebuild to a single test bundle. Required when
	// the scheme has multiple test targets across platforms (iOS UITests +
	// watchOS UITests in the same scheme): otherwise xcodebuild builds and
	// tries to run the wrong-platform bundles, which fails.
	if (testTargetName) config.onlyTesting = testTargetName;
	return config;
}

/**
 * Build the runnerConfig payload for a maestro surface so the dispatcher can
 * propagate AVD selection without re-detecting the layout at runtime.
 *
 * @param {string} flowsDir
 * @returns {Record<string, string>}
 */
export function buildMaestroRunnerConfig(flowsDir) {
	return {
		flowsDir,
		platform: "android",
	};
}

// @spec FR-001: Android/Maestro surface detection — .specs/features/031-ui-runner-android/spec.md#fr-001
/**
 * Detect whether a directory contains an Android Gradle project.
 * Matches: build.gradle or build.gradle.kts at root or in app/ subdirectory.
 */
export function hasAndroidProject(dir) {
	return (
		existsSync(join(dir, "build.gradle")) ||
		existsSync(join(dir, "build.gradle.kts")) ||
		existsSync(join(dir, "app", "build.gradle")) ||
		existsSync(join(dir, "app", "build.gradle.kts"))
	);
}

// @spec FR-003: Maestro flows directory detection — .specs/features/031-ui-runner-android/spec.md#fr-003
/**
 * Detect whether a directory has Maestro flow YAML files.
 * Matches: .specs/maestro/ OR maestro/ directory presence.
 */
export function hasMaestroFlows(dir) {
	return (
		existsSync(join(dir, ".specs", "maestro")) ||
		existsSync(join(dir, "maestro"))
	);
}

export function hasWebDeps(dir) {
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

export function hasRoutesDir(dir) {
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

/**
 * Detects test directories under an app/package/frontend dir.
 *
 * Returns an array of `TestDirEntry = { testDir: string, configFile: string | null }`.
 * - If `tests/e2e` exists → entry with `playwright.config.ts` (preferred inside testDir, fallback to dir root)
 * - If `tests/visual` exists → entry with `playwright.visual.config.ts` (preferred inside testDir, fallback to dir root)
 * - If neither exists → single default entry pointing at `tests/e2e` (backward compat: projects that haven't created their test dir yet still receive a deterministic surface entry)
 *
 * Id derivation rule (applied by `detectSurfaces`): the e2e entry maps to `<appdir>`, the visual entry to `<appdir>-visual`.
 *
 * @spec FR-001: detectTestDirs replaces detectTestDir, FR-008: visual config detection — .specs/features/036-multi-surface-detection-and-migration/spec.md#fr-001
 */
export function detectTestDirs(dir) {
	const entries = [];
	const e2eDir = join(dir, "tests", "e2e");
	const visualDir = join(dir, "tests", "visual");
	const legacyTestE2e = join(dir, "test", "e2e");

	if (existsSync(e2eDir)) {
		entries.push({
			testDir: e2eDir,
			configFile: findPlaywrightConfig(e2eDir) ?? findPlaywrightConfig(dir),
		});
	}
	if (existsSync(visualDir)) {
		entries.push({
			testDir: visualDir,
			configFile:
				findVisualPlaywrightConfig(visualDir) ?? findVisualPlaywrightConfig(dir),
		});
	}
	if (entries.length === 0 && existsSync(legacyTestE2e)) {
		entries.push({
			testDir: legacyTestE2e,
			configFile: findPlaywrightConfig(dir),
		});
	}
	if (entries.length === 0) {
		// Default to tests/e2e so downstream migrations produce the conventional path even before tests exist.
		entries.push({
			testDir: e2eDir,
			configFile: findPlaywrightConfig(dir),
		});
	}
	return entries;
}

export function findPlaywrightConfig(dir) {
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

/**
 * Find a `playwright.visual.config.{ts,js}` in `dir`. Returns null if absent.
 *
 * @spec FR-008: visual config detection — .specs/features/036-multi-surface-detection-and-migration/spec.md#fr-008
 */
export function findVisualPlaywrightConfig(dir) {
	const tsPath = join(dir, "playwright.visual.config.ts");
	if (existsSync(tsPath)) {
		return tsPath;
	}

	const jsPath = join(dir, "playwright.visual.config.js");
	if (existsSync(jsPath)) {
		return jsPath;
	}

	return null;
}

/**
 * Build one or two surface objects for a single app/package/frontend dir.
 *
 * Id derivation:
 *  - First TestDirEntry (e2e or sole) → `id: <baseId>`
 *  - Second TestDirEntry (visual)     → `id: <baseId>-visual`, unless that id collides with an
 *    existing app dir name in `siblingNames`, in which case `<baseId>-visual-v2` is used.
 *
 * Emits `console.warn(...)` with a `migrate-visual-tests.js` hint when both e2e and visual are detected.
 *
 * @spec FR-002: emit per tuple, FR-003: split-layout warning, FR-007: collision detection — .specs/features/036-multi-surface-detection-and-migration/spec.md#fr-002
 */
function buildSurfacesForDir({ baseId, displayName, dirPath, runner, siblingNames }) {
	const entries = detectTestDirs(dirPath);
	const surfaces = [];

	if (entries.length === 0) {
		return surfaces;
	}

	const [primary, secondary] = entries;
	const primarySurface = {
		id: baseId,
		name: displayName,
		path: dirPath,
		testDir: primary.testDir,
		runner,
	};
	if (runner === "playwright") {
		primarySurface.runnerConfig = primary.configFile;
	}
	surfaces.push(primarySurface);

	if (secondary) {
		const visualBase = `${baseId}-visual`;
		let visualId = visualBase;
		if (siblingNames && siblingNames.has(visualBase)) {
			visualId = `${visualBase}-v2`;
			console.warn(
				`[WARNING] Visual surface id "${visualBase}" collides with existing app dir; using "${visualId}" instead.`,
			);
		}
		const visualSurface = {
			id: visualId,
			name: `${displayName} Visual`,
			path: dirPath,
			testDir: secondary.testDir,
			runner,
		};
		if (runner === "playwright") {
			visualSurface.runnerConfig = secondary.configFile;
		}
		surfaces.push(visualSurface);

		console.warn(
			`[WARNING] Split test layout detected in ${dirPath}: both tests/e2e and tests/visual found. Consider running migrate-visual-tests.js to consolidate into a single surface.`,
		);
	}

	return surfaces;
}

/**
 * Detect all surfaces in the current working directory.
 *
 * Ordering guarantee (app-interleaved): for monorepos, surfaces are ordered as
 *   [<app1>, <app1>-visual, <app2>, <app2>-visual, ...]
 * (in `readdirSync` order — typically alphabetical on macOS/Linux).
 *
 * @spec FR-002: emit per tuple, FR-007: collision rule — .specs/features/036-multi-surface-detection-and-migration/spec.md#fr-002
 */
export function detectSurfaces() {
	// Check monorepo-style locations first, then legacy locations, so the first detected surface matches the most specific project layout.
	const surfaces = [];

	if (existsSync("apps")) {
		try {
			const appDirs = readdirSync("apps", { withFileTypes: true })
				.filter((directoryEntry) => directoryEntry.isDirectory())
				.map((directoryEntry) => directoryEntry.name);
			const siblingNames = new Set(appDirs);

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
						existsSync(join(appPath, "Package.swift")) ||
						hasXcodeProject(appPath) ||
						hasAndroidProject(appPath));

				if (isWeb) {
					surfaces.push(
						...buildSurfacesForDir({
							baseId: appDir,
							displayName: appDir.charAt(0).toUpperCase() + appDir.slice(1),
							dirPath: appPath,
							runner: "playwright",
							siblingNames,
						}),
					);
					// Stop evaluating the same app as native once we have a web match because the manifest allows only one runner per surface.
					continue;
				}

				if (isNative) {
					// @spec FR-004: enumerate Xcode test targets — .specs/features/037-test-multi-runner-integration/spec.md#fr-004
					if (hasXcodeProject(appPath)) {
						const xcodeprojDir = findXcodeProjectDir(appPath);
						/** @type {Array<{name:string, productType:string, kind:string, platform:string, directory:string}>} */
						let targets = [];
						/** @type {string[]} */
						let warnings = [];
						if (xcodeprojDir) {
							const result = enumerateAndFallback(xcodeprojDir, appPath);
							targets = result.targets;
							warnings = result.warnings;
						}
						for (const w of warnings) {
							console.warn(`WARNING: ${w}`);
						}
						if (targets.length > 0) {
							for (const t of targets) {
								const id = `${appDir}-${kebabize(t.name)}`;
								surfaces.push({
									id,
									name: `${appDir.charAt(0).toUpperCase() + appDir.slice(1)} ${t.name}`,
									path: appPath,
									testDir: t.directory,
									runner: "xcuitest",
									platform: t.platform,
									kind: t.kind,
									runnerConfig: buildXcuitestRunnerConfig(xcodeprojDir, t.platform),
								});
							}
						} else if (xcodeprojDir) {
							// pbxproj parsed but no test targets enumerated -- emit a placeholder
							// surface so client projects with bare-bones .xcodeproj fixtures still
							// pick up xcuitest detection (Feature 030 backward compat).
							console.warn(
								`WARNING: ${appDir} has .xcodeproj but no test targets - emitting fallback surface`,
							);
							surfaces.push({
								id: appDir,
								name: appDir.charAt(0).toUpperCase() + appDir.slice(1),
								path: appPath,
								testDir: join(appPath, "UITests"),
								runner: "xcuitest",
								platform: "ios",
								runnerConfig: buildXcuitestRunnerConfig(xcodeprojDir, "ios"),
							});
						} else {
							surfaces.push({
								id: appDir,
								name: appDir.charAt(0).toUpperCase() + appDir.slice(1),
								path: appPath,
								testDir: join(appPath, "UITests"),
								runner: "xcuitest",
								platform: "ios",
							});
						}
					// @spec FR-001: Android/Maestro surface detection — .specs/features/031-ui-runner-android/spec.md#fr-001
					} else if (hasAndroidProject(appPath) && hasMaestroFlows(appPath)) {
						const maestroDir = existsSync(join(appPath, ".specs", "maestro"))
							? join(appPath, ".specs", "maestro")
							: join(appPath, "maestro");
						surfaces.push({
							id: appDir,
							name: appDir.charAt(0).toUpperCase() + appDir.slice(1),
							path: appPath,
							testDir: maestroDir,
							runner: "maestro",
							platform: "android",
							runnerConfig: buildMaestroRunnerConfig(maestroDir),
						});
					} else {
						surfaces.push(
							...buildSurfacesForDir({
								baseId: appDir,
								displayName: appDir.charAt(0).toUpperCase() + appDir.slice(1),
								dirPath: appPath,
								runner: "manual",
								siblingNames,
							}),
						);
					}
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
			const siblingNames = new Set(packageDirs);

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

				surfaces.push(
					...buildSurfacesForDir({
						baseId: packageDir,
						displayName: packageDir.charAt(0).toUpperCase() + packageDir.slice(1),
						dirPath: packagePath,
						runner: "playwright",
						siblingNames,
					}),
				);
			}
		} catch {
			// Skip unreadable monorepo package folders so the generator can fall back to later detection paths.
		}
	}

	if (surfaces.length === 0 && existsSync("frontend")) {
		if (hasWebDeps("frontend") || hasRoutesDir("frontend")) {
			surfaces.push(
				...buildSurfacesForDir({
					baseId: "frontend",
					displayName: "Frontend",
					dirPath: "frontend",
					runner: "playwright",
					siblingNames: new Set(["frontend"]),
				}),
			);
		}
	}

	if (surfaces.length === 0 && (hasWebDeps(".") || hasRoutesDir("."))) {
		surfaces.push(
			...buildSurfacesForDir({
				baseId: "default",
				displayName: "Default",
				dirPath: ".",
				runner: "playwright",
				siblingNames: new Set(["default"]),
			}),
		);
	}

	// @spec FR-001: iOS/watchOS root-level detection — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-001
	if (surfaces.length === 0 && hasXcodeProject(".")) {
		const xcodeprojDir = findXcodeProjectDir(".");
		if (xcodeprojDir) {
			const result = enumerateAndFallback(xcodeprojDir, ".");
			for (const warning of result.warnings) {
				console.warn(`WARNING: ${warning}`);
			}
			if (result.targets.length > 0) {
				// Only UI-testing bundles capture screenshots; unit-test bundles
				// can't run XCUIScreen.main.screenshot(). Filter so visual surfaces
				// stay actionable for the dispatcher.
				const uiTargets = result.targets.filter((t) => t.kind === "ui");
				const skipped = result.targets.filter((t) => t.kind !== "ui");
				for (const t of skipped) {
					console.warn(
						`Skipping ${t.name} (kind=${t.kind}) — only UI Testing Bundles emit visual baselines`,
					);
				}
				if (uiTargets.length === 0) {
					console.warn(
						"WARNING: project has test targets but none are UI Testing Bundles. " +
							"Run `livespec ui-runner scaffold --target ios` and create a UI Testing Bundle in Xcode.",
					);
				}
				for (const target of uiTargets) {
					surfaces.push({
						id: kebabize(target.name),
						name: target.name,
						path: ".",
						testDir: target.directory,
						runner: "xcuitest",
						platform: target.platform,
						kind: target.kind,
						runnerConfig: buildXcuitestRunnerConfig(
							xcodeprojDir,
							target.platform,
							target.name,
						),
					});
				}
			} else {
				// pbxproj parsed but no test targets enumerated -- emit a placeholder
				// surface so client projects with bare-bones .xcodeproj fixtures still
				// pick up xcuitest detection (Feature 030 backward compat).
				console.warn(
					"WARNING: default project has .xcodeproj but no test targets - emitting fallback surface (testDir: UITests)",
				);
				surfaces.push({
					id: "default",
					name: "Default",
					path: ".",
					testDir: "UITests",
					runner: "xcuitest",
					platform: "ios",
					runnerConfig: buildXcuitestRunnerConfig(xcodeprojDir, "ios"),
				});
			}
		} else {
			surfaces.push({
				id: "default",
				name: "Default",
				path: ".",
				testDir: "UITests",
				runner: "xcuitest",
				platform: "ios",
			});
		}
	}

	// @spec FR-001: Android/Maestro root-level detection — .specs/features/031-ui-runner-android/spec.md#fr-001
	if (surfaces.length === 0 && hasAndroidProject(".") && hasMaestroFlows(".")) {
		const maestroDir = existsSync(join(".", ".specs", "maestro"))
			? join(".", ".specs", "maestro")
			: "maestro";
		surfaces.push({
			id: "default",
			name: "Default",
			path: ".",
			testDir: maestroDir,
			runner: "maestro",
			platform: "android",
			runnerConfig: buildMaestroRunnerConfig(maestroDir),
		});
	}

	return surfaces;
}

export function toYaml(surfaces) {
	// Build YAML in the exact field order expected by the checked-in manifest format so regeneration produces stable diffs.
	const lines = [
		"# Auto-generated by LiveSpec Migration v8",
		"# Edit to match your project structure",
		"",
		"surfaces:",
	];

	for (const surface of surfaces) {
		lines.push(...surfaceToYamlLines(surface));
	}

	return `${lines.join("\n")}\n`;
}

/**
 * Quote a YAML scalar when it contains characters that confuse the parser
 * (commas, colons, equals, brackets). Identifiers and bare paths are emitted
 * verbatim so existing diffs stay stable.
 */
function yamlScalar(value) {
	const str = String(value);
	if (/[:,={}\[\]#&*!|>'"%@`]/.test(str) || /\s/.test(str)) {
		return `"${str.replace(/"/g, '\\"')}"`;
	}
	return str;
}

function surfaceToYamlLines(surface) {
	const lines = [];
	lines.push(`  - id: ${surface.id}`);
	lines.push(`    name: ${surface.name}`);
	lines.push(`    path: ${surface.path}`);
	lines.push(`    testDir: ${surface.testDir}`);
	lines.push(`    runner: ${surface.runner}`);
	if (surface.platform) {
		lines.push(`    platform: ${surface.platform}`);
	}
	if (surface.runnerConfig != null) {
		if (typeof surface.runnerConfig === "string") {
			// Legacy form: runnerConfig is a single value (e.g. playwright config path).
			lines.push(`    runnerConfig: ${surface.runnerConfig}`);
		} else if (typeof surface.runnerConfig === "object") {
			// Structured form: emit a nested map so xcodebuild/maestro flags survive
			// the YAML round-trip into the dispatcher.
			const keys = Object.keys(surface.runnerConfig);
			if (keys.length > 0) {
				lines.push("    runnerConfig:");
				for (const key of keys) {
					lines.push(`      ${key}: ${yamlScalar(surface.runnerConfig[key])}`);
				}
			}
		}
	}
	return lines;
}

/**
 * Additive migration: read existing surfaces.yaml as raw text, detect missing visual surfaces,
 * and append them to the end of the file. Existing content is preserved byte-for-byte.
 *
 * INVARIANT: never parse + reserialize the YAML — only append new lines. This guarantees
 * AC-005 (byte-for-byte preservation of existing entries, including manual edits and comments).
 *
 * @spec FR-004: --migrate-surfaces additive migration — .specs/features/036-multi-surface-detection-and-migration/spec.md#fr-004
 */
export function runMigrateSurfaces({ dryRun }) {
	if (!existsSync(SURFACES_CONFIG)) {
		console.error(
			`${SURFACES_CONFIG} does not exist — nothing to migrate. Run without --migrate-surfaces to generate.`,
		);
		return 1;
	}

	const existingText = readFileSync(SURFACES_CONFIG, "utf-8");
	// Parse existing surface ids by scanning lines (text-level) so user comments and custom fields are preserved.
	const existingIds = new Set();
	for (const rawLine of existingText.split("\n")) {
		const match = rawLine.match(/^\s*-\s+id:\s*(.+?)\s*$/);
		if (match) {
			existingIds.add(match[1]);
		}
	}

	const detected = detectSurfaces();
	const missing = detected.filter((surface) => !existingIds.has(surface.id));

	if (missing.length === 0) {
		console.log("No new surfaces detected — surfaces.yaml is up to date.");
		return 0;
	}

	const newBlocks = missing.flatMap((surface) => surfaceToYamlLines(surface));
	// Ensure exactly one trailing newline before appending; the existing file always ends with `\n` per toYaml.
	const prefix = existingText.endsWith("\n") ? existingText : `${existingText}\n`;
	const appendedText = `${newBlocks.join("\n")}\n`;
	const updated = `${prefix}${appendedText}`;

	console.log(`Detected ${missing.length} new surface(s) to append:`);
	for (const surface of missing) {
		console.log(`  [${surface.id}] ${surface.name} (${surface.runner}) → ${surface.testDir}`);
	}

	if (dryRun) {
		console.log(`\n[DRY RUN] Would append to ${SURFACES_CONFIG}:`);
		console.log(appendedText);
		return 0;
	}

	writeFileSync(SURFACES_CONFIG, updated);
	console.log(`\nAppended ${missing.length} new surface(s) to ${SURFACES_CONFIG}`);
	return 0;
}

/**
 * Migration v12: additive migration that appends native (xcuitest + maestro) surfaces
 * to an existing surfaces.yaml. Mirrors runMigrateSurfaces but targets iOS/Android runners.
 *
 * INVARIANT: never parse + reserialize the YAML — only append new lines.
 *
 * @spec FR-001: iOS/watchOS migration v12 — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-001
 * @spec FR-001: Android/Maestro migration v12 — .specs/features/031-ui-runner-android/spec.md#fr-001
 */
export function runMigrateNativeSurfaces({ dryRun }) {
	if (!existsSync(SURFACES_CONFIG)) {
		console.error(
			`${SURFACES_CONFIG} does not exist — nothing to migrate. Run without --migrate-native to generate.`,
		);
		return 1;
	}

	const existingText = readFileSync(SURFACES_CONFIG, "utf-8");
	const existingIds = new Set();
	for (const rawLine of existingText.split("\n")) {
		const match = rawLine.match(/^\s*-\s+id:\s*(.+?)\s*$/);
		if (match) {
			existingIds.add(match[1]);
		}
	}

	const detected = detectSurfaces();
	// Only native runners (xcuitest, maestro) — web surfaces are handled by runMigrateSurfaces
	const nativeSurfaces = detected.filter(
		(surface) => surface.runner === "xcuitest" || surface.runner === "maestro",
	);
	const missing = nativeSurfaces.filter((surface) => !existingIds.has(surface.id));

	if (missing.length === 0) {
		console.log("No new native surfaces detected — surfaces.yaml is up to date.");
		return 0;
	}

	const newBlocks = missing.flatMap((surface) => surfaceToYamlLines(surface));
	const prefix = existingText.endsWith("\n") ? existingText : `${existingText}\n`;
	const appendedText = `${newBlocks.join("\n")}\n`;
	const updated = `${prefix}${appendedText}`;

	console.log(`Detected ${missing.length} new native surface(s) to append:`);
	for (const surface of missing) {
		console.log(`  [${surface.id}] ${surface.name} (${surface.runner}/${surface.platform}) → ${surface.testDir}`);
	}

	if (dryRun) {
		console.log(`\n[DRY RUN] Would append to ${SURFACES_CONFIG}:`);
		console.log(appendedText);
		return 0;
	}

	writeFileSync(SURFACES_CONFIG, updated);
	console.log(`\nAppended ${missing.length} native surface(s) to ${SURFACES_CONFIG}`);
	return 0;
}

export function main() {
	const args = process.argv.slice(2);
	const dryRun = args.includes("--dry-run");
	const force = args.includes("--force");
	const migrateSurfaces = args.includes("--migrate-surfaces");
	const migrateNative = args.includes("--migrate-native");

	if (migrateNative && !force) {
		// Migration v12: append iOS/Android surfaces to existing manifest.
		return runMigrateNativeSurfaces({ dryRun });
	}

	if (migrateSurfaces && !force) {
		// --force takes precedence over --migrate-surfaces (full regenerate).
		return runMigrateSurfaces({ dryRun });
	}

	if (migrateSurfaces && force) {
		console.log("--force takes precedence over --migrate-surfaces — regenerating from scratch.");
	}

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

// Only execute main() when run directly as a script — not when imported (e.g., from tests).
const isDirectExecution =
	typeof process !== "undefined" &&
	process.argv[1] &&
	fileURLToPath(import.meta.url) === process.argv[1];

if (isDirectExecution) {
	try {
		process.exitCode = main();
	} catch (error) {
		console.error(error instanceof Error ? error.message : String(error));
		process.exitCode = 1;
	}
}
