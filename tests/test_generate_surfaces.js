// Tests for scripts/generate-surfaces.js — multi-surface detection and migration.
// Feature 036.

import { describe, test, expect, beforeEach, afterEach, mock } from "bun:test";
import {
	existsSync,
	readFileSync,
	writeFileSync,
	mkdtempSync,
	mkdirSync,
	rmSync,
	cpSync,
} from "fs";
import { join, dirname, resolve } from "path";
import { tmpdir } from "os";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "..");
const FIXTURES_ROOT = join(__dirname, "fixtures", "surfaces");
const SCRIPT_PATH = join(REPO_ROOT, "scripts", "generate-surfaces.js");

// Import production functions (named ESM exports added by Steps 1-4).
const mod = await import(SCRIPT_PATH);
const {
	detectTestDirs,
	findPlaywrightConfig,
	findVisualPlaywrightConfig,
	detectSurfaces,
	buildXcuitestRunnerConfig,
	buildMaestroRunnerConfig,
} = mod;

const PBXPROJ_MOD = await import(join(REPO_ROOT, "scripts", "lib", "pbxproj.js"));
const { listSharedSchemes, pickSchemeForPlatform } = PBXPROJ_MOD;

let savedCwd;
let workDir;

function copyFixture(name) {
	const dst = mkdtempSync(join(tmpdir(), `surfaces-${name}-`));
	cpSync(join(FIXTURES_ROOT, name), dst, { recursive: true });
	return dst;
}

beforeEach(() => {
	savedCwd = process.cwd();
});

afterEach(() => {
	process.chdir(savedCwd);
	if (workDir && existsSync(workDir)) {
		rmSync(workDir, { recursive: true, force: true });
	}
	workDir = undefined;
});

describe("detectTestDirs()", () => {
	test("returns 2 entries when both tests/e2e and tests/visual exist", () => {
		workDir = copyFixture("split-layout");
		process.chdir(workDir);
		const entries = detectTestDirs("apps/web");
		expect(entries.length).toBe(2);
		expect(entries[0].testDir).toBe(join("apps/web", "tests", "e2e"));
		expect(entries[1].testDir).toBe(join("apps/web", "tests", "visual"));
		expect(entries[0].configFile).toBe(join("apps/web", "playwright.config.ts"));
		expect(entries[1].configFile).toBe(join("apps/web", "playwright.visual.config.ts"));
	});

	test("returns 1 entry when only tests/e2e exists", () => {
		workDir = copyFixture("single-surface");
		process.chdir(workDir);
		const entries = detectTestDirs("apps/web");
		expect(entries.length).toBe(1);
		expect(entries[0].testDir).toBe(join("apps/web", "tests", "e2e"));
	});

	test("returns 1 visual entry when only tests/visual exists", () => {
		workDir = mkdtempSync(join(tmpdir(), "surfaces-visonly-"));
		mkdirSync(join(workDir, "apps/web/tests/visual"), { recursive: true });
		writeFileSync(join(workDir, "apps/web/playwright.visual.config.ts"), "export default {};\n");
		process.chdir(workDir);
		const entries = detectTestDirs("apps/web");
		expect(entries.length).toBe(1);
		expect(entries[0].testDir).toBe(join("apps/web", "tests", "visual"));
		expect(entries[0].configFile).toBe(join("apps/web", "playwright.visual.config.ts"));
	});

	test("returns default 1 entry when neither exists (backward compat)", () => {
		workDir = mkdtempSync(join(tmpdir(), "surfaces-empty-"));
		mkdirSync(join(workDir, "apps/web"), { recursive: true });
		process.chdir(workDir);
		const entries = detectTestDirs("apps/web");
		expect(entries.length).toBe(1);
		expect(entries[0].testDir).toBe(join("apps/web", "tests", "e2e"));
	});
});

