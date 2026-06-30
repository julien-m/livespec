/* ARS-RULE-00949: ai-ressources/code-conventions/remotion.md:112 #performance */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
