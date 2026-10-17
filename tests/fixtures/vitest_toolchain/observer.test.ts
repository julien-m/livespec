/** Genuine local matcher fixture for observation-purpose and generic-goal proof. */
import { expect, test } from "vitest";

test("observes a dispatched local built-in matcher", () => {
	expect(2 + 3).toBe(5);
});