describe("findVisualPlaywrightConfig()", () => {
	test("finds playwright.visual.config.ts inside testDir (prefer inner)", () => {
		workDir = mkdtempSync(join(tmpdir(), "surfaces-vc-inner-"));
		mkdirSync(join(workDir, "apps/web/tests/visual"), { recursive: true });
		writeFileSync(
			join(workDir, "apps/web/tests/visual/playwright.visual.config.ts"),
			"export default {};\n",
		);
		process.chdir(workDir);
		const cfg = findVisualPlaywrightConfig(join("apps/web", "tests", "visual"));
		expect(cfg).toBe(join("apps/web", "tests", "visual", "playwright.visual.config.ts"));
	});

	test("falls back to app root when no inner config", () => {
		workDir = copyFixture("split-layout");
		process.chdir(workDir);
		// detectTestDirs uses inner-first then fallback to app root.
		const entries = detectTestDirs("apps/web");
		expect(entries[1].configFile).toBe(join("apps/web", "playwright.visual.config.ts"));
	});

	test("returns null when no visual config exists", () => {
		workDir = mkdtempSync(join(tmpdir(), "surfaces-novc-"));
		mkdirSync(workDir, { recursive: true });
		process.chdir(workDir);
		expect(findVisualPlaywrightConfig(".")).toBeNull();
	});
});

