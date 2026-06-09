// LiveSpec traceability anchors
// @spec(AC-004)
// @spec(AC-005)
// @spec(FR-002)

// @spec FR-004: enumerate Xcode test targets — .specs/features/037-test-multi-runner-integration/spec.md#fr-004
// @spec FR-005: fallback when pbxproj parse fails — .specs/features/037-test-multi-runner-integration/spec.md#fr-005
// @spec FR-007: watch/widget classification — .specs/features/037-test-multi-runner-integration/spec.md#fr-007
// @spec FR-002: extract Xcode schemes for runnerConfig — .specs/features/038-runner-config-wiring/spec.md#fr-002

import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, basename } from "node:path";

/**
 * List shared scheme names declared under <xcodeproj>/xcshareddata/xcschemes/*.xcscheme.
 * The scheme name is the file stem; this is exactly what `xcodebuild -scheme` accepts.
 *
 * @param {string} xcodeprojDir Absolute path to the `.xcodeproj` directory
 * @returns {string[]} Sorted scheme names; empty array when none are shared
 */
export function listSharedSchemes(xcodeprojDir) {
	const schemesDir = join(xcodeprojDir, "xcshareddata", "xcschemes");
	if (!existsSync(schemesDir)) return [];
	try {
		return readdirSync(schemesDir)
			.filter((name) => name.endsWith(".xcscheme"))
			.map((name) => name.replace(/\.xcscheme$/, ""))
			.sort();
	} catch {
		return [];
	}
}

/**
 * Pick the most likely scheme for a given platform from a list of shared schemes.
 * iOS prefers names without "watch"; watchOS requires "watch" in the name.
 *
 * @param {string[]} schemes
 * @param {"ios"|"watchos"|undefined} platform
 * @returns {string | null}
 */
export function pickSchemeForPlatform(schemes, platform) {
	if (schemes.length === 0) return null;
	if (platform === "watchos") {
		const match = schemes.find((s) => /watch/i.test(s));
		return match ?? null;
	}
	if (platform === "ios") {
		const match = schemes.find((s) => !/watch/i.test(s));
		return match ?? schemes[0];
	}
	return schemes[0];
}

const TEST_PRODUCT_TYPES = new Set([
	"com.apple.product-type.bundle.unit-test",
	"com.apple.product-type.bundle.ui-testing",
]);

/**
 * Classify a target name into platform/kind.
 * @param {string} name
 * @param {string} productType
 * @returns {{ platform: "ios"|"watchos", kind: "unit"|"ui"|"widget" }}
 */
export function classifyTestTarget(name, productType) {
	const lower = name.toLowerCase();
	// Platform: derived from name (watch suffix → watchOS, otherwise iOS).
	const platform = /watch/i.test(name) ? "watchos" : "ios";
	// Widgets are a special kind regardless of productType.
	if (/widget.*tests?$/i.test(name)) {
		return { platform, kind: "widget" };
	}
	// Kind: trust productType first — it is the only authoritative signal that
	// distinguishes UI Testing Bundles (which capture screenshots) from plain
	// unit-test bundles (which do not). Name-based heuristics are a fallback
	// for malformed pbxproj where productType is missing.
	if (productType === "com.apple.product-type.bundle.ui-testing") {
		return { platform, kind: "ui" };
	}
	if (productType === "com.apple.product-type.bundle.unit-test") {
		return { platform, kind: "unit" };
	}
	if (/uitests?$/i.test(name)) {
		return { platform, kind: "ui" };
	}
	if (/tests?$/i.test(lower)) {
		return { platform, kind: "unit" };
	}
	return { platform, kind: "unit" };
}

/**
 * Convert a target name into a kebab-case surface id.
 * @param {string} name
 * @returns {string}
 */
export function kebabize(name) {
	return name
		.replace(/([a-z0-9])([A-Z])/g, "$1-$2")
		.replace(/[_\s]+/g, "-")
		.toLowerCase();
}

/**
 * Parse the legacy ASCII plist variant of project.pbxproj using regex on the
 * structures we need (PBXNativeTarget blocks). This is intentionally light —
 * it only extracts target name and productType, which is what `enumerateXcodeTestTargets`
 * needs. JSON variants (Xcode 16+) are auto-detected and parsed via JSON.parse.
 *
 * @param {string} contents
 * @returns {Array<{ name: string, productType: string }>}
 */
export function parsePbxprojContents(contents) {
	const trimmed = contents.trimStart();

	// Xcode 16+ JSON variant
	if (trimmed.startsWith("{") && trimmed.includes("\"objects\"")) {
		try {
			const parsed = JSON.parse(trimmed);
			const objects = parsed.objects || {};
			/** @type {Array<{ name: string, productType: string }>} */
			const targets = [];
			for (const obj of Object.values(objects)) {
				if (obj && obj.isa === "PBXNativeTarget" && typeof obj.name === "string") {
					targets.push({ name: obj.name, productType: String(obj.productType || "") });
				}
			}
			return targets;
		} catch {
			// Fall through to ASCII parsing
		}
	}

	// Legacy ASCII plist variant — extract PBXNativeTarget blocks
	const blockRegex = /\/\* Begin PBXNativeTarget section \*\/([\s\S]*?)\/\* End PBXNativeTarget section \*\//;
	const sectionMatch = blockRegex.exec(contents);
	if (!sectionMatch) return [];
	const section = sectionMatch[1];

	/** @type {Array<{ name: string, productType: string }>} */
	const out = [];
	// Each target block looks like:
	//   ABCDEF1234 /* AppTests */ = { isa = PBXNativeTarget; ... name = AppTests; productType = "com.apple.product-type.bundle.unit-test"; ... };
	const targetRegex = /=\s*\{[^}]*?isa\s*=\s*PBXNativeTarget[^}]*?\}/g;
	let match;
	while ((match = targetRegex.exec(section)) !== null) {
		const block = match[0];
		const nameMatch = /\bname\s*=\s*"?([A-Za-z0-9_\-]+)"?\s*;/.exec(block);
		const ptMatch = /\bproductType\s*=\s*"([^"]+)"/.exec(block);
		if (nameMatch && ptMatch) {
			out.push({ name: nameMatch[1], productType: ptMatch[1] });
		}
	}
	return out;
}

