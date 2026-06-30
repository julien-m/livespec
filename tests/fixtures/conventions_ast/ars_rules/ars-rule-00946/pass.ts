/* ARS-RULE-00946: ai-ressources/code-conventions/remotion.md:109 #performance */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