describe("detectSurfaces() — split layouts", () => {
	test("apps/* split layout emits 2 surfaces with correct ids", () => {
		workDir = copyFixture("split-layout");
		process.chdir(workDir);
		const warnSpy = mock(() => {});
		const original = console.warn;
		console.warn = warnSpy;
		try {
			const surfaces = detectSurfaces();
			expect(surfaces.length).toBe(2);
			expect(surfaces[0].id).toBe("web");
			expect(surfaces[0].testDir).toBe(join("apps/web", "tests", "e2e"));
			expect(surfaces[0].runnerConfig).toBe(join("apps/web", "playwright.config.ts"));
			expect(surfaces[1].id).toBe("web-visual");
			expect(surfaces[1].testDir).toBe(join("apps/web", "tests", "visual"));
			expect(surfaces[1].runnerConfig).toBe(
				join("apps/web", "playwright.visual.config.ts"),
			);
			// Warning emitted with hint to migrate-visual-tests.js
			expect(warnSpy).toHaveBeenCalled();
			const allWarnText = warnSpy.mock.calls.map((c) => c.join(" ")).join("\n");
			expect(allWarnText).toContain("migrate-visual-tests.js");
		} finally {
			console.warn = original;
		}
	});

	test("monorepo split: 2 apps each split → 4 surfaces in interleaved order", () => {
		workDir = copyFixture("monorepo-split");
		process.chdir(workDir);
		const original = console.warn;
		console.warn = () => {};
		try {
			const surfaces = detectSurfaces();
			const ids = surfaces.map((s) => s.id);
			expect(ids.length).toBe(4);
			// App-interleaved order (AC-008): each app's e2e is immediately followed by its visual sibling.
			// readdirSync order is filesystem-dependent — we verify the interleaving invariant, not a fixed permutation.
			expect(new Set(ids)).toEqual(
				new Set(["dashboard", "dashboard-visual", "web", "web-visual"]),
			);
			expect(ids.indexOf("dashboard-visual")).toBe(ids.indexOf("dashboard") + 1);
			expect(ids.indexOf("web-visual")).toBe(ids.indexOf("web") + 1);
		} finally {
			console.warn = original;
		}
	});

	test("mixed monorepo: one app split, one consolidated → 3 surfaces", () => {
		workDir = mkdtempSync(join(tmpdir(), "surfaces-mixed-"));
		mkdirSync(join(workDir, "apps/web/tests/e2e"), { recursive: true });
		mkdirSync(join(workDir, "apps/web/tests/visual"), { recursive: true });
		writeFileSync(
			join(workDir, "apps/web/package.json"),
			JSON.stringify({ name: "web", dependencies: { react: "^18.0.0" } }),
		);
		writeFileSync(join(workDir, "apps/web/playwright.config.ts"), "export default {};\n");
		writeFileSync(
			join(workDir, "apps/web/playwright.visual.config.ts"),
			"export default {};\n",
		);
		mkdirSync(join(workDir, "apps/mobile/tests/e2e"), { recursive: true });
		writeFileSync(
			join(workDir, "apps/mobile/package.json"),
			JSON.stringify({ name: "mobile", dependencies: { react: "^18.0.0" } }),
		);
		writeFileSync(
			join(workDir, "apps/mobile/playwright.config.ts"),
			"export default {};\n",
		);
		process.chdir(workDir);
		const original = console.warn;
		console.warn = () => {};
		try {
			const surfaces = detectSurfaces();
			const ids = surfaces.map((s) => s.id);
			expect(ids.length).toBe(3);
			expect(new Set(ids)).toEqual(new Set(["mobile", "web", "web-visual"]));
			expect(ids.indexOf("web-visual")).toBe(ids.indexOf("web") + 1);
		} finally {
			console.warn = original;
		}
	});

	test("collision: apps/web and apps/web-visual both exist → web visual surface uses -v2 suffix", () => {
		workDir = mkdtempSync(join(tmpdir(), "surfaces-collision-"));
		mkdirSync(join(workDir, "apps/web/tests/e2e"), { recursive: true });
		mkdirSync(join(workDir, "apps/web/tests/visual"), { recursive: true });
		writeFileSync(
			join(workDir, "apps/web/package.json"),
			JSON.stringify({ name: "web", dependencies: { react: "^18.0.0" } }),
		);
		writeFileSync(join(workDir, "apps/web/playwright.config.ts"), "export default {};\n");
		writeFileSync(
			join(workDir, "apps/web/playwright.visual.config.ts"),
			"export default {};\n",
		);
		mkdirSync(join(workDir, "apps/web-visual/tests/e2e"), { recursive: true });
		writeFileSync(
			join(workDir, "apps/web-visual/package.json"),
			JSON.stringify({ name: "web-visual", dependencies: { react: "^18.0.0" } }),
		);
		writeFileSync(
			join(workDir, "apps/web-visual/playwright.config.ts"),
			"export default {};\n",
		);
		process.chdir(workDir);
		const original = console.warn;
		console.warn = () => {};
		try {
			const surfaces = detectSurfaces();
			const ids = surfaces.map((s) => s.id);
			expect(ids).toContain("web");
			expect(ids).toContain("web-visual"); // for the apps/web-visual app dir e2e
			expect(ids).toContain("web-visual-v2"); // collision-resolved id for web's visual
		} finally {
			console.warn = original;
		}
	});

	test("regression: only tests/e2e → exactly 1 surface, no -visual suffix", () => {
		workDir = copyFixture("single-surface");
		process.chdir(workDir);
		const surfaces = detectSurfaces();
		expect(surfaces.length).toBe(1);
		expect(surfaces[0].id).toBe("web");
		expect(surfaces.some((s) => s.id.endsWith("-visual"))).toBe(false);
	});

	test("packages/ branch: split layout → 2 surfaces", () => {
		workDir = mkdtempSync(join(tmpdir(), "surfaces-pkg-"));
		mkdirSync(join(workDir, "packages/ui/tests/e2e"), { recursive: true });
		mkdirSync(join(workDir, "packages/ui/tests/visual"), { recursive: true });
		writeFileSync(
			join(workDir, "packages/ui/package.json"),
			JSON.stringify({ name: "ui", dependencies: { react: "^18.0.0" } }),
		);
		writeFileSync(
			join(workDir, "packages/ui/playwright.config.ts"),
			"export default {};\n",
		);
		writeFileSync(
			join(workDir, "packages/ui/playwright.visual.config.ts"),
			"export default {};\n",
		);
		process.chdir(workDir);
		const original = console.warn;
		console.warn = () => {};
		try {
			const surfaces = detectSurfaces();
			const ids = surfaces.map((s) => s.id);
			expect(ids).toEqual(["ui", "ui-visual"]);
		} finally {
			console.warn = original;
		}
	});

	test("frontend/ branch: split layout → 2 surfaces", () => {
		workDir = mkdtempSync(join(tmpdir(), "surfaces-front-"));
		mkdirSync(join(workDir, "frontend/tests/e2e"), { recursive: true });
		mkdirSync(join(workDir, "frontend/tests/visual"), { recursive: true });
		writeFileSync(
			join(workDir, "frontend/package.json"),
			JSON.stringify({ name: "frontend", dependencies: { react: "^18.0.0" } }),
		);
		writeFileSync(
			join(workDir, "frontend/playwright.config.ts"),
			"export default {};\n",
		);
		writeFileSync(
			join(workDir, "frontend/playwright.visual.config.ts"),
			"export default {};\n",
		);
		process.chdir(workDir);
		const original = console.warn;
		console.warn = () => {};
		try {
			const surfaces = detectSurfaces();
			const ids = surfaces.map((s) => s.id);
			expect(ids).toEqual(["frontend", "frontend-visual"]);
		} finally {
			console.warn = original;
		}
	});

	test("root fallback: split layout at root → 2 surfaces (default + default-visual)", () => {
		workDir = mkdtempSync(join(tmpdir(), "surfaces-root-"));
		mkdirSync(join(workDir, "tests/e2e"), { recursive: true });
		mkdirSync(join(workDir, "tests/visual"), { recursive: true });
		writeFileSync(
			join(workDir, "package.json"),
			JSON.stringify({ name: "rootapp", dependencies: { react: "^18.0.0" } }),
		);
		writeFileSync(join(workDir, "playwright.config.ts"), "export default {};\n");
		writeFileSync(join(workDir, "playwright.visual.config.ts"), "export default {};\n");
		process.chdir(workDir);
		const original = console.warn;
		console.warn = () => {};
		try {
			const surfaces = detectSurfaces();
			const ids = surfaces.map((s) => s.id);
			expect(ids).toEqual(["default", "default-visual"]);
		} finally {
			console.warn = original;
		}
	});
});

