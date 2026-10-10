/** Reference candidate, never counted as generated output. */
import { createServer } from "node:http";
import { existsSync, readFileSync, writeFileSync } from "node:fs";

export const createApp = (storePath: string) => createServer(async (request, response) => {
	if (request.method !== "POST" || request.url !== "/items") {
		response.writeHead(404).end();
		return;
	}
	if (request.headers.authorization !== "Bearer witness") {
		response.writeHead(403).end();
		return;
	}
	try {
		let body = "";
		for await (const chunk of request) body += chunk;
		const item: unknown = JSON.parse(body);
		if (!item || typeof item !== "object" || !("name" in item) ||
			typeof item.name !== "string" || !item.name.trim()) {
			response.writeHead(400).end();
			return;
		}
		const stored = existsSync(storePath) ? JSON.parse(readFileSync(storePath, "utf8")) : [];
		stored.push(item);
		writeFileSync(storePath, JSON.stringify(stored));
		response.writeHead(201, { "Content-Type": "application/json" }).end(JSON.stringify(item));
	} catch {
		response.writeHead(400).end();
	}
});
