/** Connect executed await/return instrumentation to the exact owned matcher thenable. */
import type { PendingRecord } from "./trace-state";

interface AsyncEntry {
	record: PendingRecord;
	eligible: boolean;
}
interface AsyncBridge {
	register(value: object, record: PendingRecord): void;
	arm(value: object): void;
	consume(value: object): void;
}

const createBridge = (): AsyncBridge => {
	// Evidence records stay in this closure; the worker bridge exposes no lookup or mutable entry.
	const pending = new WeakMap<object, AsyncEntry>();
	return Object.freeze({
		register: (value: object, record: PendingRecord): void => {
			pending.set(value, { record, eligible: false });
		},
		arm: (value: object): void => {
			const entry = pending.get(value);
			if (entry) entry.eligible = true;
		},
		consume: (value: object): void => {
			const entry = pending.get(value);
			if (entry?.eligible) entry.record.consumed = true;
		},
	});
};
const registryKey = Symbol.for("livespec.vitest.async-consumption");
// Native runner imports and Vite's test-module graph instantiate assets separately in the same worker.
const shared = globalThis as typeof globalThis & {
	[registryKey]?: AsyncBridge;
};
shared[registryKey] ??= createBridge();
const bridge = shared[registryKey];

/** Register an owned thenable without treating promise assimilation as consumption. */
export const registerAsyncMatcher = <T extends object>(
	value: T,
	record: PendingRecord,
): T => {
	bridge.register(value, record);
	return value;
};

// @spec FR-002: Only executed direct test await/return proves consumption — .specs/features/096-node-vitest-execution/spec.md#fr-002
export const markAsyncConsumption = <T>(value: T): T => {
	if (value && (typeof value === "object" || typeof value === "function")) {
		bridge.arm(value);
	}
	return value;
};

/** Require both executed syntax authorization and actual consumption of that exact thenable. */
export const consumeAsyncMatcher = (value: object): void => {
	bridge.consume(value);
};
