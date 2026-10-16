/** Reconcile complete collected task inventory with worker-owned final matcher streams. */
import { createHash } from "node:crypto";
import { existsSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, relative } from "node:path";
import type { File, Task } from "@vitest/runner";
import type { Reporter } from "vitest/reporters";
import { type AssertionRecord, identity, required } from "./trace-state";

interface WorkerFragment {
	test_id: string;
	assertions: AssertionRecord[];
	errors: string[];
}
interface InventoryTest {
	test_id: string;
	file: string;
	full_name: string;
	status: "passed" | "failed" | "skipped";
}
const collect = (task: Task): InventoryTest[] => {
	if (task.type === "suite") return task.tasks.flatMap(collect);
	const testId = identity(task);
	return [
		{
			test_id: testId,
			file: relative(required("LIVESPEC_EXECUTION_PROJECT"), task.file.filepath)
				.split("\\")
				.join("/"),
			full_name: testId.substring(testId.indexOf("::") + 2),
			status:
				task.mode === "skip" ||
				task.mode === "todo" ||
				task.result?.state === "skip"
					? "skipped"
					: task.result?.state === "pass"
						? "passed"
						: "failed",
		},
	];
};
const publish = (path: string, payload: unknown): void => {
	writeFileSync(path, JSON.stringify(payload), { flag: "wx", mode: 0o600 });
};

// @spec FR-002: Reconcile every selected test with its final matcher stream — .specs/features/096-node-vitest-execution/spec.md#fr-002
/** Final reporter writes immutable files only after all workers and hooks finish. */
export default class ObservationReporter implements Reporter {
	onFinished(files: File[], frameworkErrors: unknown[]): void {
		const tests = files.flatMap((file) => file.tasks.flatMap(collect));
		const workerDirectory = required("LIVESPEC_VITEST_WORKERS");
		const fragments: WorkerFragment[] = (
			existsSync(workerDirectory) ? readdirSync(workerDirectory) : []
		).map((name) =>
			JSON.parse(
				readFileSync(join(required("LIVESPEC_VITEST_WORKERS"), name), "utf8"),
			),
		);
		const boundInputs: Record<string, string> = JSON.parse(
			readFileSync(required("LIVESPEC_VITEST_INPUTS"), "utf8"),
		);
		const errors = fragments.flatMap((fragment) => fragment.errors);
		for (const [path, digest] of Object.entries(boundInputs)) {
			if (
				createHash("sha256")
					.update(
						readFileSync(join(required("LIVESPEC_EXECUTION_PROJECT"), path)),
					)
					.digest("hex") !== digest
			)
				errors.push(`Changed loaded input: ${path}`);
		}
		if (frameworkErrors.length)
			errors.push(
				`Framework collection/setup/unhandled errors: ${frameworkErrors.map((error) => (error instanceof Error ? error.message : String(error))).join("; ")}`,
			);
		for (const test of tests.filter((test) => test.status !== "skipped")) {
			const matching = fragments.filter(
				(fragment) => fragment.test_id === test.test_id,
			);
			if (matching.length !== 1 || !matching[0].assertions.length)
				errors.push(`Missing unique settled matcher stream: ${test.test_id}`);
		}
		if (new Set(tests.map((test) => test.test_id)).size !== tests.length)
			errors.push("Duplicate selected test identities");
		const context = {
			schema_version: "1",
			invocation: required("LIVESPEC_EXECUTION_NONCE"),
			project_root: required("LIVESPEC_EXECUTION_PROJECT"),
			feature: required("LIVESPEC_EXECUTION_FEATURE"),
		};
		publish(required("LIVESPEC_ASSERTION_TRACE"), {
			...context,
			assertions: fragments.flatMap((fragment) => fragment.assertions),
		});
		publish(required("LIVESPEC_VITEST_INVENTORY"), {
			...context,
			tests,
			errors,
			bound_inputs: boundInputs,
		});
	}
}
