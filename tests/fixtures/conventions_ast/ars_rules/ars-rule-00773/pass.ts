/* ARS-RULE-00773: ai-ressources/code-conventions/nextjs.md:74 #caching-revalidation */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
