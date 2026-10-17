/** Classify the immediate external dispatch origin, including nested user callbacks. */
import { isAbsolute, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { isObserverAsset, required } from "./trace-state";

/** First non-owned, non-Chai frame identifies user dispatch or framework delegation. */
export interface MatcherCallsite {
	path: string;
	line: number;
	user: boolean;
}
/** Preserve callback boundaries instead of suppressing every nested matcher by depth. */
export const matcherCallsite = (): MatcherCallsite | undefined => {
	const frames = new Error().stack?.split("\n") ?? [];
	for (const frame of frames) {
		// V8 source frames provide absolute paths or file URLs followed by line and column.
		const match = frame.match(/(?:\(|at )((?:file:\/\/)?\/.*?):(\d+):\d+\)?$/);
		if (!match) continue;
		const path = match[1].startsWith("file:")
			? fileURLToPath(match[1])
			: match[1];
		if (isObserverAsset(path) || path.includes("/node_modules/chai/")) continue;
		const local = relative(required("LIVESPEC_EXECUTION_PROJECT"), path);
		return {
			path: local.split("\\").join("/"),
			line: Number(match[2]),
			user:
				!local.startsWith("..") &&
				!isAbsolute(local) &&
				!local.includes("node_modules/"),
		};
	}
	return undefined;
};
