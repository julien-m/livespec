/* ARS-RULE-00947: ai-ressources/code-conventions/remotion.md:110 #performance */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
