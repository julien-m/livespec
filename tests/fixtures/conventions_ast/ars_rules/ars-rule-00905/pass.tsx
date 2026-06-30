/* ARS-RULE-00905: ai-ressources/code-conventions/react.md:68 #error-boundaries */
import { readFileSync } from "node:fs";
export const value = readFileSync("x");