describe("--migrate-surfaces flag (CLI integration)", () => {
	function runScript(args, cwd) {
		const proc = Bun.spawnSync(["node", SCRIPT_PATH, ...args], {
			cwd,
			env: { ...process.env },
		});
		return {
			stdout: proc.stdout.toString(),
			stderr: proc.stderr.toString(),
			exitCode: proc.exitCode,
		};
	}

	test("appends missing visual surface preserving existing entries byte-for-byte", () => {
		workDir = copyFixture("legacy-manifest");
		const yamlPath = join(workDir, ".specs", "surfaces.yaml");
		const before = readFileSync(yamlPath, "utf-8");
		const result = runScript(["--migrate-surfaces"], workDir);
		expect(result.exitCode).toBe(0);
		const after = readFileSync(yamlPath, "utf-8");
		// Prefix (before content) is preserved byte-for-byte
		expect(after.startsWith(before)).toBe(true);
		// New visual entry appended
		expect(after).toContain("id: web-visual");
		expect(after).toContain(join("apps/web", "tests", "visual"));
	});

	test("idempotent: no-op when manifest already contains visual surface", () => {
		workDir = copyFixture("legacy-manifest");
		const yamlPath = join(workDir, ".specs", "surfaces.yaml");
		// First run: appends the visual entry.
		runScript(["--migrate-surfaces"], workDir);
		const afterFirst = readFileSync(yamlPath, "utf-8");
		// Second run: must be byte-for-byte identical.
		const result = runScript(["--migrate-surfaces"], workDir);
		expect(result.exitCode).toBe(0);
		expect(result.stdout).toContain("No new surfaces detected");
		const afterSecond = readFileSync(yamlPath, "utf-8");
		expect(afterSecond).toBe(afterFirst);
	});

	test("--migrate-surfaces + --dry-run does not write file", () => {
		workDir = copyFixture("legacy-manifest");
		const yamlPath = join(workDir, ".specs", "surfaces.yaml");
		const before = readFileSync(yamlPath, "utf-8");
		const result = runScript(["--migrate-surfaces", "--dry-run"], workDir);
		expect(result.exitCode).toBe(0);
		const after = readFileSync(yamlPath, "utf-8");
		expect(after).toBe(before);
		expect(result.stdout).toContain("web-visual");
	});

	test("--migrate-surfaces + --force: full overwrite (force wins)", () => {
		workDir = copyFixture("legacy-manifest");
		const yamlPath = join(workDir, ".specs", "surfaces.yaml");
		const result = runScript(["--migrate-surfaces", "--force"], workDir);
		expect(result.exitCode).toBe(0);
		const after = readFileSync(yamlPath, "utf-8");
		// Custom name "Main Web App" was a manual edit; --force regenerates from scratch and discards it.
		expect(after).not.toContain("Main Web App");
		expect(after).toContain("id: web");
		expect(after).toContain("id: web-visual");
	});

	test("preserves user-edited custom name field on additive migrate", () => {
		workDir = copyFixture("legacy-manifest");
		const yamlPath = join(workDir, ".specs", "surfaces.yaml");
		runScript(["--migrate-surfaces"], workDir);
		const after = readFileSync(yamlPath, "utf-8");
		expect(after).toContain("name: Main Web App");
	});

	test("preserves comments in existing manifest", () => {
		workDir = copyFixture("legacy-manifest");
		const yamlPath = join(workDir, ".specs", "surfaces.yaml");
		const original = readFileSync(yamlPath, "utf-8");
		expect(original).toContain("# Auto-generated by LiveSpec");
		runScript(["--migrate-surfaces"], workDir);
		const after = readFileSync(yamlPath, "utf-8");
		expect(after).toContain("# Auto-generated by LiveSpec");
		expect(after).toContain("# Edit to match your project structure");
	});
});

