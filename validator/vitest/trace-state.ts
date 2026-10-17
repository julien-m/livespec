/** Shared invocation identities and exclusive worker trace publication. */

import { randomUUID } from "node:crypto";
import { realpathSync, writeFileSync } from "node:fs";
import { isAbsolute, join, relative, sep } from "node:path";
import type { Task } from "@vitest/runner";

/** Settled matcher evidence matching the Python assertion schema. */
export interface AssertionRecord {
	test_id: string;
	path: string;
	line: number;
	assertion: string;
	status: "passed" | "failed";
}
/** A matcher attempt; consumption is independent of framework settlement. */
export interface PendingRecord {
	task: Task;
	attempt: number;
	assertion: AssertionRecord;
	consumed: boolean;
	settled: boolean;
}
export const records: PendingRecord[] = [];
export const errors: string[] = [];

/** Read a required nonempty invocation parameter. */
export const required = (name: string): string => {
	const value = process.env[name];
	if (!value) throw new Error(`Missing ${name}`);
	return value;
};
/** Only files inside the canonical observer asset directory are runner-owned. */
export const isObserverAsset = (path: string): boolean => {
	const local = relative(
		realpathSync(required("LIVESPEC_VITEST_ASSETS")),
		realpathSync(path),
	);
	return (
		local === "" ||
		(local !== ".." && !local.startsWith(`..${sep}`) && !isAbsolute(local))
	);
};
/** Construct the same full-name identity as the owned JUnit reporter. */
export const identity = (task: Task): string => {
	const names: string[] = [task.name];
	let parent = task.suite;
	while (parent && parent !== task.file) {
		names.unshift(parent.name);
		parent = parent.suite;
	}
	return `${relative(required("LIVESPEC_VITEST_ROOT"), task.file.filepath).split("\\").join("/")}::${names.join(" > ")}`;
};
/** Publish only the final attempt after the runner has finished teardown. */
export const finalizeTask = (task: Task): void => {
	const current = records.filter(
		(record) =>
			record.task === task && record.attempt === (task.result?.retryCount ?? 0),
	);
	for (const record of records.filter((record) => record.task === task)) {
		if (!record.settled || !record.consumed)
			errors.push(
				`Unconsumed or unsettled matcher: ${identity(task)}; use direct await/return in an inline imported test/it callback; async helpers and Promise compositions are unsupported`,
			);
	}
	const assertions = current
		.filter((record) => record.settled && record.consumed)
		.map((record) => record.assertion);
	writeFileSync(
		join(required("LIVESPEC_VITEST_WORKERS"), `${randomUUID()}.json`),
		JSON.stringify({
			test_id: identity(task),
			assertions,
			errors: [...errors],
		}),
		{ flag: "wx", mode: 0o600 },
	);
};
