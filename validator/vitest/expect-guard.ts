/** Guard alternate expect APIs without materializing Vitest's lazy test expectation. */
import { errors } from "./trace-state";

const guarded = new WeakSet<object>();

/** Reject unsupported matcher registration and alternate expectation paths on first access. */
export const guardExpectation = (expectation: unknown): void => {
	if (typeof expectation !== "function")
		throw new Error("Unsupported test expectation value");
	if (guarded.has(expectation)) return;
	guarded.add(expectation);
	for (const name of ["extend", "poll", "soft", "addEqualityTesters"]) {
		Object.defineProperty(expectation, name, {
			value: () => {
				errors.push(`Unsupported expect.${name}`);
				throw new Error(`Unsupported expect.${name}`);
			},
		});
	}
};
