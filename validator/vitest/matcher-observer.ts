/** Observe genuine Chai/Vitest dispatch without consuming matcher promises. */
import { createRequire } from "node:module";
import { consumeAsyncMatcher, registerAsyncMatcher } from "./async-consumption";
import { guardExpectation } from "./expect-guard";
import { matcherCallsite } from "./matcher-callsite";
import {
	errors,
	identity,
	type PendingRecord,
	records,
	required,
} from "./trace-state";

const localRequire = createRequire(
	`${required("LIVESPEC_VITEST_ROOT")}/package.json`,
);
// Absolute dynamic imports select the governed consumer installation outside our asset tree.
const { chai, expect } = (await import(
	localRequire.resolve("vitest").replace(/index\.cjs$/, "dist/index.js")
)) as typeof import("vitest");
const { getCurrentTest } = (await import(
	localRequire.resolve("@vitest/runner")
)) as typeof import("@vitest/runner");
const SUPPORTED = new Set([
	"toBe",
	"toBeTruthy",
	"toEqual",
	"toMatchObject",
	"toBeUndefined",
	"toContainEqual",
	"toHaveLength",
	"toContain",
	"toThrow",
	"toMatch",
	"toBeNull",
	"toBeGreaterThan",
	"toBeGreaterThanOrEqual",
	"toBeLessThan",
	"toHaveBeenCalledWith",
	"toHaveBeenCalled",
]);
type ChaiMethod = (this: object, ...args: unknown[]) => unknown;
interface ChaiOverrides {
	overwriteMethod(
		target: object,
		name: string,
		factory: (original: ChaiMethod) => ChaiMethod,
	): void;
	overwriteProperty(
		target: object,
		name: string,
		factory: (original: ChaiMethod) => ChaiMethod,
	): void;
}
// Chai 5 types omit the getter-super argument that its tested runtime supplies.
const overrides = chai.util as unknown as ChaiOverrides;

// @spec FR-002: Bind real matcher dispatch to its test and source — .specs/features/096-node-vitest-execution/spec.md#fr-002
const createRecord = (
	assertion: object,
	matcher: string,
	asynchronous: boolean,
): PendingRecord => {
	const task = getCurrentTest();
	if (!task || chai.util.flag(assertion, "vitest-test") !== task) {
		errors.push("Unsupported direct Chai or out-of-test matcher");
		throw new Error("Unsupported direct Chai or out-of-test matcher");
	}
	const source = matcherCallsite();
	if (source?.user) {
		const record: PendingRecord = {
			task,
			attempt: task.result?.retryCount ?? 0,
			consumed: !asynchronous,
			settled: false,
			assertion: {
				test_id: identity(task),
				path: source.path,
				line: source.line,
				assertion: `${chai.util.flag(assertion, "negate") ? ".not." : ""}${matcher}`,
				status: "passed",
			},
		};
		records.push(record);
		return record;
	}
	errors.push("Matcher source callsite is outside the governed project");
	throw new Error("Matcher source callsite is outside the governed project");
};

// @spec FR-002: Observe settlement independently of explicit await consumption — .specs/features/096-node-vitest-execution/spec.md#fr-002
const observe = (
	assertion: object,
	matcher: string,
	invoke: () => unknown,
	asynchronous: boolean,
): unknown => {
	// A framework delegation is distinct from a nested user callback with its own source frame.
	if (!matcherCallsite()?.user) return invoke();
	const record = createRecord(assertion, matcher, asynchronous);
	try {
		const returned = invoke();
		if (!asynchronous) {
			record.settled = true;
			return returned;
		}
		const native =
			record.task.type === "test" ? record.task.promises?.at(-1) : undefined;
		if (
			!native ||
			!returned ||
			typeof returned !== "object" ||
			!("then" in returned)
		)
			throw new Error("Unsupported async matcher return");
		// Native Promise observation bypasses Vitest's consumer-marking then wrapper.
		Promise.prototype.then.call(
			native,
			() => {
				record.settled = true;
			},
			() => {
				record.settled = true;
				record.assertion.status = "failed";
			},
		);
		const promise = returned as Promise<unknown>; // The native promise check above establishes the Vitest thenable boundary.
		const observed = {
			// biome-ignore lint/suspicious/noThenProperty: An explicit thenable is necessary to distinguish consumer await from framework auto-await.
			then: (fulfilled: unknown, rejected: unknown) => {
				consumeAsyncMatcher(observed);
				return Reflect.apply(promise.then, promise, [fulfilled, rejected]);
			},
			catch: promise.catch.bind(promise),
			finally: promise.finally.bind(promise),
		};
		return registerAsyncMatcher(observed, record);
	} catch (error) {
		record.settled = true;
		record.assertion.status = "failed";
		throw error;
	}
};

/** Install once per worker before importing consumer setup and tests. */
export const installObserver = (): void => {
	const internal = new Set([
		"constructor",
		"assert",
		"withTest",
		"withContext",
	]);
	const language = new Set([
		"to",
		"be",
		"been",
		"is",
		"that",
		"which",
		"and",
		"has",
		"have",
		"with",
		"at",
		"of",
		"same",
		"but",
		"does",
		"still",
		"also",
		"not",
		"resolves",
		"rejects",
		"_obj",
	]);
	for (const name of Object.getOwnPropertyNames(chai.Assertion.prototype)) {
		const descriptor = Object.getOwnPropertyDescriptor(
			chai.Assertion.prototype,
			name,
		);
		if (
			!descriptor ||
			SUPPORTED.has(name) ||
			internal.has(name) ||
			language.has(name) ||
			name.startsWith("__")
		)
			continue;
		const reject = (): void => {
			if (matcherCallsite()?.user && getCurrentTest()) {
				errors.push(`Unsupported Chai/matcher form: ${name}`);
				throw new Error(`Unsupported Chai/matcher form: ${name}`);
			}
		};
		if (typeof descriptor.value === "function")
			overrides.overwriteMethod(
				chai.Assertion.prototype,
				name,
				(original) =>
					function (this: object, ...args: unknown[]) {
						reject();
						return Reflect.apply(original, this, args);
					},
			);
		else if (descriptor.get)
			overrides.overwriteProperty(
				chai.Assertion.prototype,
				name,
				(original) =>
					function (this: object) {
						reject();
						return original.call(this);
					},
			);
	}
	for (const matcher of SUPPORTED) {
		overrides.overwriteMethod(
			chai.Assertion.prototype,
			matcher,
			(original) =>
				function (this: object, ...args: unknown[]) {
					return observe(
						this,
						matcher,
						() => Reflect.apply(original, this, args),
						false,
					);
				},
		);
	}
	for (const form of ["resolves", "rejects"]) {
		overrides.overwriteProperty(
			chai.Assertion.prototype,
			form,
			(original) =>
				function (this: object) {
					const assertion = original.call(this) as object; // Chai resolves/rejects getters return the assertion proxy.
					const proxy: object = new Proxy(assertion, {
						get(target, key, receiver) {
							const method: unknown = Reflect.get(target, key, receiver);
							// Vitest returns its inner assertion proxy for language/.not chains; retain our outer observation boundary.
							if (
								typeof method === "object" &&
								method !== null &&
								(method === target || method instanceof chai.Assertion)
							)
								return proxy;
							if (
								typeof key !== "string" ||
								!SUPPORTED.has(key) ||
								typeof method !== "function"
							)
								return method;
							return (...args: unknown[]) =>
								observe(
									target,
									key,
									() => Reflect.apply(method, target, args),
									true,
								);
						},
					});
					return proxy;
				},
		);
	}
	guardExpectation(expect);
};
