/** Evaluate the original local Vite configuration before overlaying owned observation. */
import { createHash } from "node:crypto";
import { readFileSync, realpathSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { isAbsolute, join, relative, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import type { ConfigEnv } from "vite";
import type { UserConfig } from "vitest/config";
import { instrumentAsyncConsumption } from "./async-source";
import { required } from "./trace-state";

const root = required("LIVESPEC_VITEST_ROOT");
const localRequire = createRequire(`${root}/package.json`);
// Import-only ESM entry avoids Vite's deprecated CommonJS bridge.
const vitePath = localRequire
	.resolve("vite")
	.replace(/index\.cjs$/, "dist/node/index.js");

const tracked: Record<string, string> = {};
// @spec FR-003: Bind actual loaded config and setup dependencies before execution — .specs/features/096-node-vitest-execution/spec.md#fr-003
const bindInput = (input: string): void => {
	const path = realpathSync(input);
	const local = relative(required("LIVESPEC_EXECUTION_PROJECT"), path)
		.split("\\")
		.join("/");
	if (local.startsWith("..") || isAbsolute(local))
		throw new Error(`Unsupported external input: ${input}`);
	if (local.includes("node_modules/")) return;
	tracked[local] ??= createHash("sha256")
		.update(readFileSync(path))
		.digest("hex");
	writeFileSync(required("LIVESPEC_VITEST_INPUTS"), JSON.stringify(tracked), {
		mode: 0o600,
	});
};
const asset = (name: string): string =>
	join(required("LIVESPEC_VITEST_ASSETS"), name);
const timeout = (name: string, existing: number | undefined): number => {
	const limit = Number(required(name));
	if (!Number.isFinite(limit) || limit <= 0) throw new Error(`Invalid ${name}`);
	return Math.min(existing ?? limit, limit);
};

/** Keep root/config environment and all consumer fields except the owned instrumentation. */
export default async (environment: ConfigEnv): Promise<UserConfig> => {
	const { loadConfigFromFile, parseAst } = (await import(
		pathToFileURL(vitePath).href
	)) as typeof import("vite");
	// MagicString is part of the governed Vitest production dependency closure, not a global tool.
	const { default: StringEditor } = (await import(
		localRequire.resolve("magic-string")
	)) as typeof import("magic-string");
	const original = process.env.LIVESPEC_VITEST_ORIGINAL_CONFIG;
	const loaded = original
		? await loadConfigFromFile(environment, original, root)
		: null;
	for (const dependency of loaded?.dependencies ?? []) {
		bindInput(dependency);
		const local = relative(
			required("LIVESPEC_EXECUTION_PROJECT"),
			realpathSync(dependency),
		);
		if (local.startsWith("..") || isAbsolute(local))
			throw new Error(`Unsupported external config dependency: ${dependency}`);
	}
	const config: UserConfig = loaded?.config ?? {};
	if (config.root && resolve(root, config.root) !== root)
		throw new Error("Unsupported config root override");
	const test = config.test ?? {};
	if (
		test.runner ||
		test.reporters ||
		test.workspace ||
		test.browser?.enabled ||
		test.pool === "vmThreads" ||
		test.pool === "vmForks"
	)
		throw new Error(
			"Unsupported custom runner/reporter/workspace/browser/pool configuration",
		);
	if (config.plugins?.length) {
		// Config plugins can replace owned runner/reporter after this overlay; reject lifecycle hooks.
		for (const plugin of config.plugins as unknown[]) {
			if (
				plugin &&
				typeof plugin === "object" &&
				("config" in plugin || "configResolved" in plugin)
			)
				throw new Error("Unsupported configuration lifecycle plugin");
		}
	}
	if (original) bindInput(original);
	writeFileSync(required("LIVESPEC_VITEST_INPUTS"), JSON.stringify(tracked), {
		mode: 0o600,
	});
	return {
		...config,
		plugins: [
			...(config.plugins ?? []),
			{
				name: "livespec-async-source",
				enforce: "post",
				transform(source: string, id: string) {
					const input = id.split("?")[0];
					if (
						!isAbsolute(input) ||
						input.includes("/node_modules/") ||
						input.includes("/validator/vitest/")
					)
						return null;
					return instrumentAsyncConsumption(
						source,
						id,
						parseAst,
						StringEditor,
						asset("async-consumption.ts"),
					);
				},
			},
			{
				name: "livespec-bind-inputs",
				enforce: "pre",
				transform(_source: string, id: string) {
					const input = id.split("?")[0];
					if (
						isAbsolute(input) &&
						!input.includes("/node_modules/") &&
						!input.includes("/validator/vitest/")
					)
						bindInput(input);
					return null;
				},
			},
		],
		root: config.root ?? root,
		test: {
			...test,
			runner: asset("runner.ts"),
			reporters: [
				asset("reporter.ts"),
				["junit", { outputFile: required("LIVESPEC_VITEST_JUNIT") }],
			],
			testTimeout: timeout("LIVESPEC_VITEST_TEST_TIMEOUT", test.testTimeout),
			hookTimeout: timeout("LIVESPEC_VITEST_HOOK_TIMEOUT", test.hookTimeout),
		},
	};
};
