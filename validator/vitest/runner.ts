/** Preserve Vitest lifecycle hooks and finalize evidence after task cleanup. */
import { createRequire } from "node:module";
import type {
	Custom,
	ExtendedContext,
	Task,
	TaskContext,
	Test,
} from "@vitest/runner";
import { guardExpectation } from "./expect-guard";
import { installObserver } from "./matcher-observer";
import { errors, finalizeTask, required } from "./trace-state";

const localRequire = createRequire(
	`${required("LIVESPEC_VITEST_ROOT")}/package.json`,
);
// The consumer's genuine runner is the superclass; assets have no framework dependency.
const { VitestTestRunner } = (await import(
	localRequire.resolve("vitest/runners")
)) as typeof import("vitest/runners");
installObserver();

/** Runner-owned finalization surrounds the genuine framework implementation. */
export default class ObservationRunner extends VitestTestRunner {
	/** Wrap the superclass-installed getter while preserving its laziness and original context identity. */
	override extendTaskContext<T extends Test | Custom>(
		context: TaskContext<T>,
	): ExtendedContext<T> {
		// A temporary inherited context lets the superclass install its nonconfigurable descriptors unchanged.
		const facade = Object.create(context) as TaskContext<T>;
		super.extendTaskContext(facade);
		const descriptors = Object.getOwnPropertyDescriptors(facade);
		const originalGet = descriptors.expect?.get;
		if (originalGet)
			descriptors.expect = {
				...descriptors.expect,
				get() {
					const expectation: unknown = originalGet.call(this);
					guardExpectation(expectation);
					return expectation;
				},
			};
		Object.defineProperties(context, descriptors);
		// The superclass has installed the required context descriptors without accessing the lazy expectation.
		return context as ExtendedContext<T>;
	}

	override async onBeforeRunTask(task: Task): Promise<void> {
		await super.onBeforeRunTask(task);
		if (task.concurrent) {
			errors.push(`Unsupported concurrent test: ${task.name}`);
			throw new Error("Unsupported concurrent test");
		}
	}
	override onAfterRunTask(task: Task): void {
		super.onAfterRunTask(task);
		finalizeTask(task);
	}
}
