/* ARS-RULE-01213: ai-ressources/code-conventions/tanstack.md:67 #data-loading */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
