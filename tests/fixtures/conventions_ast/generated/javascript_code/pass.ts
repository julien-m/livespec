import { readFile } from "node:fs/promises";

export const load = async (path: string): Promise<string> => readFile(path, "utf-8");