describe("--dry-run (multi-surface output)", () => {
	test("--dry-run prints multi-surface output for split layout", () => {
		workDir = copyFixture("split-layout");
		const proc = Bun.spawnSync(["node", SCRIPT_PATH, "--dry-run"], {
			cwd: workDir,
		});
		expect(proc.exitCode).toBe(0);
		const stdout = proc.stdout.toString();
		expect(stdout).toContain("[web]");
		expect(stdout).toContain("[web-visual]");
	});
});

// @spec FR-004, FR-005, FR-007: pbxproj parser tests — .specs/features/037-test-multi-runner-integration/spec.md#fr-004
describe("pbxproj parser (Feature 037)", () => {
	test("parses ASCII pbxproj and classifies watchOS targets", async () => {
		const pbxMod = await import(join(REPO_ROOT, "scripts", "lib", "pbxproj.js"));
		const ascii = `// !$*UTF8*$!\n{\n\trootObject = ABC;\n\tobjects = {\n/* Begin PBXNativeTarget section */\n\t\tT1 /* AppTests */ = {isa = PBXNativeTarget; name = AppTests; productType = "com.apple.product-type.bundle.unit-test"; };\n\t\tT2 /* AppUITests */ = {isa = PBXNativeTarget; name = AppUITests; productType = "com.apple.product-type.bundle.ui-testing"; };\n\t\tT3 /* AppWatchTests */ = {isa = PBXNativeTarget; name = AppWatchTests; productType = "com.apple.product-type.bundle.unit-test"; };\n/* End PBXNativeTarget section */\n\t};\n}\n`;
		const targets = pbxMod.parsePbxprojContents(ascii);
		expect(targets.length).toBe(3);
		const names = targets.map((t) => t.name).sort();
		expect(names).toEqual(["AppTests", "AppUITests", "AppWatchTests"]);
	});

	test("classifies watchOS, widget, ui, and unit targets", async () => {
		const { classifyTestTarget } = await import(join(REPO_ROOT, "scripts", "lib", "pbxproj.js"));
		expect(classifyTestTarget("AppWatchTests", "com.apple.product-type.bundle.unit-test").platform).toBe("watchos");
		expect(classifyTestTarget("AppWidgetTests", "com.apple.product-type.bundle.unit-test").kind).toBe("widget");
		expect(classifyTestTarget("AppUITests", "com.apple.product-type.bundle.ui-testing").kind).toBe("ui");
		expect(classifyTestTarget("AppTests", "com.apple.product-type.bundle.unit-test").kind).toBe("unit");
	});

	test("kebabize converts CamelCase target names", async () => {
		const { kebabize } = await import(join(REPO_ROOT, "scripts", "lib", "pbxproj.js"));
		expect(kebabize("AppWatchTests")).toBe("app-watch-tests");
		expect(kebabize("StraptUITests")).toBe("strapt-uitests");
		expect(kebabize("App_Tests")).toBe("app-tests");
	});

	test("enumerateAndFallback returns directory-globbed targets when pbxproj missing", async () => {
		const { enumerateAndFallback } = await import(join(REPO_ROOT, "scripts", "lib", "pbxproj.js"));
		const tmp = mkdtempSync(join(tmpdir(), "pbx-fallback-"));
		mkdirSync(join(tmp, "App.xcodeproj"));
		mkdirSync(join(tmp, "AppTests"));
		mkdirSync(join(tmp, "AppUITests"));
		mkdirSync(join(tmp, "AppWatchTests"));
		const result = enumerateAndFallback(join(tmp, "App.xcodeproj"), tmp);
		const names = result.targets.map((t) => t.name).sort();
		expect(names).toEqual(["AppTests", "AppUITests", "AppWatchTests"]);
		expect(result.warnings.length).toBeGreaterThan(0);
		rmSync(tmp, { recursive: true, force: true });
	});

	test("orphan target (declared but directory missing) is omitted with warning", async () => {
		const { enumerateAndFallback } = await import(join(REPO_ROOT, "scripts", "lib", "pbxproj.js"));
		const tmp = mkdtempSync(join(tmpdir(), "pbx-orphan-"));
		const xcodeproj = join(tmp, "App.xcodeproj");
		mkdirSync(xcodeproj);
		writeFileSync(
			join(xcodeproj, "project.pbxproj"),
			`// !$*UTF8*$!\n{\n\tobjects = {\n/* Begin PBXNativeTarget section */\n\t\tT1 = {isa = PBXNativeTarget; name = AppTests; productType = "com.apple.product-type.bundle.unit-test"; };\n/* End PBXNativeTarget section */\n\t};\n}\n`,
		);
		// Note: AppTests directory is intentionally NOT created
		const result = enumerateAndFallback(xcodeproj, tmp);
		expect(result.targets.length).toBe(0);
		expect(result.warnings.some((w) => w.includes("AppTests") && w.includes("not found"))).toBe(true);
		rmSync(tmp, { recursive: true, force: true });
	});
});

