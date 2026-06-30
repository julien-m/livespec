/* ARS-RULE-01077: ai-ressources/code-conventions/shadcn.md:83 #anti-patterns */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
