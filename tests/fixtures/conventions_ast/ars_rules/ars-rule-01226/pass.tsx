/* ARS-RULE-01226: ai-ressources/code-conventions/tanstack.md:112 #anti-patterns */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
