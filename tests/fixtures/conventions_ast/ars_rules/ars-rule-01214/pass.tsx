/* ARS-RULE-01214: ai-ressources/code-conventions/tanstack.md:68 #data-loading */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