/**
 * Enumerate Xcode test targets from a project.pbxproj file.
 *
 * @param {string} xcodeprojDir Absolute path to the `.xcodeproj` directory
 * @param {string} appPath The parent directory used to resolve target source dirs
 * @returns {{ targets: Array<{name:string, productType:string, kind:string, platform:string, directory:string}>, fallback: boolean, warning: string | null }}
 */
export function enumerateXcodeTestTargets(xcodeprojDir, appPath) {
	const pbxPath = join(xcodeprojDir, "project.pbxproj");
	if (!existsSync(pbxPath)) {
		return {
			targets: [],
			fallback: true,
			warning: `project.pbxproj not found in ${xcodeprojDir}`,
		};
	}

	let contents;
	try {
		contents = readFileSync(pbxPath, "utf8");
	} catch (err) {
		return {
			targets: [],
			fallback: true,
			warning: `Could not read ${pbxPath} (${err.message}) — falling back to directory heuristics`,
		};
	}

	let raw;
	try {
		raw = parsePbxprojContents(contents);
	} catch (err) {
		return {
			targets: [],
			fallback: true,
			warning: `Could not parse ${basename(xcodeprojDir)} — falling back to directory heuristics (${err.message})`,
		};
	}

	const testTargets = raw.filter((t) => TEST_PRODUCT_TYPES.has(t.productType));
	if (testTargets.length === 0) {
		return { targets: [], fallback: false, warning: null };
	}

	const enriched = testTargets.map((t) => {
		const cls = classifyTestTarget(t.name, t.productType);
		return {
			name: t.name,
			productType: t.productType,
			kind: cls.kind,
			platform: cls.platform,
			directory: resolveTargetDirectory(appPath, t.name),
		};
	});

	return { targets: enriched, fallback: false, warning: null };
}

/**
 * Resolve the on-disk directory for an Xcode target. Xcode does not encode
 * the source path inside `PBXNativeTarget`, so we probe the common locations
 * used in the wild: `<root>/<Target>/`, `<root>/Tests/<Target>/`,
 * `<root>/Sources/<Target>/`, `<root>/UITests/<Target>/`.
 *
 * @param {string} appPath
 * @param {string} targetName
 * @returns {string}
 */
function resolveTargetDirectory(appPath, targetName) {
	const candidates = [
		join(appPath, targetName),
		join(appPath, "Tests", targetName),
		join(appPath, "Sources", targetName),
		join(appPath, "UITests", targetName),
	];
	for (const candidate of candidates) {
		if (existsSync(candidate)) return candidate;
	}
	// Fall back to the Xcode-standard layout so callers can still report a
	// canonical "expected here" path in their warning.
	return join(appPath, targetName);
}

/**
 * Fallback: glob sibling directories matching common Xcode test naming.
 *
 * @param {string} appPath
 * @returns {Array<{name:string, productType:string, kind:string, platform:string, directory:string}>}
 */
export function fallbackGlobTestDirs(appPath) {
	if (!existsSync(appPath)) return [];
	let entries;
	try {
		entries = readdirSync(appPath);
	} catch {
		return [];
	}
	/** @type {Array<{name:string, productType:string, kind:string, platform:string, directory:string}>} */
	const out = [];
	for (const entry of entries) {
		if (!/(?:Tests?|UITests?|WatchTests?|WatchUITests?|WidgetTests?)$/i.test(entry)) continue;
		const fullPath = join(appPath, entry);
		try {
			if (!statSync(fullPath).isDirectory()) continue;
		} catch {
			continue;
		}
		const productType = /UITests?$/i.test(entry)
			? "com.apple.product-type.bundle.ui-testing"
			: "com.apple.product-type.bundle.unit-test";
		const cls = classifyTestTarget(entry, productType);
		out.push({
			name: entry,
			productType,
			kind: cls.kind,
			platform: cls.platform,
			directory: fullPath,
		});
	}
	return out;
}

/**
 * High-level helper: enumerate test targets, falling back to globbing if pbxproj
 * cannot be parsed. Filters out targets whose source directory does not exist
 * (FR-006). Returns warnings to be logged by the caller.
 *
 * @param {string} xcodeprojDir
 * @param {string} appPath
 * @returns {{ targets: Array<{name:string, productType:string, kind:string, platform:string, directory:string}>, warnings: string[] }}
 */
export function enumerateAndFallback(xcodeprojDir, appPath) {
	/** @type {string[]} */
	const warnings = [];
	const result = enumerateXcodeTestTargets(xcodeprojDir, appPath);
	let targets = result.targets;
	if (result.warning) warnings.push(result.warning);
	// Only fall back when parsing/readability failed. A parsed project with zero
	// test targets is a real "nothing to emit" case that callers should report.
	if (result.fallback) {
		const fb = fallbackGlobTestDirs(appPath);
		if (fb.length > 0) targets = fb;
	}

	const filtered = [];
	for (const target of targets) {
		if (existsSync(target.directory)) {
			filtered.push(target);
		} else {
			warnings.push(
				`Test target ${target.name} declared in project.pbxproj but directory ${target.directory} not found — skipping`,
			);
		}
	}
	return { targets: filtered, warnings };
}
