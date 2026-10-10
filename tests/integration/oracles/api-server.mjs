/** Candidate-owned process; its stdout is never an acceptance verdict. */
import { pathToFileURL } from "node:url";
import { join } from "node:path";
const { createApp } = await import(pathToFileURL(join(process.argv[2], "app.ts")));
const server = createApp(process.argv[3]);
server.listen(0, "127.0.0.1", () => {
	console.log(JSON.stringify({ port: server.address().port }));
});