// @spec FR-002: scheme extraction — .specs/features/038-runner-config-wiring/spec.md#fr-002
describe("scheme extractor (Feature 038)", () => {
	test("listSharedSchemes returns sorted scheme names", () => {
		const tmp = mkdtempSync(join(tmpdir(), "schemes-"));
		const xcodeproj = join(tmp, "App.xcodeproj");
		const schemesDir = join(xcodeproj, "xcshareddata", "xcschemes");
		mkdirSync(schemesDir, { recursive: true });
		writeFileSync(join(schemesDir, "App.xcscheme"), "<Scheme/>");
		writeFileSync(join(schemesDir, "App Watch App.xcscheme"), "<Scheme/>");
		const schemes = listSharedSchemes(xcodeproj);
		expect(schemes).toEqual(["App", "App Watch App"]);
		rmSync(tmp, { recursive: true, force: true });
	});

	test("listSharedSchemes returns empty array when no schemes shared", () => {
		const tmp = mkdtempSync(join(tmpdir(), "no-schemes-"));
		const xcodeproj = join(tmp, "App.xcodeproj");
		mkdirSync(xcodeproj);
		expect(listSharedSchemes(xcodeproj)).toEqual([]);
		rmSync(tmp, { recursive: true, force: true });
	});

	test("pickSchemeForPlatform picks watch scheme for watchos", () => {
		const result = pickSchemeForPlatform(["App", "App Watch App"], "watchos");
		expect(result).toBe("App Watch App");
	});

	test("pickSchemeForPlatform picks non-watch scheme for ios", () => {
		const result = pickSchemeForPlatform(["App", "App Watch App"], "ios");
		expect(result).toBe("App");
	});

	test("pickSchemeForPlatform returns null when watchos has no watch scheme", () => {
		const result = pickSchemeForPlatform(["App"], "watchos");
		expect(result).toBeNull();
	});
});

// @spec FR-001: runnerConfig wiring — .specs/features/038-runner-config-wiring/spec.md#fr-001
describe("buildXcuitestRunnerConfig (Feature 038)", () => {
	test("populates project + destination + scheme from xcshareddata", () => {
		const tmp = mkdtempSync(join(tmpdir(), "rc-xcuitest-"));
		const xcodeproj = join(tmp, "STRAPT.xcodeproj");
		const schemesDir = join(xcodeproj, "xcshareddata", "xcschemes");
		mkdirSync(schemesDir, { recursive: true });
		writeFileSync(join(schemesDir, "STRAPT.xcscheme"), "<Scheme/>");
		writeFileSync(join(schemesDir, "STRAPT Watch App.xcscheme"), "<Scheme/>");
		const config = buildXcuitestRunnerConfig(xcodeproj, "ios");
		expect(config.scheme).toBe("STRAPT");
		expect(config.destination).toBe("platform=iOS Simulator,name=iPhone 16");
		expect(config.project).toContain("STRAPT.xcodeproj");
		const watchConfig = buildXcuitestRunnerConfig(xcodeproj, "watchos");
		expect(watchConfig.scheme).toBe("STRAPT Watch App");
		expect(watchConfig.destination).toContain("watchOS Simulator");
		rmSync(tmp, { recursive: true, force: true });
	});

	test("returns config without scheme when no schemes are shared", () => {
		const tmp = mkdtempSync(join(tmpdir(), "rc-no-schemes-"));
		const xcodeproj = join(tmp, "App.xcodeproj");
		mkdirSync(xcodeproj);
		const config = buildXcuitestRunnerConfig(xcodeproj, "ios");
		expect(config.scheme).toBeUndefined();
		expect(config.destination).toBeDefined();
		expect(config.project).toContain("App.xcodeproj");
		rmSync(tmp, { recursive: true, force: true });
	});
});

describe("buildMaestroRunnerConfig (Feature 038)", () => {
	test("returns flowsDir + platform=android", () => {
		const config = buildMaestroRunnerConfig("maestro");
		expect(config.flowsDir).toBe("maestro");
		expect(config.platform).toBe("android");
	});
});

// @spec FR-005: nested YAML output — .specs/features/038-runner-config-wiring/spec.md#fr-005
describe("toYaml emits nested runnerConfig (Feature 038)", () => {
	test("object runnerConfig becomes nested YAML map", async () => {
		const { toYaml } = mod;
		const yaml = toYaml([
			{
				id: "ios",
				name: "STRAPT",
				path: ".",
				testDir: "STRAPTTests",
				runner: "xcuitest",
				platform: "ios",
				runnerConfig: {
					project: "STRAPT.xcodeproj",
					scheme: "STRAPT",
					destination: "platform=iOS Simulator,name=iPhone 16",
				},
			},
		]);
		expect(yaml).toContain("    runnerConfig:");
		expect(yaml).toContain("      project: STRAPT.xcodeproj");
		expect(yaml).toContain("      scheme: STRAPT");
		// Destination contains commas/equals → must be quoted
		expect(yaml).toContain('      destination: "platform=iOS Simulator,name=iPhone 16"');
	});

	test("string runnerConfig stays single-line (legacy form)", async () => {
		const { toYaml } = mod;
		const yaml = toYaml([
			{
				id: "web",
				name: "Web",
				path: "apps/web",
				testDir: "apps/web/tests/e2e",
				runner: "playwright",
				runnerConfig: "apps/web/playwright.config.ts",
			},
		]);
		expect(yaml).toContain("    runnerConfig: apps/web/playwright.config.ts");
		// Must NOT have nested form
		expect(yaml).not.toContain("\n      ");
	});
});
